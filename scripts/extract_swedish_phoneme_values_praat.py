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
# from the Waxholm corpus using Parselmouth (Praat).
# Based on methods from:
# "Alignment of Speech to Highly Imperfect Text Transcriptions"
# https://ieeexplore.ieee.org/document/4284627

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


def extract_formants_praat(sound, n_formants=3, max_formant=5500.0):
    """
    Extract formants using Praat's Burg algorithm.

    Args:
        sound: parselmouth.Sound object
        n_formants: number of formants to extract
        max_formant: maximum formant frequency (5500 Hz for male, 5000 Hz for female)

    Returns:
        formants: array of mean formant frequencies, or None if extraction fails
    """
    try:
        # Create formant object using Burg method
        formant = call(sound, "To Formant (burg)",
                      0.0,      # time step (0 = auto)
                      5,        # max number of formants
                      max_formant,  # maximum formant (Hz)
                      0.025,    # window length (s)
                      50.0)     # pre-emphasis from (Hz)

        # Get duration midpoint for measurement
        midpoint = sound.duration / 2

        formants = []
        for i in range(1, n_formants + 1):
            f = call(formant, "Get value at time", i, midpoint, "Hertz", "Linear")
            if np.isnan(f) or f <= 0:
                return None
            formants.append(f)

        return np.array(formants)
    except Exception:
        return None


def extract_formants_praat_mean(sound, n_formants=3, max_formant=5500.0):
    """
    Extract mean formants over the entire sound using Praat.

    Args:
        sound: parselmouth.Sound object
        n_formants: number of formants to extract
        max_formant: maximum formant frequency

    Returns:
        formants: array of mean formant frequencies, or None if extraction fails
    """
    try:
        formant = call(sound, "To Formant (burg)",
                      0.0, 5, max_formant, 0.025, 50.0)

        formants = []
        for i in range(1, n_formants + 1):
            f = call(formant, "Get mean", i, 0, 0, "Hertz")
            if np.isnan(f) or f <= 0:
                return None
            formants.append(f)

        return np.array(formants)
    except Exception:
        return None


def extract_spectral_moments(sound):
    """
    Extract spectral moments for fricative characterization using Praat.

    Spectral moments (center of gravity, standard deviation, skewness, kurtosis)
    are useful for distinguishing fricatives.

    Args:
        sound: parselmouth.Sound object

    Returns:
        dict with spectral characteristics, or None if extraction fails
    """
    try:
        # Create spectrum
        spectrum = call(sound, "To Spectrum", "yes")

        # Get spectral moments
        cog = call(spectrum, "Get centre of gravity", 2)  # power = 2
        std = call(spectrum, "Get standard deviation", 2)
        skewness = call(spectrum, "Get skewness", 2)
        kurtosis = call(spectrum, "Get kurtosis", 2)

        # Get energy in frequency bands
        low_band = call(spectrum, "Get band energy", 300, 1500)
        mid_band = call(spectrum, "Get band energy", 1500, 3000)
        high_s_band = call(spectrum, "Get band energy", 3000, 5000)
        high_sh_band = call(spectrum, "Get band energy", 2000, 4000)
        very_high_band = call(spectrum, "Get band energy", 5000, 8000)

        total_energy = call(spectrum, "Get band energy", 0, 0)  # 0,0 = full range

        if total_energy == 0:
            return None

        return {
            'centroid': cog,
            'std_dev': std,
            'skewness': skewness,
            'kurtosis': kurtosis,
            'low': low_band / total_energy,
            'mid': mid_band / total_energy,
            'high_s': high_s_band / total_energy,
            'high_sh': high_sh_band / total_energy,
            'very_high': very_high_band / total_energy
        }
    except Exception:
        return None


def process_corpus(data_location: Path, verbose=False, use_mean_formants=True):
    """
    Process all Waxholm files and extract phoneme characteristics.

    Args:
        data_location: path to Waxholm data directory
        verbose: print progress information
        use_mean_formants: use mean formants over segment (vs midpoint)

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
            audio = audio.astype(np.float64) / 32768.0  # Normalize int16 to float

            # Create Parselmouth Sound object
            full_sound = parselmouth.Sound(audio, sampling_frequency=sr)
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

            # Ensure we don't exceed audio bounds
            if end_time > full_sound.duration:
                continue

            try:
                # Extract segment using Praat
                segment = call(full_sound, "Extract part",
                             start_time, end_time, "rectangular", 1, "no")
            except Exception:
                continue

            if clean_phone in SWEDISH_VOWELS:
                if use_mean_formants:
                    formants = extract_formants_praat_mean(segment)
                else:
                    formants = extract_formants_praat(segment)

                if formants is not None:
                    vowel_formants[clean_phone].append(formants.tolist())

            elif clean_phone in SWEDISH_FRICATIVES:
                spectra = extract_spectral_moments(segment)
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
        description='Extract Swedish vowel and fricative characteristics from Waxholm corpus using Praat.'
    )
    parser.add_argument(
        'data_location',
        type=str,
        help='Path to the Waxholm data directory'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='swedish_phoneme_values_praat.json',
        help='Output JSON file (default: swedish_phoneme_values_praat.json)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print progress information'
    )
    parser.add_argument(
        '--midpoint',
        action='store_true',
        help='Measure formants at segment midpoint instead of mean over segment'
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

    print("Extracting phoneme characteristics from Waxholm corpus (using Praat)...")
    vowel_formants, fricative_spectra = process_corpus(
        data_location,
        args.verbose,
        use_mean_formants=not args.midpoint
    )

    print("Computing statistics...")
    stats = compute_statistics(vowel_formants, fricative_spectra)

    # Add metadata
    stats['metadata'] = {
        'source': 'Waxholm Speech Corpus',
        'extractor': 'parselmouth (Praat)',
        'sample_rate': 16000,
        'min_segment_duration': MIN_SEGMENT_DURATION,
        'formant_measurement': 'midpoint' if args.midpoint else 'mean',
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
