# Ramcharitmanas source data

The bot can build `data/prompts.txt` from **Goswami Tulsidas — Ramcharitmanas** in reading order.

## Files

- `tulsidas/*.json` — downloaded by `scripts/build_prompts_from_manas.py` if missing (~7 MB total)

## Attribution

JSON structure and aligned text from the open [RamayanaPath](https://github.com/pawanprakashpal/RamayanaPath) project (Tulsidas edition, Devanagari original + Hindi meaning + English gloss). The Awadhi/Hindi source text is public domain.

## Regenerate prompts

```bash
# ~6087 scenes → ~2030 days @ 3 Shorts/day (recommended)
python scripts/build_prompts_from_manas.py

# ~10800 scenes → ~3600 days (finer, 4-line chaupai split in halves)
python scripts/build_prompts_from_manas.py --granularity pair
```

After regenerating, reset `data/state.json` `"index": 0` if you want to start from Bal Kand mangalacharan again.
