"""Alignment sanity-check: align held-out test utterances with the trained model
and compare phone boundaries against the reference labels."""
import argparse
from pathlib import Path

import numpy as np

import pyshiro
from pyshiro.labels import read_lab, segments_to_phoneme_intervals


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", type=Path, default=Path("model/waxholm.hsmm"))
    ap.add_argument("--phonemap", type=Path, default=Path("phonemap.json"))
    ap.add_argument("--wav_dir", type=Path, default=Path("test_wav"))
    ap.add_argument("--lab_dir", type=Path, default=Path("lab"))
    ap.add_argument("--n", type=int, default=30, help="max files to evaluate")
    args = ap.parse_args()

    model = pyshiro.load_hsmm(args.model)
    pm = pyshiro.load_phonemap(args.phonemap)

    all_err = []
    per_file = []
    for wav in sorted(args.wav_dir.glob("*.wav"))[:args.n]:
        ref = read_lab(args.lab_dir / f"{wav.stem}.lab")
        phones = [p for _, _, p in ref]
        streams = pyshiro.extract_mfcc_from_file(wav)
        T = streams[0].shape[0]
        ss = pyshiro.build_state_sequence(phones, pm, T)
        segs, _ = pyshiro.forced_align_2pass(model, streams, ss,
                                             nodur_phonemes={"sil"}, hmm_cap=1000)
        pred = segments_to_phoneme_intervals(phones, segs)
        errs = [abs(ref[i][1] - pred[i][1] * 0.005) * 1000
                for i in range(len(phones) - 1)]
        if errs:
            per_file.append((wav.stem, np.mean(errs), np.median(errs)))
            all_err.extend(errs)

    all_err = np.array(all_err)
    print(f"test files aligned: {len(per_file)}   internal boundaries: {len(all_err)}")
    print(f"boundary abs error (ms):  mean {all_err.mean():.1f}   median {np.median(all_err):.1f}"
          f"   p90 {np.percentile(all_err, 90):.1f}")
    print(f"within 20ms: {100 * np.mean(all_err < 20):.1f}%   "
          f"within 50ms: {100 * np.mean(all_err < 50):.1f}%")
    print("\nper-file (stem, mean ms, median ms):")
    for stem, m, md in per_file[:12]:
        print(f"  {stem:16s} mean {m:6.1f}  median {md:6.1f}")


if __name__ == "__main__":
    main()
