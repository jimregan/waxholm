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
from waxholm.utils import cond_lc, clean_pron_set


JUNK = [
    "XX\t\n",
    ".\t.\n"
]


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
        stem_parts = stem.split(".")
        speaker = stem_parts[0]
        mix = Mix(filepath=mixfile)

        spk_path = outpath / f"{speaker}"

        if not spk_path.is_dir():
            spk_path.mkdir()
        txtfile = f"{spk_path}/{stem}.txt"
        with open(txtfile, "w") as textoutput:
            text = mix.text.strip()
            text = " ".join([cond_lc(x) for x in text.split(" ")])
            if text.endswith("."):
                text = text[:-1].strip()
            textoutput.write(text + "\n")

        if args.audio:
            smpfile = str(mixfile).replace(".mix", "")
            wavfile = f"{spk_path}/{stem}.wav"
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
                    cand = f"{word}\t{pron}\n"
                    if not cand in JUNK:
                        lexf.write(cand)


if __name__ == '__main__':
    main()
