#!/usr/bin/env python
# flake8: noqa

from waxholm import FR, Mix
from praatio import textgrid
from praatio.utilities.constants import Interval
import argparse
from pathlib import Path

from waxholm.audio import smp_to_wav


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


def get_merged_phone_intervals(mix, strategy = ""):
    times = mix.get_time_pairs()
    if mix.check_fr():
        labels = [fr.get_phone() for fr in mix.fr[0:-1]]
    else:
        labels = []
    if len(times) == len(labels):
        out = []
        last = None
        for z in zip(times, labels):
            if z[0][0] == z[0][1]:
                print(f"Start time ({z[0][0]}) same as end time ({z[0][1]})")
            if last == None:
                last = (z[0][0], z[0][1], z[1])
                continue
            else:
                cur = (z[0][0], z[0][1], z[1])
                if cur[1] == last[1]:
                    if strategy == "merge":
                        last = (last[0], last[1], f"{last[2]} {cur[2]}")
                    else:
                        last = (last[0], last[1], cur[2])
                else:
                    out.append(Interval(last[0], last[1], last[2]))
                    last = cur                
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

        word_tier = textgrid.IntervalTier("words", get_word_intervals(mix))
        phone_tier = textgrid.IntervalTier("phones", get_merged_phone_intervals(mix))

        tg.addTier(word_tier, reportingMode="error")
        tg.addTier(phone_tier, reportingMode="error")

        tg.save(str(outfile), format="long_textgrid", includeBlankSpaces=True, reportingMode="warning")


if __name__ == '__main__':
    main()
