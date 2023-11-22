#!/usr/bin/env python

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

