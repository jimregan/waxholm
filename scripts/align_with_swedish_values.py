#!/usr/bin/env python
# Copyright (c) 2026, Jim O'Regan for Språkbanken Tal
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Performs approximate phoneme alignment for Swedish audio using formant-based
# vowel detection and spectral fricative detection.
# Uses reference values extracted from the Waxholm corpus.
# Based on methods from:
# "Alignment of Speech to Highly Imperfect Text Transcriptions"
# https://ieeexplore.ieee.org/document/4284627

try:
    import librosa
    import numpy as np
except ImportError as e:
    print(f"Required library not available: {e}")
    print("This script requires librosa and numpy. Install with:")
    print("  pip install librosa numpy")
    exit(1)

import argparse
import json
from pathlib import Path


def load_reference_values(reference_file: Path):
    """
    Load reference phoneme values from JSON file.

    Args:
        reference_file: path to JSON file with phoneme values

    Returns:
        dict with vowel and fricative reference values
    """
    with open(reference_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_formants(audio, sr, n_formants=3):
    """
    Extract formants using LPC analysis.

    Args:
        audio: audio frame (numpy array)
        sr: sampling rate
        n_formants: number of formants to extract

    Returns:
        formants: array of formant frequencies, or None if extraction fails
    """
    if len(audio) < 256:
        return None

    # LPC order
    order = int(2 + sr / 1000)

    # Pre-emphasis
    audio = librosa.effects.preemphasis(audio)

    # Normalize
    audio = audio - np.mean(audio)
    max_val = np.max(np.abs(audio))
    if max_val == 0:
        return None
    audio = audio / max_val

    try:
        a = librosa.lpc(audio, order=order)
        roots = np.roots(a)
        roots = roots[np.imag(roots) >= 0]
        angles = np.angle(roots)
        freqs = np.sort(angles * (sr / (2 * np.pi)))
        freqs = freqs[(freqs > 200) & (freqs < 5000)]

        if len(freqs) < n_formants:
            return None

        return freqs[:n_formants]
    except Exception:
        return None


def extract_spectral_features(audio, sr):
    """
    Extract spectral features for fricative detection.

    Args:
        audio: audio frame
        sr: sampling rate

    Returns:
        dict with spectral features, or None if extraction fails
    """
    if len(audio) < 256:
        return None

    try:
        n_fft = min(2048, len(audio))
        S = np.abs(librosa.stft(audio, n_fft=n_fft))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

        power = np.mean(S ** 2, axis=1)
        total_energy = np.sum(power)
        if total_energy == 0:
            return None

        bands = {
            'low': (300, 1500),
            'mid': (1500, 3000),
            'high_s': (3000, 5000),
            'high_sh': (2000, 4000),
            'very_high': (5000, 8000)
        }

        result = {}
        for band_name, (low, high) in bands.items():
            mask = (freqs >= low) & (freqs < high)
            band_energy = np.sum(power[mask])
            result[band_name] = band_energy / total_energy

        result['centroid'] = float(librosa.feature.spectral_centroid(
            S=S, sr=sr
        ).mean())

        return result
    except Exception:
        return None


def match_vowel(formants, vowel_refs, weights=None):
    """
    Match formants to closest vowel reference.

    Args:
        formants: array of F1, F2, F3
        vowel_refs: dict of vowel reference values
        weights: optional weights for F1, F2, F3

    Returns:
        tuple of (best_vowel, distance)
    """
    if weights is None:
        weights = np.array([2.0, 1.0, 0.5])  # F1 most important, F3 least

    best_vowel = None
    best_distance = float('inf')

    for vowel, ref in vowel_refs.items():
        target = np.array([ref['F1'], ref['F2'], ref['F3']])
        # Normalize by standard deviation if available
        if 'F1_std' in ref and ref['F1_std'] > 0:
            norm = np.array([ref['F1_std'], ref['F2_std'], ref['F3_std']])
            dist = np.sum(weights * ((formants - target) / norm) ** 2)
        else:
            dist = np.sum(weights * (formants - target) ** 2)

        if dist < best_distance:
            best_distance = dist
            best_vowel = vowel

    return best_vowel, best_distance


def match_fricative(features, fricative_refs):
    """
    Match spectral features to closest fricative reference.

    Args:
        features: dict of spectral features
        fricative_refs: dict of fricative reference values

    Returns:
        tuple of (best_fricative, distance)
    """
    best_fricative = None
    best_distance = float('inf')

    feature_keys = ['low', 'mid', 'high_s', 'high_sh', 'centroid']

    for fricative, ref in fricative_refs.items():
        dist = 0
        for key in feature_keys:
            if key in features and key in ref:
                diff = features[key] - ref[key]
                # Normalize by std if available
                std_key = f'{key}_std'
                if std_key in ref and ref[std_key] > 0:
                    diff = diff / ref[std_key]
                dist += diff ** 2

        if dist < best_distance:
            best_distance = dist
            best_fricative = fricative

    return best_fricative, best_distance


def detect_voiced_frames(y, sr, frame_length, hop_length):
    """
    Detect voiced frames using energy and zero-crossing rate.

    Returns:
        boolean array indicating voiced frames
    """
    # RMS energy
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]

    # Zero crossing rate (lower for voiced, higher for unvoiced/silence)
    zcr = librosa.feature.zero_crossing_rate(y=y, frame_length=frame_length, hop_length=hop_length)[0]

    # Voiced frames have higher energy and lower ZCR
    energy_threshold = np.percentile(rms, 25)
    zcr_threshold = np.percentile(zcr, 75)

    voiced = (rms > energy_threshold) & (zcr < zcr_threshold)
    return voiced, rms


