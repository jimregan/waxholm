#!/usr/bin/env python

from waxholm import FR, Mix
from waxholm.audio import smp_to_wav
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
    manifest = str(outpath / "train.tsv")
    transcript = str(outpath / "train.ltr")

    with open(manifest, "w") as m_out, open(transcript, "w") as t_out:
        m_out.write(str(outpath) + "\n")
        for file in inpath.glob("**/*.mix"):
            stem = file.stem.replace(".smp", "")
            frames = 0

            if args.audio:
                smpfile = str(file).replace(".mix", "")
                wavfile = outpath / f"{stem}.wav"
                smp_to_wav(smpfile, wavfile)
                frames, _ = sf.read(wavfile)

            mix = Mix(file)
            mix.prune_empty_silences(verbose=True)
            if args.phonetic:
                labels = mix.get_phone_label_tuples()
                labels = [_clean_phone(x[2]) for x in labels]
                label_text = " ".join(labels)
            else:
                labels = mix.get_word_label_tuples()
                labels = clean_words(labels)
                label_text = " ".join(labels)
                label_text = label_text.lower()

            m_out.write(f"{stem}.wav\t{len(frames)}\n")
            t_out.write(f"{label_text}\n")

if __name__ == '__main__':
    main()
