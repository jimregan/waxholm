#!/usr/bin/env python

from waxholm import FR, Mix
from waxholm.audio import smp_to_wav
import argparse
from pathlib import Path


def _clean_phone(phone):
    # original accents
    phone = phone.replace("'", "").replace('\"', "").replace("`", "")
    # IPA-style accents
    phone = phone.replace("ˌ", "").replace("ˈ", "")
    # other markers
    phone = phone.replace("#", "").replace("+", "")
    return phone


def _clean_word(word):
    if "XX" in word:
        return ""
    else:
        return word


def clean_words(words):
    return [x for x in words if _clean_word(x) != ""]


def main():
    parser = argparse.ArgumentParser(description='Make fairseq input tsv from waxholm data.')
    parser.add_argument('inpath', type=str, help='path to input')
    parser.add_argument('outpath', type=str, help='path to place converted files')
    parser.add_argument('--phonetic', help='use phonetic transcriptions', action='store_true')
    parser.add_argument('--audio', help='also convert audio', action='store_true')
    args = parser.parse_args()

    inpath = Path(args.inpath)
    outpath = Path(args.outpath)

    if outpath.exists() and not outpath.is_dir():
        print(f"File exists with output path name ({outpath}); cowardly refusing to continue")
        exit()

    if not outpath.exists() and not outpath.is_dir():
        outpath.mkdir()

    for file in inpath.glob("**/*.mix"):
        stem = file.stem.replace(".smp", "")
        if args.audio:
            smpfile = str(file).replace(".mix", "")
            wavfile = outpath / f"{stem}.wav"
            smp_to_wav(smpfile, wavfile)

#        print(stem)


if __name__ == '__main__':
    main()
