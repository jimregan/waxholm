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
# Extended extraction of Swedish phoneme characteristics from the Waxholm corpus
# using Parselmouth (Praat). Covers vowels, fricatives, nasals, stops, and
# approximants.

try:
    import parselmouth
    from parselmouth.praat import call
    import numpy as np
except ImportError as e:
    print(f"Required library not available: {e}")
    print("This script requires parselmouth and numpy. Install with:")
    print("  pip install praat-parselmouth numpy")
    exit(1)

import argparse
import json
from pathlib import Path
from collections import defaultdict

from waxholm import Mix
from waxholm.audio import smp_read_sf


# Swedish phoneme categories
SWEDISH_VOWELS = {
    'A', 'A:', 'E', 'E:', 'E0', 'I', 'I:', 'O', 'O:',
    'U', 'U:', 'Y', 'Y:', 'Ä', 'Ä:', 'Ä3', 'Ä4',
    'Ö', 'Ö:', 'Ö3', 'Ö4', 'Å', 'Å:'
}

SWEDISH_FRICATIVES = {
    'F', 'S', 'SJ', 'TJ', 'H', 'V', '2S'
}

SWEDISH_NASALS = {
    'M', 'N', 'NG', '2N'
}

SWEDISH_STOPS = {
    'P', 'B', 'T', 'D', 'K', 'G', '2T', '2D'
}

SWEDISH_APPROXIMANTS = {
    'L', 'R', 'J', '2L'
}

# Minimum segment duration in seconds
MIN_SEGMENT_DURATION = 0.03
MIN_SEGMENT_DURATION_STOPS = 0.02  # Stops can be shorter


def extract_vowel_features(sound, max_formant=5500.0):
    """
    Extract vowel features: F1-F3 formants.
    """
    try:
        formant = call(sound, "To Formant (burg)",
                      0.0, 5, max_formant, 0.025, 50.0)

        features = {}
        for i in range(1, 4):
            f = call(formant, "Get mean", i, 0, 0, "Hertz")
            if np.isnan(f) or f <= 0:
                return None
            features[f'F{i}'] = f

        # Also get bandwidth (relates to vowel quality/nasalization)
        for i in range(1, 4):
            bw = call(formant, "Get bandwidth at time", i, sound.duration / 2, "Hertz", "Linear")
            if not np.isnan(bw):
                features[f'B{i}'] = bw

        return features
    except Exception:
        return None


def extract_fricative_features(sound):
    """
    Extract fricative features: spectral moments and band energies.
    """
    try:
        spectrum = call(sound, "To Spectrum", "yes")

        features = {
            'centroid': call(spectrum, "Get centre of gravity", 2),
            'std_dev': call(spectrum, "Get standard deviation", 2),
            'skewness': call(spectrum, "Get skewness", 2),
            'kurtosis': call(spectrum, "Get kurtosis", 2),
        }

        # Band energies (normalized)
        total_energy = call(spectrum, "Get band energy", 0, 0)
        if total_energy == 0:
            return None

        bands = [
            ('low', 300, 1500),
            ('mid', 1500, 3000),
            ('high_s', 3000, 5000),
            ('high_sh', 2000, 4000),
            ('very_high', 5000, 8000),
        ]
        for name, low, high in bands:
            features[name] = call(spectrum, "Get band energy", low, high) / total_energy

        return features
    except Exception:
        return None


def extract_nasal_features(sound, max_formant=5500.0):
    """
    Extract nasal features: formants, nasal formant, and voicing.

    Nasals are characterized by:
    - A low nasal formant around 250-300 Hz
    - Anti-formants that reduce energy at certain frequencies
    - Continuous voicing
    """
    try:
        features = {}

        # Formants (nasals have formant-like resonances)
        formant = call(sound, "To Formant (burg)",
                      0.0, 5, max_formant, 0.025, 50.0)

        for i in range(1, 4):
            f = call(formant, "Get mean", i, 0, 0, "Hertz")
            if not np.isnan(f) and f > 0:
                features[f'F{i}'] = f

        # Pitch (voicing characteristics)
        pitch = call(sound, "To Pitch", 0.0, 75, 600)
        mean_f0 = call(pitch, "Get mean", 0, 0, "Hertz")
        if not np.isnan(mean_f0):
            features['F0'] = mean_f0

        # Fraction voiced
        point_process = call(sound, "To PointProcess (periodic, cc)", 75, 600)
        voiced_fraction = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        # Jitter is low for voiced sounds; we use it as a proxy

        # Intensity
        intensity = call(sound, "To Intensity", 100, 0, "yes")
        mean_intensity = call(intensity, "Get mean", 0, 0, "energy")
        if not np.isnan(mean_intensity):
            features['intensity'] = mean_intensity

        # Spectrum for nasal characteristics
        spectrum = call(sound, "To Spectrum", "yes")

        # Low frequency energy (nasal murmur around 250-300 Hz)
        total_energy = call(spectrum, "Get band energy", 0, 0)
        if total_energy > 0:
            nasal_band = call(spectrum, "Get band energy", 200, 400)
            features['nasal_band'] = nasal_band / total_energy

            # Anti-formant region varies by nasal, but generally causes dips
            low_mid = call(spectrum, "Get band energy", 400, 1000)
            features['low_mid_band'] = low_mid / total_energy

        return features if features else None
    except Exception:
        return None


