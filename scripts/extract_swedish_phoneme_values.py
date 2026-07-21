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
# Extracts Swedish vowel formant values and fricative spectral characteristics
# from the Waxholm corpus for use in phoneme-based alignment.
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
from collections import defaultdict

from waxholm import Mix
from waxholm.audio import smp_read_sf


# Swedish vowels (short and long variants)
SWEDISH_VOWELS = {
    'A', 'A:', 'E', 'E:', 'E0', 'I', 'I:', 'O', 'O:',
    'U', 'U:', 'Y', 'Y:', 'Ä', 'Ä:', 'Ä3', 'Ä4',
    'Ö', 'Ö:', 'Ö3', 'Ö4', 'Å', 'Å:'
}

# Swedish fricatives
SWEDISH_FRICATIVES = {
    'F', 'S', 'SJ', 'TJ', 'H', 'V', '2S'
}

# Minimum segment duration in seconds for reliable extraction
MIN_SEGMENT_DURATION = 0.03


def extract_formants(audio, sr, n_formants=3):
    """
    Extract formants using LPC analysis.

    Args:
        audio: audio segment (numpy array)
        sr: sampling rate
        n_formants: number of formants to extract

    Returns:
        formants: array of formant frequencies, or None if extraction fails
    """
    if len(audio) < 256:
        return None

    # LPC order rule of thumb: 2 + sr/1000
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
        # Get LPC coefficients
        a = librosa.lpc(audio, order=order)

        # Find roots of LPC polynomial
        roots = np.roots(a)
        roots = roots[np.imag(roots) >= 0]  # Keep positive frequencies only

        # Convert to Hz
        angles = np.angle(roots)
        freqs = np.sort(angles * (sr / (2 * np.pi)))

        # Filter to reasonable formant range (200-5000 Hz)
        freqs = freqs[(freqs > 200) & (freqs < 5000)]

        if len(freqs) < n_formants:
            return None

        return freqs[:n_formants]
    except Exception:
        return None


def extract_spectral_characteristics(audio, sr):
    """
    Extract spectral energy distribution for fricative characterization.

    Args:
        audio: audio segment
        sr: sampling rate

    Returns:
        dict with energy in different frequency bands
    """
    if len(audio) < 256:
        return None

    try:
        # Compute power spectrum
        n_fft = min(2048, len(audio))
        S = np.abs(librosa.stft(audio, n_fft=n_fft))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

        # Average power across frames
        power = np.mean(S ** 2, axis=1)

        # Energy in different frequency bands
        bands = {
            'low': (300, 1500),      # Low frequency
            'mid': (1500, 3000),     # Mid frequency
            'high_s': (3000, 5000),  # High frequency (typical for /s/)
            'high_sh': (2000, 4000), # Frequency range for palatal fricatives
            'very_high': (5000, 8000) # Very high frequency
        }

        result = {}
        total_energy = np.sum(power)
        if total_energy == 0:
            return None

        for band_name, (low, high) in bands.items():
            mask = (freqs >= low) & (freqs < high)
            band_energy = np.sum(power[mask])
            result[band_name] = band_energy / total_energy

        # Spectral centroid
        result['centroid'] = float(librosa.feature.spectral_centroid(
            S=S, sr=sr
        ).mean())

        return result
    except Exception:
        return None


