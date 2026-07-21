#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate data for reviewing repeated phones from Waxholm .mix files."""

import argparse
import json
import os
import shutil
from pathlib import Path

from waxholm import Mix
from waxholm.audio import smp_to_wav


DEFAULT_OUTPUT = Path("web/repeated-phones/repeated-phone-candidates.json")
DEFAULT_AUDIO_OUTPUT = Path("web/repeated-phones/audio")
STRESS_MARKS = "ˈˌ`"
PHONE_PREFIXES = "#$"


def normalize_phone(label):
    """Normalize lexical decorations while keeping the phonetic symbol."""
    return label.lstrip(STRESS_MARKS).lstrip(PHONE_PREFIXES)


def web_path(path, base_dir):
    return os.path.relpath(path, base_dir).replace(os.sep, "/")


def source_audio_for_mix(mixfile):
    """Return the source audio path for a Waxholm .smp.mix file."""
    return mixfile.parent / mixfile.stem


def audio_output_path(mixfile, audio_output):
    stem = mixfile.stem
    if stem.endswith(".smp"):
        stem = stem[:-4]
    return audio_output / "{}.wav".format(stem)


def ensure_wav(mixfile, wavfile, convert_audio):
    if wavfile.exists():
        return True
    if not convert_audio:
        return False

    smpfile = source_audio_for_mix(mixfile)
    if not smpfile.exists():
        return False

    wavfile.parent.mkdir(parents=True, exist_ok=True)
    smp_to_wav(smpfile, wavfile)
    return True


def enclosing_words(words, start, end):
    return [
        word
        for word in words
        if word and word[2] and word[1] > start and word[0] < end
    ]


def interval_dict(interval):
    return {
        "start": round(interval[0], 6),
        "end": round(interval[1], 6),
        "label": interval[2] or "",
    }


def collect_candidates(inpath, output, audio_output, context, convert_audio):
    candidates = []
    output_dir = output.parent
    seen_audio = {}

    for mixfile in sorted(inpath.glob("**/*.mix")):
        try:
            mix = Mix(mixfile)
            mix.prune_empty_silences(verbose=False)
        except Exception as exc:
            print("Skipping {}: {}".format(mixfile, exc))
            continue

        phones = mix.get_phone_label_tuples()
        words = mix.get_word_label_tuples(verbose=False)
        if len(phones) < 2:
            continue

        wavfile = audio_output_path(mixfile, audio_output)
        has_audio = seen_audio.get(wavfile)
        if has_audio is None:
            has_audio = ensure_wav(mixfile, wavfile, convert_audio)
            seen_audio[wavfile] = has_audio

        for index in range(len(phones) - 1):
            left = phones[index]
            right = phones[index + 1]
            left_label = left[2] or ""
            right_label = right[2] or ""
            normalized = normalize_phone(left_label)
            if not normalized or normalized != normalize_phone(right_label):
                continue

            start = left[0]
            boundary = left[1]
            end = right[1]
            nearby_start = max(0, index - 4)
            nearby_end = min(len(phones), index + 6)
            item_words = enclosing_words(words, start, end)
            audio = web_path(wavfile, output_dir) if has_audio else ""

            candidates.append(
                {
                    "id": "{}:{}".format(mixfile.relative_to(inpath), index + 1),
                    "file": str(mixfile.relative_to(inpath)),
                    "audio": audio,
                    "sourceAudio": str(source_audio_for_mix(mixfile).relative_to(inpath)),
                    "phone": normalized,
                    "leftLabel": left_label,
                    "rightLabel": right_label,
                    "start": round(start, 6),
                    "boundary": round(boundary, 6),
                    "end": round(end, 6),
                    "windowStart": round(max(0.0, start - context), 6),
                    "windowEnd": round(end + context, 6),
                    "phoneIndex": index + 1,
                    "segments": [interval_dict(phone) for phone in phones[nearby_start:nearby_end]],
                    "words": [interval_dict(word) for word in item_words],
                }
            )

    return candidates


def main():
    parser = argparse.ArgumentParser(
        description="Generate repeated-phone review data from Waxholm .mix files."
    )
    parser.add_argument("inpath", type=Path, help="Waxholm source data directory")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--audio-output", default=DEFAULT_AUDIO_OUTPUT, type=Path)
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Do not convert matching .smp files to WAV for browser playback.",
    )
    parser.add_argument(
        "--clean-audio-output",
        action="store_true",
        help="Remove the generated review WAV directory before writing new audio.",
    )
    parser.add_argument(
        "--context",
        default=0.35,
        type=float,
        help="Seconds of context before and after each repeated-phone span.",
    )
    args = parser.parse_args()

    if args.clean_audio_output and args.audio_output.exists():
        shutil.rmtree(args.audio_output)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audio_output.mkdir(parents=True, exist_ok=True)
    candidates = collect_candidates(
        args.inpath,
        args.output,
        args.audio_output,
        args.context,
        convert_audio=not args.no_audio,
    )
    payload = {
        "generatedBy": "scripts/generate_repeated_phone_review.py",
        "source": str(args.inpath),
        "candidateCount": len(candidates),
        "normalization": "strip leading stress marks and #/$ phone prefixes",
        "candidates": candidates,
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Wrote {} candidates to {}".format(len(candidates), args.output))


if __name__ == "__main__":
    main()
