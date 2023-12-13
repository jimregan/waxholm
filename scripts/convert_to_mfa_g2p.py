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
#
# Collects a dictionary from the Waxholm data, suitable for use with MFA's
# G2P trainer (i.e., skipping non-speech "phones").
# Note that the result should still be sorted using the standard Unix sort tool.

from waxholm import Mix
import argparse
from pathlib import Path
import re

from waxholm.utils import cond_lc, clean_pron_set, is_x_word


JUNK = [
    "XX\t\n",
    ".\t.\n"
]


def final_pass(pron):
    pron = pron.replace("T t", "T")
    pron = pron.replace("t", "T")
    pron = pron.replace("D d", "D")
    pron = pron.replace("d", "D")
    pron = pron.replace("G g", "G")
    pron = pron.replace("g", "G")
    pron = pron.replace("K k", "K")
    pron = pron.replace("k", "K")
    return pron


def main():
    parser = argparse.ArgumentParser(description='Gathers a lexicon from the Waxholm data for input to Montreal Forced Aligner\'s G2P trainer.')
    parser.add_argument('data_location', type=str, help='path to the Waxholm data')
    parser.add_argument('lexicon', type=str, help='path to place the gathered lexicon')
    parser.add_argument('--include_numbers', help='include numbers in the output', action='store_true')
    args = parser.parse_args()

    if args.lexicon:
        outpath = Path(args.lexicon)

        if outpath.exists():
            print(f"File exists with output path name ({outpath}); cowardly refusing to continue")
            exit()

    data_location = Path(args.data_location)
    if not data_location.exists():
        print(f"Path to data ({data_location}) does not exist")
        exit()
    elif not data_location.is_dir():
        print(f"Path to data ({data_location}) exists, but is not a directory")
        exit()

    lexicon = {}

    for mixfile in data_location.glob("**/*.mix"):
        mix = Mix(filepath=mixfile)

        for word_pair in mix.get_dictionary_list():
            if is_x_word(word_pair[0]):
                continue
            elif not args.include_numbers and re.match(".*[0-9].*", word_pair[0]):
                continue
            word = cond_lc(word_pair[0])
            pron = final_pass(word_pair[1])

            if not word in lexicon:
                lexicon[word] = set()
            lexicon[word].add(pron)

    lexicon = dict(sorted(lexicon.items()))
    with open(str(outpath), "w") as lexf:
        for word in lexicon:
            prons = clean_pron_set(lexicon[word], True)
            for pron in prons:
                cand = f"{word}\t{pron}\n"
                if not cand in JUNK and not cand.endswith("\t\n"):
                    lexf.write(cand)


if __name__ == '__main__':
    main()
