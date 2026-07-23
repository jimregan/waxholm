"""
convert.py — Waxholm TextGrids -> pyshiro training data.

Reads the `phones` tier of each Waxholm .textgrid (produced by the waxholm
module's Mix.get_merged_plosives), normalizes the phone tokens, and writes:
  - <out_lab>/<stem>.lab   HTK 100ns integer labels (one per wav)
  - <out_phonemap>         phonemap.json for pyshiro (monophone, 3 states/phone)

Normalization (agreed conventions):
  - strip stress/accent marks  ˈ ` ˌ      (= waxholm.utils.strip_accents)
  - drop # (boundary) and ~ (compound) marks
  - drop + assimilation marker, preserving : length (= waxholm.utils.fix_duration_markers)
  - p:            -> sil   (matches waxholm.utils.clean_silences_mfa)
  - empty ""      -> sil
  - noise tokens pa/sm/öh/ha/kl kept as their own phones (like pyshiro's `br`)
  - retroflex 2-series (2N 2t 2d 2S ...) and plosive case (K/k ...) kept distinct

Each label file is padded with a leading/trailing `sil` so the phone sequence
covers the whole wav (0 .. wav_dur), which keeps the HSMM re-alignment honest.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import soundfile as sf

from pyshiro.labels import write_lab

SIL = "sil"


def strip_accents(text: str) -> str:            # waxholm.utils.strip_accents
    for accent in "ˈ`ˌ":
        text = text.replace(accent, "")
    return text


def fix_duration_markers(s: str) -> str:        # waxholm.utils.fix_duration_markers
    s += " "
    s = s.replace(":+ ", ": ")
    s = s.replace("+ ", " ")
    return s.strip()


# uppercase = plosive closure symbol, not a phoneme: fold into the release phone
# (waxholm.utils.SILS). e.g. merged-plosive "K" -> "k".
SILS = {"K": "k", "G": "g", "T": "t", "D": "d",
        "2T": "2t", "2D": "2d", "P": "p", "B": "b"}


def normalize(tok: str) -> str:
    t = strip_accents(tok)
    t = t.replace("#", "").replace("~", "")     # boundary + compound marks
    t = fix_duration_markers(t)
    t = t.strip()
    if t == "" or t == "p:":                     # empty gap / annotated pause -> silence
        return SIL
    return SILS.get(t, t)                         # fold plosive closures into release phone


_ITEM_RE = re.compile(r"item\s*\[\d+\]:")
_NAME_RE = re.compile(r'name\s*=\s*"([^"]*)"')
_IV_RE = re.compile(
    r'intervals\s*\[\d+\]:\s*xmin\s*=\s*([0-9.eE+\-]+)\s*'
    r'xmax\s*=\s*([0-9.eE+\-]+)\s*text\s*=\s*"([^"]*)"'
)


def parse_phones_tier(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    for block in _ITEM_RE.split(text)[1:]:
        m = _NAME_RE.search(block)
        if not m or m.group(1) != "phones":
            continue
        return [(float(s), float(e), t) for s, e, t in _IV_RE.findall(block)]
    return []


def convert_file(tg_path: Path, wav_path: Path, out_lab: Path) -> Counter:
    raw = parse_phones_tier(tg_path)
    if not raw:
        return Counter()

    wav_dur = sf.info(str(wav_path)).duration
    intervals = []

    # leading silence
    first_start = raw[0][0]
    if first_start > 1e-4:
        intervals.append((0.0, first_start, SIL))

    for s, e, tok in raw:
        ph = normalize(tok)
        # merge adjacent identical silences to keep the sequence tidy
        if intervals and intervals[-1][2] == ph == SIL and abs(intervals[-1][1] - s) < 1e-6:
            ps, _, _ = intervals[-1]
            intervals[-1] = (ps, e, SIL)
        else:
            intervals.append((s, e, ph))

    # trailing silence
    last_end = intervals[-1][1]
    if wav_dur - last_end > 1e-4:
        if intervals[-1][2] == SIL:
            ps, _, _ = intervals[-1]
            intervals[-1] = (ps, wav_dur, SIL)
        else:
            intervals.append((last_end, wav_dur, SIL))

    write_lab(intervals, out_lab)          # float seconds -> HTK 100ns integer
    return Counter(ph for _, _, ph in intervals)


def build_phonemap(phones) -> dict:
    # sil first, then noise phones, then the rest alphabetically — deterministic
    noise = [p for p in ("pa", "sm", "öh", "ha", "kl") if p in phones]
    rest = sorted(p for p in phones if p not in ({SIL} | set(noise)))
    ordered = [SIL] + noise + rest

    phone_map = {}
    for i, ph in enumerate(ordered):
        base = 3 * i
        phone_map[ph] = {
            "states": [
                {"dur": base + k, "out": [base + k, base + k, base + k]}
                for k in range(3)
            ]
        }
    return {"phone_map": phone_map}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tgrid_dir", type=Path,
                    default=Path("/Users/joregan/Playing/waxholm-module/waxholm/tgrid"))
    ap.add_argument("--out_lab", type=Path, default=Path("lab"))
    ap.add_argument("--out_phonemap", type=Path, default=Path("phonemap.json"))
    args = ap.parse_args()

    args.out_lab.mkdir(parents=True, exist_ok=True)

    tgrids = sorted(args.tgrid_dir.glob("*.textgrid"))
    print(f"TextGrids: {len(tgrids)}")

    total = Counter()
    n_ok = n_skip = 0
    for tg in tgrids:
        wav = tg.with_suffix(".wav")
        if not wav.exists():
            n_skip += 1
            continue
        counts = convert_file(tg, wav, args.out_lab / f"{tg.stem}.lab")
        if counts:
            total.update(counts)
            n_ok += 1
        else:
            n_skip += 1

    phones = set(total)
    phonemap = build_phonemap(phones)
    args.out_phonemap.write_text(
        json.dumps(phonemap, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"converted: {n_ok}  skipped: {n_skip}")
    print(f"phonemap: {len(phones)} phones -> {args.out_phonemap}")
    print("\nphone inventory (count desc):")
    for ph, c in total.most_common():
        print(f"  {ph:6s} {c:7d}")


if __name__ == "__main__":
    main()
