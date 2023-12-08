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


def check_candidates(word, pron):
    monowords = [
        "att",
        "och"
    ]
    len_pron = len(pron.split(" "))
    if len_pron != 1:
        return False
    if len(word) == 1 or word in monowords:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description='Convert .mix to input to the Montreal Forced Aligner.')
    parser.add_argument('data_location', type=str, help='path to the Waxholm data')
    args = parser.parse_args()

    data_location = Path(args.data_location)
    if not data_location.exists():
        print(f"Path to data ({data_location}) does not exist")
        exit()
    elif not data_location.is_dir():
        print(f"Path to data ({data_location}) exists, but is not a directory")
        exit()

    for mixfile in data_location.glob("**/*.mix"):
        mix = Mix(filepath=mixfile)

        for word_pair in mix.get_dictionary_list():
            word = word_pair[0]
            pron = word_pair[1]

            lword = word.lower()
            if check_candidates(lword, pron):
                print(f'File: {mixfile} ({word} : {pron})')            


if __name__ == '__main__':
    main()
