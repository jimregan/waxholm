#!/usr/bin/env python

from waxholm import FR, Mix
from waxholm.audio import smp_to_wav
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description='Make fairseq input tsv from waxholm data.')
    parser.add_argument('inpath', type=str, help='path to input')
    parser.add_argument('outpath', type=str, help='path to place converted files')
    parser.add_argument('--phonetic', type=bool, help='use phonetic transcriptions', default=False)
    parser.add_argument('--audio', type=bool, help='also convert audio', default=False)
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
            smp_to_wav(smpfile, str(wavfile))

#        print(stem)


if __name__ == '__main__':
    main()
