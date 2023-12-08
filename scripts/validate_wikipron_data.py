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

from waxholm import FR, Mix
import argparse
from pathlib import Path


def clean_wikipron(word: str, accents: bool = True) -> str:
    if accents:
        word = word.replace("²", "")
        word = word.replace("¹", "")
    word = word.replace("‿", "")
    return word


def main():
    parser = argparse.ArgumentParser(description='Validate Wikipron data')
    parser.add_argument('wikipron', type=str, help='path to wikipron data')
    parser.add_argument('--outpath', type=str, help='path to place converted files')
    args = parser.parse_args()

    if args.outpath:
        outpath = Path(args.outpath)

        if outpath.exists() and not outpath.is_dir():
            print(f"File exists with output path name ({outpath}); cowardly refusing to continue")
            exit()

        if not outpath.exists() and not outpath.is_dir():
            outpath.mkdir()

    wikipron = Path(args.wikipron)