def align_audio(audio_file: str, reference_values: dict,
                frame_length_sec=0.03, hop_length_sec=0.01):
    """
    Perform phoneme alignment on an audio file.

    Args:
        audio_file: path to audio file
        reference_values: dict with vowel and fricative references
        frame_length_sec: analysis window in seconds
        hop_length_sec: hop between frames in seconds

    Returns:
        list of (time, phoneme, confidence) tuples
    """
    # Load audio
    y, sr = librosa.load(audio_file, sr=16000)

    frame_length = int(frame_length_sec * sr)
    hop_length = int(hop_length_sec * sr)

    # Detect voiced/unvoiced frames
    voiced, rms = detect_voiced_frames(y, sr, frame_length, hop_length)

    vowel_refs = reference_values.get('vowels', {})
    fricative_refs = reference_values.get('fricatives', {})

    results = []
    n_frames = 1 + (len(y) - frame_length) // hop_length

    for i in range(n_frames):
        start = i * hop_length
        end = start + frame_length
        frame = y[start:end]
        time = start / sr

        # Skip very quiet frames
        if rms[i] < np.percentile(rms, 10):
            results.append((time, 'SIL', 1.0))
            continue

        if voiced[i]:
            # Try vowel detection
            formants = extract_formants(frame, sr)
            if formants is not None:
                vowel, dist = match_vowel(formants, vowel_refs)
                # Convert distance to confidence (lower distance = higher confidence)
                confidence = 1.0 / (1.0 + dist / 1000)
                results.append((time, vowel, confidence))
            else:
                results.append((time, '?', 0.0))
        else:
            # Try fricative detection
            features = extract_spectral_features(frame, sr)
            if features is not None:
                fricative, dist = match_fricative(features, fricative_refs)
                confidence = 1.0 / (1.0 + dist)
                results.append((time, fricative, confidence))
            else:
                results.append((time, '?', 0.0))

    return results


def smooth_results(results, min_duration_frames=3):
    """
    Smooth results by removing very short segments.

    Args:
        results: list of (time, phoneme, confidence) tuples
        min_duration_frames: minimum number of consecutive frames

    Returns:
        smoothed results
    """
    if len(results) < min_duration_frames:
        return results

    smoothed = []
    i = 0

    while i < len(results):
        current_phoneme = results[i][1]
        segment_start = i
        total_confidence = results[i][2]

        # Find consecutive frames with same phoneme
        while i + 1 < len(results) and results[i + 1][1] == current_phoneme:
            i += 1
            total_confidence += results[i][2]

        segment_length = i - segment_start + 1

        if segment_length >= min_duration_frames or current_phoneme == 'SIL':
            avg_confidence = total_confidence / segment_length
            smoothed.append((results[segment_start][0], current_phoneme, avg_confidence))

        i += 1

    return smoothed


