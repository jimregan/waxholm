# Waxholm

A Python library for reading and processing transcription data from the **Waxholm Speech Corpus**, a Swedish speech database developed by KTH (Royal Institute of Technology). The module parses `.mix` annotation files containing detailed phonetic and word-level alignments.

**License**: Apache 2.0
**Developed for**: Språkbanken Tal (Swedish Language Bank)

## Installation

```bash
pip install waxholm
```

## Usage

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

## Core Classes

### Mix

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

### FR

Represents a single **Frame Record** from a `.mix` file.

**Key attributes**:
- `frame` - Frame number
- `seconds` - Time in seconds
- `type` - B (Begin), I (Inner), or E (End)
- `phone` - Phoneme symbol
- `word` - Orthographic word
- `pm` - Postulated pronunciation

## Conversion Scripts

The `scripts/` directory contains utilities for exporting to various formats:

| Script | Purpose |
|--------|---------|
| `convert_to_mfa.py` | Montreal Forced Aligner format with lexicon |
| `convert_to_mfa_g2p.py` | MFA format for G2P training |
| `convert_to_nemo_g2p.py` | NVIDIA NeMo G2P format |
| `convert_to_fairseq.py` | Facebook FairSeq format |
| `convert_to_textgrid.py` | Praat TextGrid format |
| `check_lexicon.py` | Validate lexicon entries |

## Audio Conversion

The module can convert Waxholm's SMP audio format to WAV:

```python
from waxholm.audio import smp_to_wav

smp_to_wav("input.smp", "output.wav")
```

## Data Format

The `.mix` file format uses **FR records**:
```
FR <frame_num> <phone_info> [>pm <pm>] [>w <word>] <time_sec>
```

**Type markers**:
- `B` - Begin (start of word, includes word label)
- `I` - Inner (mid-word phoneme)
- `E` - End marker

## Swedish Phoneme Inventory

The module handles Swedish phonemes with Waxholm-specific encoding:
- **Stops**: K, G, T, D, P, B (retroflex: 2T, 2D)
- **Fricatives**: F, V, S, SJ, TJ
- **Nasals**: M, N, NG
- **Vowels**: A, E, I, O, U, Y, Ä, Ö, Å (length marked with `:`)
- **Approximants**: J, L, R
- **Schwa**: E0

## Dependencies

- **Core**: `soundfile`
- **Scripts**: `praatio` (for TextGrid conversion)

## Running Tests

```bash
pytest waxholm/tests/
```
