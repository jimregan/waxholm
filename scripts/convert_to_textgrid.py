#!/usr/bin/env python
# flake8: noqa

from waxholm import FR, Mix
from praatio import textgrid
from praatio.utilities.constants import Interval
import argparse
from pathlib import Path


def get_phone_intervals(mix):
    times = mix.get_time_pairs()
    if mix.check_fr():
        labels = [fr.get_phone() for fr in mix.fr[0:-1]]
    else:
        labels = []
    if len(times) == len(labels):
        out = []
        for z in zip(times, labels):
            out.append(Interval(z[0][0], z[0][1], z[1]))
        return out
    else:
        return []


def get_word_intervals(mix):
    times = mix.get_time_pairs()
    if len(times) == len(mix.fr[0:-1]):
        out = []
        for z in zip(times, mix.fr[0:-1]):
            if z[1].type == "B":
                out.append(Interval(z[0][0], z[0][1], z[1].word))
        return out
    else:
        return []


def main():
    parser = argparse.ArgumentParser(description='Convert .mix to Praat textgrid.')
    parser.add_argument('files', type=str, nargs='+', help='files to process')
    parser.add_argument('--outpath', type=str, help='path to place converted files')
    args = parser.parse_args()

    for file in args.files:
        path = Path(file)
        stem = path.stem
        if args.outpath:
            parent = args.outpath
        else:
            parent = path.parents[0]
        outfile = parent / f"{stem}.textgrid"

        mix = Mix(file)
        tg = textgrid.Textgrid()

        word_tier = textgrid.IntervalTier("words", get_word_intervals(mix))
        phone_tier = textgrid.IntervalTier("phones", get_phone_intervals(mix))

        tg.addTier(word_tier, reportingMode="error")
        tg.addTier(phone_tier, reportingMode="error")

        tg.save(str(outfile), format="long_textgrid", includeBlankSpaces=True, reportingMode="warning")


if __name__ == '__main__':
    main()
