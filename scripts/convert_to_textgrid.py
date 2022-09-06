#!/usr/bin/env python
# flake8: noqa

from collections import namedtuple
from waxholm import FR, Mix
from praatio import textgrid
from praatio.utilities.constants import Interval
import argparse
from pathlib import Path

from waxholm.audio import smp_to_wav


def main():
    parser = argparse.ArgumentParser(description='Convert .mix to Praat textgrid.')
    parser.add_argument('files', type=str, nargs='+', help='files to process')
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

    for file in args.files:
        path = Path(file)
        stem = path.stem
        if stem.endswith(".mix"):
            stem = stem[:-4]
        if stem.endswith(".smp"):
            stem = stem[:-4]
        if args.outpath:
            parent = args.outpath
        else:
            parent = path.parents[0]
        outfile = f"{parent}/{stem}.textgrid"

        if args.audio:
            smpfile = file.replace(".mix", "")
            wavfile = f"{parent}/{stem}.wav"
            smp_to_wav(smpfile, wavfile)

        mix = Mix(file)
        tg = textgrid.Textgrid()

        word_tier = textgrid.IntervalTier("words", mix.get_word_label_tuples())
        phone_tier = textgrid.IntervalTier("phones", mix.get_merged_plosives())

        tg.addTier(word_tier, reportingMode="error")
        tg.addTier(phone_tier, reportingMode="error")

        tg.save(str(outfile), format="long_textgrid", includeBlankSpaces=True, reportingMode="warning")


if __name__ == '__main__':
    main()