def merge_segments(results, hop_length_sec=0.01):
    """
    Merge consecutive identical phonemes into segments with start/end times.

    Returns:
        list of (start_time, end_time, phoneme, confidence) tuples
    """
    if not results:
        return []

    segments = []
    current_start = results[0][0]
    current_phoneme = results[0][1]
    current_confidence = results[0][2]
    count = 1

    for i in range(1, len(results)):
        if results[i][1] == current_phoneme:
            current_confidence += results[i][2]
            count += 1
        else:
            end_time = results[i][0]
            segments.append((
                current_start,
                end_time,
                current_phoneme,
                current_confidence / count
            ))
            current_start = results[i][0]
            current_phoneme = results[i][1]
            current_confidence = results[i][2]
            count = 1

    # Add final segment
    if results:
        end_time = results[-1][0] + hop_length_sec
        segments.append((
            current_start,
            end_time,
            current_phoneme,
            current_confidence / count
        ))

    return segments


def main():
    parser = argparse.ArgumentParser(
        description='Align Swedish audio using extracted phoneme reference values.'
    )
    parser.add_argument(
        'audio_file',
        type=str,
        help='Path to audio file to align'
    )
    parser.add_argument(
        '--reference', '-r',
        type=str,
        default='swedish_phoneme_values.json',
        help='Reference values JSON file (default: swedish_phoneme_values.json)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file (default: stdout)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['tsv', 'json', 'textgrid'],
        default='tsv',
        help='Output format (default: tsv)'
    )
    parser.add_argument(
        '--frame-length',
        type=float,
        default=0.03,
        help='Frame length in seconds (default: 0.03)'
    )
    parser.add_argument(
        '--hop-length',
        type=float,
        default=0.01,
        help='Hop length in seconds (default: 0.01)'
    )
    args = parser.parse_args()

    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"Error: Audio file '{audio_path}' does not exist")
        exit(1)

    reference_path = Path(args.reference)
    if not reference_path.exists():
        print(f"Error: Reference file '{reference_path}' does not exist")
        print("Generate it first using extract_swedish_phoneme_values.py")
        exit(1)

    print(f"Loading reference values from {reference_path}...", file=__import__('sys').stderr)
    reference_values = load_reference_values(reference_path)

    print(f"Aligning {audio_path}...", file=__import__('sys').stderr)
    results = align_audio(
        str(audio_path),
        reference_values,
        frame_length_sec=args.frame_length,
        hop_length_sec=args.hop_length
    )

    # Smooth and merge
    results = smooth_results(results)
    segments = merge_segments(results, args.hop_length)

    # Output
    output_lines = []

    if args.format == 'tsv':
        output_lines.append("start\tend\tphoneme\tconfidence")
        for start, end, phoneme, conf in segments:
            output_lines.append(f"{start:.3f}\t{end:.3f}\t{phoneme}\t{conf:.3f}")

    elif args.format == 'json':
        output_data = {
            'segments': [
                {
                    'start': round(start, 3),
                    'end': round(end, 3),
                    'phoneme': phoneme,
                    'confidence': round(conf, 3)
                }
                for start, end, phoneme, conf in segments
            ]
        }
        output_lines.append(json.dumps(output_data, indent=2, ensure_ascii=False))

    elif args.format == 'textgrid':
        # Simple Praat TextGrid format
        total_duration = segments[-1][1] if segments else 0
        output_lines.append('File type = "ooTextFile"')
        output_lines.append('Object class = "TextGrid"')
        output_lines.append('')
        output_lines.append(f'xmin = 0')
        output_lines.append(f'xmax = {total_duration}')
        output_lines.append('tiers? <exists>')
        output_lines.append('size = 1')
        output_lines.append('item []:')
        output_lines.append('    item [1]:')
        output_lines.append('        class = "IntervalTier"')
        output_lines.append('        name = "phonemes"')
        output_lines.append('        xmin = 0')
        output_lines.append(f'        xmax = {total_duration}')
        output_lines.append(f'        intervals: size = {len(segments)}')
        for i, (start, end, phoneme, _) in enumerate(segments, 1):
            output_lines.append(f'        intervals [{i}]:')
            output_lines.append(f'            xmin = {start}')
            output_lines.append(f'            xmax = {end}')
            output_lines.append(f'            text = "{phoneme}"')

    output_text = '\n'.join(output_lines)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"Saved to {args.output}", file=__import__('sys').stderr)
    else:
        print(output_text)


if __name__ == '__main__':
    main()