def extract_stop_features(sound, full_sound=None, start_time=0, end_time=0):
    """
    Extract stop consonant features: VOT, burst spectrum, intensity.

    Stops are characterized by:
    - Closure (silence/low energy)
    - Burst (brief noise)
    - Voice Onset Time (VOT) - negative for prevoiced, positive for aspirated
    """
    try:
        features = {}

        # Intensity profile
        intensity = call(sound, "To Intensity", 100, 0, "yes")
        max_intensity = call(intensity, "Get maximum", 0, 0, "Parabolic")
        min_intensity = call(intensity, "Get minimum", 0, 0, "Parabolic")
        mean_intensity = call(intensity, "Get mean", 0, 0, "energy")

        if not np.isnan(max_intensity):
            features['max_intensity'] = max_intensity
        if not np.isnan(min_intensity):
            features['min_intensity'] = min_intensity
        if not np.isnan(mean_intensity):
            features['mean_intensity'] = mean_intensity

        # Intensity range (burst prominence)
        if not np.isnan(max_intensity) and not np.isnan(min_intensity):
            features['intensity_range'] = max_intensity - min_intensity

        # Spectral characteristics of the burst
        spectrum = call(sound, "To Spectrum", "yes")
        features['burst_cog'] = call(spectrum, "Get centre of gravity", 2)
        features['burst_std'] = call(spectrum, "Get standard deviation", 2)

        # Band energies for place of articulation
        total_energy = call(spectrum, "Get band energy", 0, 0)
        if total_energy > 0:
            # Different places have energy in different regions
            # Labials: diffuse, falling spectrum
            # Alveolars: high frequency energy
            # Velars: mid-frequency concentration
            features['low_band'] = call(spectrum, "Get band energy", 300, 1000) / total_energy
            features['mid_band'] = call(spectrum, "Get band energy", 1000, 2500) / total_energy
            features['high_band'] = call(spectrum, "Get band energy", 2500, 5000) / total_energy

        # Check for voicing (for voiced stops)
        pitch = call(sound, "To Pitch", 0.0, 75, 600)
        voiced_frames = call(pitch, "Count voiced frames")
        total_frames = call(pitch, "Get number of frames")
        if total_frames > 0:
            features['voiced_fraction'] = voiced_frames / total_frames

        return features if features else None
    except Exception:
        return None


