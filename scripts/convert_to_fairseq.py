#!/usr/bin/env python

from waxholm import FR, Mix
from waxholm.audio import smp_to_wav
from waxholm.utils import clean_x_words
import argparse
from pathlib import Path
import soundfile as sf


def _clean_phone(phone):
    # original accents
    phone = phone.replace("'", "").replace('\"', "").replace("`", "")
    # IPA-style accents
    phone = phone.replace("ˌ", "").replace("ˈ", "")
    # other markers
    phone = phone.replace("#", "").replace("+", "")
    return phone


DISCARD_PHONES = [
    "pa", "."
]


def clean_phones(phones):
    return [_clean_phone(x) for x in phones if x not in DISCARD_PHONES]


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
    manifest = str(outpath / "train.tsv")
    transcript = str(outpath / "train.ltr")

    with open(manifest, "w") as m_out, open(transcript, "w") as t_out:
        m_out.write(str(outpath.resolve()) + "\n")
        for file in inpath.glob("**/*.mix"):
            stem = file.stem.replace(".smp", "")
            frames = 0

            if args.audio:
                smpfile = str(file).replace(".mix", "")
                wavfile = str(outpath / f"{stem}.wav")
                smp_to_wav(smpfile, wavfile)
                frames, _ = sf.read(wavfile)

            mix = Mix(file)
            mix.prune_empty_silences(verbose=False)
            if args.phonetic:
                labels = mix.get_merged_plosives()
                labels = clean_phones(labels)
                label_text = " ".join(labels)
            else:
                labels = mix.get_word_label_tuples()
                labels = clean_x_words(labels)
                label_text = " ".join(labels)
                label_text = label_text.lower()

            m_out.write(f"{stem}.wav\t{len(frames)}\n")
            t_out.write(f"{label_text}\n")

if __name__ == '__main__':
    main()
