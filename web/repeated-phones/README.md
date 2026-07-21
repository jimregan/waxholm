# Repeated Phone Review

Static browser interface for stepping through adjacent repeated-phone candidates
from Waxholm source `.mix` files. It uses generated JSON plus review WAVs created
by `scripts/generate_repeated_phone_review.py`; it does not use TextGrid output.

Generate candidates and browser-playable audio from a Waxholm source tree:

```bash
python scripts/generate_repeated_phone_review.py /path/to/waxholm/data
```

Serve the repository root and open the app:

```bash
python -m http.server 8000
```

Then visit:

```text
http://localhost:8000/web/repeated-phones/
```

The generator detects adjacent phones with the same normalized label after
stripping leading stress marks and `#`/`$` prefixes. It reads phones and words
through `waxholm.Mix`, and converts matching source `.smp` files to review WAVs
through `waxholm.audio.smp_to_wav`.

Useful options:

```bash
python scripts/generate_repeated_phone_review.py /path/to/waxholm/data --context 0.5
python scripts/generate_repeated_phone_review.py /path/to/waxholm/data --no-audio
python scripts/generate_repeated_phone_review.py /path/to/waxholm/data --clean-audio-output
```
