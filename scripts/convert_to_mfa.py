#!/usr/bin/env python
# Copyright (c) 2023, Jim O'Regan for Språkbanken Tal
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
# flake8: noqa

from waxholm import Mix
import argparse
from pathlib import Path

from waxholm.audio import smp_to_wav
from waxholm.utils import replace_glottal_closures, fix_duration_markers


def strip_accents(text):
    for accent in "ˈ`ˌ":
        text = text.replace(accent, "")
    return text


def clean_silences(pron):
    if pron == "p:":
        return "SIL"
    split = pron.split(" ")
    start = 0
    end = len(split) - 1
    if split[start] == "p:":
        start += 1
    if split[end] == "p:":
        end -= 1
    return " ".join(split[start:end+1])


def clean_pronunciation(text):
    text = fix_duration_markers(text)
    text = strip_accents(text)
    text = replace_glottal_closures(text)
    text = clean_silences(text)
    return text


def clean_pron_set(prons):
    output = set()
    for pron in prons:
        output.add(clean_pronunciation(pron))
    return output


def cond_lc(text):
    if len(text) >= 2 and text[0] == "X" and text[-1] == "X":
        return text
    else:
        return text.lower()


def main():
    parser = argparse.ArgumentParser(description='Convert .mix to input to the Montreal Forced Aligner.')
    parser.add_argument('data_location', type=str, help='path to the Waxholm data')
    parser.add_argument('--outpath', type=str, help='path to place converted files')
    parser.add_argument('--audio', help='also convert audio', action='store_true')
    args = parser.parse_args()

    if args.outpath:
        outpath = Path(args.outpath)

        if outpath.exists() and not outpath.is_dir():
            print(f"File exists with output path name ({outpath}); cowardly refusing to continue")
            exit()

        if not outpath.exists() and not outpath.is_dir():
            outpath.mkdir()

    data_location = Path(args.data_location)
    if not data_location.exists():
        print(f"Path to data ({data_location}) does not exist")
        exit()
    elif not data_location.is_dir():
        print(f"Path to data ({data_location}) exists, but is not a directory")
        exit()

    lexicon = {}

    for mixfile in data_location.glob("**/*.mix"):
        stem = mixfile.stem
        mix = Mix(filepath=mixfile)

        txtfile = f"{outpath}/{stem}.txt"
        with open(txtfile, "w") as textoutput:
            text = mix.text.strip()
            text = text.lower()
            if text.endswith("."):
                text = text[:-1].strip()
            textoutput.write(text + "\n")

        if args.audio:
            smpfile = str(mixfile).replace(".mix", "")
            wavfile = f"{outpath}/{stem}.wav"
            smp_to_wav(smpfile, wavfile)

        for word_pair in mix.get_dictionary_list():
            word = cond_lc(word_pair[0])
            pron = word_pair[1]

            if not word in lexicon:
                lexicon[word] = set()
            lexicon[word].add(pron)

        with open(str(outpath / "lexicon.dict"), "w") as lexf:
            for word in lexicon:
                prons = clean_pron_set(lexicon[word])
                for pron in prons:
                    lexf.write(f"{word}\t{pron}\n")


if __name__ == '__main__':
    main()
