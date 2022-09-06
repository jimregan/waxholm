#!/usr/bin/env python
# flake8: noqa

from collections import namedtuple
from waxholm import FR, Mix
from praatio import textgrid
from praatio.utilities.constants import Interval
import argparse
from pathlib import Path

from waxholm.audio import smp_to_wav


Label = namedtuple('Label', ['start', 'end', 'label'])

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


def get_label_tuples(mix):
    times = get_phone_intervals(mix)
    return [Label(start = x[0], end = x[1], label = x[2]) for x in times]


def prune_empty_labels(labels, debug = False):
    out = []
    for label in labels:
        if label[0] != label[1]:
            out.append(label)
        else:
            if debug:
                print(f"Start: ({label[0]}); end: ({label[1]}); label {label[2]}")    
    return out


def merge_plosives(labels):
    i = 0
    sils = {
        "K": "k",
        "G": "g",
        "T": "t",
        "D": "d",
        "2T": "2t",
        "2D": "2d",
        "P": "p",
        "B": "b"
    }
    out = []
    while i < len(labels)-1:
        cur = labels[i]
        next = labels[i+1]
        cl = cur[2]
        if cl in sils.keys() and sils[cl] == next[2]:
            tmp = Label(start = cur[0], end = next[1], label = next[2])
            out.append(tmp)
            i += 2
        else:
            out.append(cur)
            i += 1
    return out


def get_merged_phone_intervals(mix):
    labels = get_label_tuples(mix)
    labels = prune_empty_labels(labels)
    merged = merge_plosives(labels)
    return [(x[0], x[1], x[2]) for x in merged]


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
