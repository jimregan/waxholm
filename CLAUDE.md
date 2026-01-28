# Waxholm Module

A Python library for reading and processing transcription data from the **Waxholm Speech Corpus**, a Swedish speech database developed by KTH (Royal Institute of Technology). The module parses `.mix` annotation files containing detailed phonetic and word-level alignments.

**Current Version**: 0.1.6
**License**: Apache 2.0
**Developed for**: Språkbanken Tal (Swedish Language Bank)

## Project Structure

```
waxholm/
├── waxholm/                    # Main package
│   ├── __init__.py            # Exports Mix, FR classes
│   ├── mix.py                 # Core parsing logic
│   ├── audio.py               # SMP to WAV audio conversion
│   ├── utils.py               # Phonetic processing utilities
│   ├── exceptions.py          # Custom exceptions (FRExpected)
│   └── tests/                 # Unit tests (pytest)
├── scripts/                   # Conversion utilities
├── data/                      # Lexicon and pronunciation data
├── docs/                      # Sphinx documentation
└── setup.py                   # Package configuration
```

## Core Classes

### FR Class (`waxholm/mix.py`)

Represents a single **Frame Record** from a `.mix` file.

**Key attributes**:
- `frame` - Frame number
- `seconds` - Time in seconds
- `type` - B (Begin), I (Inner), or E (End)
- `phone` - Phoneme symbol
- `word` - Orthographic word
- `pm` - Postulated pronunciation

**Key methods**:
- `from_text(text)` - Parse a single FR line
- `get_phone(fix_accents)` - Get phoneme with optional accent normalization
- `is_silence_word(noise)` - Check if word is silence/noise

### Mix Class (`waxholm/mix.py`)

Represents a complete `.mix` file with parsed annotations.

**Key attributes**:
- `fr` - List of FR objects
- `text` - Orthographic transcription
- `phoneme` - Phonetic transcription
- `path` - Source file path

**Key methods**:
- `get_time_pairs(as_frames)` - Get (start, end) time tuples
- `get_phone_label_tuples()` - Get (start, end, phoneme) tuples for alignment
- `get_word_label_tuples()` - Get (start, end, word) tuples
- `get_dictionary(fix_accents)` - Extract pronunciation dictionary
- `get_phoneme_string(insert_pauses, fix_accents)` - Get full phonetic string
- `merge_plosives()` - Merge stop consonant closures with releases
- `prune_empty_segments()` - Remove zero-duration annotations

## Utility Modules

### `waxholm/utils.py`

Phonetic and text processing utilities:
- `clean_pronunciation()` - Comprehensive phonetic cleaning
- `strip_accents()` - Remove IPA accent markers
- `map_to_ipa()` - Convert Waxholm symbols to IPA
- `clean_x_words()` - Remove non-speech noise markers (X-tags)
- `is_glottal_closure()` - Check if phoneme pair is glottal closure

### `waxholm/audio.py`

Audio file handling:
- `smp_to_wav(infile, outfile)` - Convert Waxholm SMP format to WAV
- `smp_headers(filename)` - Extract SMP file metadata
- `smp_read_sf(filename)` - Read SMP audio data

## Conversion Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| `convert_to_mfa.py` | Montreal Forced Aligner format with lexicon |
| `convert_to_mfa_g2p.py` | MFA format for G2P training |
| `convert_to_nemo_g2p.py` | NVIDIA NeMo G2P format |
| `convert_to_fairseq.py` | Facebook FairSeq format |
| `convert_to_textgrid.py` | Praat TextGrid format |
| `check_lexicon.py` | Validate lexicon entries |

## Data Format

The `.mix` file format uses **FR records**:
```
FR <frame_num> <phone_info> [>pm <pm>] [>w <word>] <time_sec>
```

**Type markers**:
- `B` - Begin (start of word, includes word label)
- `I` - Inner (mid-word phoneme)
- `E` - End marker

**Phone markers**:
- `#` - Word boundary phone
- `$` - Inner phone
- `X...X` - Non-speech events (smacks, clicks, breath)

## Dependencies

**Core**: `soundfile`
**Scripts**: `praatio` (for TextGrid conversion)
**Development**: `pytest`, `tox`

## Usage Example

```python
from waxholm import Mix

mix = Mix("path/to/file.mix")

# Access transcriptions
text = mix.text
phonemes = mix.phoneme

# Get alignment data
phone_labels = mix.get_phone_label_tuples()  # [(start, end, phone), ...]
word_labels = mix.get_word_label_tuples()    # [(start, end, word), ...]

# Extract pronunciation dictionary
dictionary = mix.get_dictionary()  # {word: [[phonemes], ...]}

# Prepare for acoustic modeling
mix.prune_empty_segments()
mix.merge_plosives()
```

## Swedish Phoneme Inventory

The module handles Swedish phonemes with Waxholm-specific encoding:
- **Stops**: K, G, T, D, P, B (retroflex: 2T, 2D)
- **Fricatives**: F, V, S, SJ, TJ
- **Nasals**: M, N, NG
- **Vowels**: A, E, I, O, U, Y, Ä, Ö, Å (length marked with `:`)
- **Approximants**: J, L, R
- **Schwa**: E0

## Running Tests

```bash
pytest waxholm/tests/
```
