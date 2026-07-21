"""Quick alignment sanity-check: align held-out test utterances with the trained
model and compare phone boundaries against the reference labels."""
from pathlib import Path
import numpy as np
import pyshiro
from pyshiro.labels import read_lab, segments_to_phoneme_intervals

TG = Path("/Users/joregan/Playing/waxholm-module/waxholm/tgrid")
model = pyshiro.load_hsmm("model/waxholm.hsmm")
pm = pyshiro.load_phonemap("phonemap.json")

test_wavs = sorted(Path("test_wav").glob("*.wav"))[:30]
all_err = []
per_file = []
for wav in test_wavs:
    ref = read_lab(Path("lab") / f"{wav.stem}.lab")
    phones = [p for _, _, p in ref]
    streams = pyshiro.extract_mfcc_from_file(wav)
    T = streams[0].shape[0]
    ss = pyshiro.build_state_sequence(phones, pm, T)
    segs, _ = pyshiro.forced_align_2pass(model, streams, ss,
                                         nodur_phonemes={"sil"}, hmm_cap=1000)
    pred = segments_to_phoneme_intervals(phones, segs)  # frames
    # internal boundaries: ref end times (sec) vs pred end times (frame*0.005)
    errs = []
    for i in range(len(phones) - 1):
        ref_b = ref[i][1]
        pred_b = pred[i][1] * 0.005
        errs.append(abs(ref_b - pred_b) * 1000)  # ms
    if errs:
        per_file.append((wav.stem, np.mean(errs), np.median(errs)))
        all_err.extend(errs)

all_err = np.array(all_err)
print(f"test files aligned: {len(per_file)}   internal boundaries: {len(all_err)}")
print(f"boundary abs error (ms):  mean {all_err.mean():.1f}   median {np.median(all_err):.1f}"
      f"   p90 {np.percentile(all_err,90):.1f}")
print(f"within 20ms: {100*np.mean(all_err<20):.1f}%   within 50ms: {100*np.mean(all_err<50):.1f}%")
print("\nper-file (stem, mean ms, median ms):")
for stem, m, md in per_file[:12]:
    print(f"  {stem:16s} mean {m:6.1f}  median {md:6.1f}")