def process_corpus(data_location: Path, verbose=False):
    """
    Process all Waxholm files and extract phoneme characteristics.

    Args:
        data_location: path to Waxholm data directory
        verbose: print progress information

    Returns:
        tuple of (vowel_formants, fricative_spectra) dictionaries
    """
    vowel_formants = defaultdict(list)
    fricative_spectra = defaultdict(list)

    mix_files = list(data_location.glob("**/*.mix"))

    if verbose:
        print(f"Found {len(mix_files)} .mix files")

    for i, mixfile in enumerate(mix_files):
        if verbose and i % 100 == 0:
            print(f"Processing file {i+1}/{len(mix_files)}")

        try:
            mix = Mix(filepath=mixfile)
        except Exception as e:
            if verbose:
                print(f"  Skipping {mixfile}: {e}")
            continue

        # Find corresponding audio file
        # Handle .smp.mix naming convention: stem removes .mix, leaving the .smp name
        smp_file = mixfile.parent / mixfile.stem
        if not smp_file.exists():
            if verbose:
                print(f"  Audio file not found: {smp_file}")
            continue

        try:
            audio, sr = smp_read_sf(str(smp_file))
            audio = audio.astype(np.float32) / 32768.0  # Normalize int16 to float
        except Exception as e:
            if verbose:
                print(f"  Could not read audio {smp_file}: {e}")
            continue

        # Get phone-level alignments
        phone_tuples = mix.get_phone_label_tuples()

        for start_time, end_time, phone in phone_tuples:
            # Skip accented versions - strip accent markers
            clean_phone = phone.lstrip("ˈ`ˌ")

            duration = end_time - start_time
            if duration < MIN_SEGMENT_DURATION:
                continue

            # Extract audio segment
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)

            if start_sample >= len(audio) or end_sample > len(audio):
                continue

            segment = audio[start_sample:end_sample]

            if clean_phone in SWEDISH_VOWELS:
                formants = extract_formants(segment, sr)
                if formants is not None:
                    vowel_formants[clean_phone].append(formants.tolist())

            elif clean_phone in SWEDISH_FRICATIVES:
                spectra = extract_spectral_characteristics(segment, sr)
                if spectra is not None:
                    fricative_spectra[clean_phone].append(spectra)

    return dict(vowel_formants), dict(fricative_spectra)


def compute_statistics(vowel_formants, fricative_spectra):
    """
    Compute mean and std for each phoneme's characteristics.

    Returns:
        dict with statistics for vowels and fricatives
    """
    stats = {
        'vowels': {},
        'fricatives': {}
    }

    # Vowel statistics (mean formants)
    for vowel, formant_list in vowel_formants.items():
        if len(formant_list) < 5:  # Need enough samples
            continue
        formants_array = np.array(formant_list)
        stats['vowels'][vowel] = {
            'F1': float(np.mean(formants_array[:, 0])),
            'F2': float(np.mean(formants_array[:, 1])),
            'F3': float(np.mean(formants_array[:, 2])),
            'F1_std': float(np.std(formants_array[:, 0])),
            'F2_std': float(np.std(formants_array[:, 1])),
            'F3_std': float(np.std(formants_array[:, 2])),
            'count': len(formant_list)
        }

    # Fricative statistics (mean spectral characteristics)
    for fricative, spectra_list in fricative_spectra.items():
        if len(spectra_list) < 5:
            continue

        # Aggregate spectral characteristics
        keys = spectra_list[0].keys()
        stats['fricatives'][fricative] = {'count': len(spectra_list)}

        for key in keys:
            values = [s[key] for s in spectra_list]
            stats['fricatives'][fricative][key] = float(np.mean(values))
            stats['fricatives'][fricative][f'{key}_std'] = float(np.std(values))

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Extract Swedish vowel and fricative characteristics from Waxholm corpus.'
    )
    parser.add_argument(
        'data_location',
        type=str,
        help='Path to the Waxholm data directory'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='swedish_phoneme_values.json',
        help='Output JSON file (default: swedish_phoneme_values.json)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print progress information'
    )
    args = parser.parse_args()

    data_location = Path(args.data_location)
    if not data_location.exists():
        print(f"Error: Path '{data_location}' does not exist")
        exit(1)
    if not data_location.is_dir():
        print(f"Error: Path '{data_location}' is not a directory")
        exit(1)

    output_path = Path(args.output)
    if output_path.exists():
        print(f"Error: Output file '{output_path}' already exists")
        exit(1)

    print("Extracting phoneme characteristics from Waxholm corpus...")
    vowel_formants, fricative_spectra = process_corpus(data_location, args.verbose)

    print("Computing statistics...")
    stats = compute_statistics(vowel_formants, fricative_spectra)

    # Add metadata
    stats['metadata'] = {
        'source': 'Waxholm Speech Corpus',
        'sample_rate': 16000,
        'min_segment_duration': MIN_SEGMENT_DURATION,
        'vowel_count': sum(s['count'] for s in stats['vowels'].values()),
        'fricative_count': sum(s['count'] for s in stats['fricatives'].values())
    }

    print(f"\nExtracted values for {len(stats['vowels'])} vowels and {len(stats['fricatives'])} fricatives")
    print(f"Total vowel segments: {stats['metadata']['vowel_count']}")
    print(f"Total fricative segments: {stats['metadata']['fricative_count']}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_path}")


if __name__ == '__main__':
    main()