def extract_approximant_features(sound, max_formant=5500.0):
    """
    Extract approximant/liquid features: formants (especially F3), voicing.

    Approximants are characterized by:
    - Formant patterns (F3 distinguishes /r/ from /l/)
    - Continuous voicing
    - Less constriction than fricatives
    """
    try:
        features = {}

        # Formants (F3 is particularly important for /r/ vs /l/)
        formant = call(sound, "To Formant (burg)",
                      0.0, 5, max_formant, 0.025, 50.0)

        for i in range(1, 5):  # Get F1-F4 for approximants
            f = call(formant, "Get mean", i, 0, 0, "Hertz")
            if not np.isnan(f) and f > 0:
                features[f'F{i}'] = f

        # Bandwidths
        for i in range(1, 4):
            bw = call(formant, "Get bandwidth at time", i, sound.duration / 2, "Hertz", "Linear")
            if not np.isnan(bw):
                features[f'B{i}'] = bw

        # Pitch/voicing
        pitch = call(sound, "To Pitch", 0.0, 75, 600)
        mean_f0 = call(pitch, "Get mean", 0, 0, "Hertz")
        if not np.isnan(mean_f0):
            features['F0'] = mean_f0

        # Intensity
        intensity = call(sound, "To Intensity", 100, 0, "yes")
        mean_intensity = call(intensity, "Get mean", 0, 0, "energy")
        if not np.isnan(mean_intensity):
            features['intensity'] = mean_intensity

        # Harmonics-to-noise ratio (high for voiced approximants)
        try:
            hnr = call(sound, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
            mean_hnr = call(hnr, "Get mean", 0, 0)
            if not np.isnan(mean_hnr):
                features['HNR'] = mean_hnr
        except Exception:
            pass

        return features if features else None
    except Exception:
        return None


def process_corpus(data_location: Path, verbose=False):
    """
    Process all Waxholm files and extract phoneme characteristics.
    """
    vowel_data = defaultdict(list)
    fricative_data = defaultdict(list)
    nasal_data = defaultdict(list)
    stop_data = defaultdict(list)
    approximant_data = defaultdict(list)

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
        smp_file = mixfile.parent / mixfile.stem
        if not smp_file.exists():
            if verbose:
                print(f"  Audio file not found: {smp_file}")
            continue

        try:
            audio, sr = smp_read_sf(str(smp_file))
            audio = audio.astype(np.float64) / 32768.0
            full_sound = parselmouth.Sound(audio, sampling_frequency=sr)
        except Exception as e:
            if verbose:
                print(f"  Could not read audio {smp_file}: {e}")
            continue

        # Get phone-level alignments
        phone_tuples = mix.get_phone_label_tuples()

        for start_time, end_time, phone in phone_tuples:
            clean_phone = phone.lstrip("ˈ`ˌ")
            duration = end_time - start_time

            # Different minimum durations for different categories
            if clean_phone in SWEDISH_STOPS:
                if duration < MIN_SEGMENT_DURATION_STOPS:
                    continue
            elif duration < MIN_SEGMENT_DURATION:
                continue

            if end_time > full_sound.duration:
                continue

            try:
                segment = call(full_sound, "Extract part",
                             start_time, end_time, "rectangular", 1, "no")
            except Exception:
                continue

            if clean_phone in SWEDISH_VOWELS:
                features = extract_vowel_features(segment)
                if features:
                    vowel_data[clean_phone].append(features)

            elif clean_phone in SWEDISH_FRICATIVES:
                features = extract_fricative_features(segment)
                if features:
                    fricative_data[clean_phone].append(features)

            elif clean_phone in SWEDISH_NASALS:
                features = extract_nasal_features(segment)
                if features:
                    nasal_data[clean_phone].append(features)

            elif clean_phone in SWEDISH_STOPS:
                features = extract_stop_features(segment, full_sound, start_time, end_time)
                if features:
                    stop_data[clean_phone].append(features)

            elif clean_phone in SWEDISH_APPROXIMANTS:
                features = extract_approximant_features(segment)
                if features:
                    approximant_data[clean_phone].append(features)

    return {
        'vowels': dict(vowel_data),
        'fricatives': dict(fricative_data),
        'nasals': dict(nasal_data),
        'stops': dict(stop_data),
        'approximants': dict(approximant_data)
    }


def compute_statistics(data_by_category, min_samples=5):
    """
    Compute mean and std for each phoneme's characteristics.
    """
    stats = {}

    for category, phoneme_data in data_by_category.items():
        stats[category] = {}

        for phoneme, feature_list in phoneme_data.items():
            if len(feature_list) < min_samples:
                continue

            stats[category][phoneme] = {'count': len(feature_list)}

            # Get all feature keys from the first item
            all_keys = set()
            for f in feature_list:
                all_keys.update(f.keys())

            for key in all_keys:
                values = [f[key] for f in feature_list if key in f and not np.isnan(f[key])]
                if values:
                    stats[category][phoneme][key] = float(np.mean(values))
                    stats[category][phoneme][f'{key}_std'] = float(np.std(values))

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Extract extended Swedish phoneme characteristics from Waxholm corpus.'
    )
    parser.add_argument(
        'data_location',
        type=str,
        help='Path to the Waxholm data directory'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='swedish_phoneme_values_extended.json',
        help='Output JSON file (default: swedish_phoneme_values_extended.json)'
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

    print("Extracting extended phoneme characteristics from Waxholm corpus...")
    raw_data = process_corpus(data_location, args.verbose)

    print("Computing statistics...")
    stats = compute_statistics(raw_data)

    # Add metadata
    total_counts = {}
    for category in stats:
        total_counts[category] = sum(p.get('count', 0) for p in stats[category].values())

    stats['metadata'] = {
        'source': 'Waxholm Speech Corpus',
        'extractor': 'parselmouth (Praat) - extended',
        'sample_rate': 16000,
        'min_segment_duration': MIN_SEGMENT_DURATION,
        'min_segment_duration_stops': MIN_SEGMENT_DURATION_STOPS,
        'categories': list(raw_data.keys()),
        'counts': total_counts
    }

    print(f"\nExtracted values for:")
    for category in ['vowels', 'fricatives', 'nasals', 'stops', 'approximants']:
        if category in stats:
            n_phonemes = len(stats[category])
            n_segments = total_counts.get(category, 0)
            print(f"  {category}: {n_phonemes} phonemes, {n_segments} segments")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_path}")


if __name__ == '__main__':
    main()
