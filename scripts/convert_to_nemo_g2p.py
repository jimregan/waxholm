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
# Collects a dictionary from the Waxholm data, suitable for use with NeMo's
# G2P trainer (i.e., skipping non-speech "phones").
# FIXME: pronunciations coming out in wrong order
# FIXME: join IPA characters

from waxholm import Mix
import argparse
from pathlib import Path
import json

from waxholm.utils import is_x_word, clean_pronunciation, map_to_ipa


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
    parser = argparse.ArgumentParser(description='Gathers a corpus of sentences and their transcriptions from the Waxholm data for input to NeMo\'s G2P trainer.')
    parser.add_argument('data_location', type=str, help='path to the Waxholm data')
    parser.add_argument('lexicon', type=str, help='path to place the gathered lexicon')
    parser.add_argument('--accented', help='include accent markers in the output', action='store_true')
    args = parser.parse_args()

    if args.lexicon:
        outpath = Path(args.lexicon)

        if outpath.exists():
            print(f"File exists with output path name ({outpath}); cowardly refusing to continue")
            exit()

    if args.accented:
        print("Not yet implemented")
        exit()

    data_location = Path(args.data_location)
    if not data_location.exists():
        print(f"Path to data ({data_location}) does not exist")
        exit()
    elif not data_location.is_dir():
        print(f"Path to data ({data_location}) exists, but is not a directory")
        exit()

    pairs = []

    for mixfile in data_location.glob("**/*.mix"):
        mix = Mix(filepath=mixfile)

        words = []
        prons = []
        for word_pair in mix.get_dictionary_list():
            if is_x_word(word_pair[0]):
                continue
            pron = clean_pronunciation(word_pair[1])
            pron = final_pass(pron)
            pron = "".join(map_to_ipa(pron.split(" ")))
            words.append(word_pair[0])
            prons.append(pron)
        graphemes = " ".join(words).replace(" .", ".").replace(" ,", ",")
        text = " ".join(prons).replace(" .", ".").replace(" ,", ",")
        pairs.append({"text_graphemes": graphemes, "text": text})

    with open(str(outpath), "w", encoding='utf8') as lexf:
        for pair in pairs:
            jsonout = json.dumps(pair)
            lexf.write(jsonout + "\n")


if __name__ == '__main__':
    main()
