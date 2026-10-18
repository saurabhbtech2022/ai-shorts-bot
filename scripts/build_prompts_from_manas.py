#!/usr/bin/env python3
"""
Build data/prompts.txt from Goswami Tulsidas Ramcharitmanas (book order).

Source JSON (Devanagari + Hindi meaning + English gloss):
  https://github.com/pawanprakashpal/RamayanaPath — data/tulsidas/*.json
  (~6087 verses → ~2030 days at 3 Shorts/day)

Usage:
  python scripts/build_prompts_from_manas.py
  python scripts/build_prompts_from_manas.py --granularity pair   # ~10.8k scenes, ~3600 days
  python scripts/build_prompts_from_manas.py --granularity line   # ~21k scenes (full chaupai lines)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

KAND_FILES = [
    ("bal-kand", "बालकाण्ड"),
    ("ayodhya-kand", "अयोध्याकाण्ड"),
    ("aranya-kand", "अरण्यकाण्ड"),
    ("kishkindha-kand", "किष्किन्धाकाण्ड"),
    ("sundar-kand", "सुन्दरकाण्ड"),
    ("lanka-kand", "लंकाकाण्ड"),
    ("uttar-kand", "उत्तरकाण्ड"),
]

BASE_URL = (
    "https://raw.githubusercontent.com/pawanprakashpal/RamayanaPath/master/data/tulsidas/{slug}.json"
)

HEADER = """# श्री रामचरित मानस — गोस्वामी तुलसीदास (पूरी पुस्तक, क्रम से)
# Source: RamayanaPath / IIT Kanpur aligned Tulsidas text (see data/ramcharitmanas/SOURCE.md)
# एक पंक्ति = एक YouTube Short | 3 Shorts/day → ~{days} din ({scenes} scenes)
# Format: title | English image prompt | Hindi caption [| narration] [| overlay]

"""


@dataclass(frozen=True)
class SceneRow:
    title: str
    image_en: str
    caption_hi: str


def _sanitize_field(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("|", " ").replace("\n", " ")).strip()


def _split_lines(original: str, line_count: int | None) -> list[str]:
    lines = [ln.strip() for ln in original.split("\n") if ln.strip()]
    if not lines and original.strip():
        lines = [original.strip()]
    if line_count and len(lines) < line_count and len(lines) == 1:
        # Some entries use ॥ markers on one physical line
        parts = re.split(r"(?<=[।॥])\s+", original.strip())
        lines = [p.strip() for p in parts if p.strip()]
    return lines


def _chunk_lines(lines: list[str], granularity: str) -> list[list[str]]:
    if not lines:
        return [[]]
    if granularity == "line":
        return [[ln] for ln in lines]
    if granularity == "pair":
        if len(lines) <= 2:
            return [lines]
        if len(lines) == 4:
            return [lines[:2], lines[2:]]
        # fallback: pairs
        out: list[list[str]] = []
        for i in range(0, len(lines), 2):
            out.append(lines[i : i + 2])
        return out
    return [lines]


def _caption_for_chunk(
    chunk_lines: list[str],
    hindi_translation: str,
    granularity: str,
    chunk_index: int,
    chunk_total: int,
) -> str:
    if hindi_translation:
        if granularity == "verse" or chunk_total == 1:
            cap = hindi_translation
        else:
            ht_lines = [ln.strip() for ln in hindi_translation.split("\n") if ln.strip()]
            if len(ht_lines) >= len(chunk_lines) and chunk_lines:
                start = chunk_index * len(chunk_lines)
                cap = " ".join(ht_lines[start : start + len(chunk_lines)])
            else:
                cap = hindi_translation
        return _sanitize_field(cap)
    return _sanitize_field(" ".join(chunk_lines))


def _image_prompt(kand_hi: str, english: str, verse_type: str) -> str:
    gloss = _sanitize_field(english)[:220] if english else ""
    if not gloss:
        gloss = f"Ramcharitmanas {verse_type} scene from {kand_hi}"
    return (
        f"Ramcharitmanas illustration, {kand_hi}, {verse_type}, "
        f"{gloss}, traditional Indian divine art, cinematic, respectful, 9:16 vertical"
    )[:480]


def download_kand_json(slug: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size > 1000:
        return
    url = BASE_URL.format(slug=slug)
    print(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, dest)


def iter_scenes(granularity: str) -> list[SceneRow]:
    rows: list[SceneRow] = []
    global_idx = 0
    for slug, kand_hi in KAND_FILES:
        path = ROOT / "data" / "ramcharitmanas" / "tulsidas" / f"{slug}.json"
        download_kand_json(slug, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        for group in data.get("dohaGroups", []):
            doha_num = group.get("dohaNumber", 0)
            for verse in group.get("verses", []):
                vtype = str(verse.get("type", "verse"))
                original = str(verse.get("original", ""))
                hindi_tr = str(verse.get("hindiTranslation", "") or "")
                english = str(verse.get("translation", "") or "")
                line_count = verse.get("lineCount")
                lines = _split_lines(original, line_count if isinstance(line_count, int) else None)
                chunks = _chunk_lines(lines, granularity)
                for ci, chunk in enumerate(chunks):
                    global_idx += 1
                    part = f" · {ci + 1}/{len(chunks)}" if len(chunks) > 1 else ""
                    title = _sanitize_field(f"{kand_hi} · दोहा {doha_num} · {vtype}{part}")
                    if len(title) > 80:
                        title = title[:77] + "..."
                    cap = _caption_for_chunk(chunk, hindi_tr, granularity, ci, len(chunks))
                    if not cap:
                        continue
                    rows.append(
                        SceneRow(
                            title=title,
                            image_en=_image_prompt(kand_hi, english, vtype),
                            caption_hi=cap[:500],
                        )
                    )
    return rows


def write_prompts(rows: list[SceneRow], out: Path) -> None:
    days = max(1, len(rows) // 3)
    parts = [HEADER.format(days=days, scenes=len(rows))]
    for row in rows:
        parts.append(f"{row.title} | {row.image_en} | {row.caption_hi}\n")
    out.write_text("".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build prompts.txt from Ramcharitmanas JSON")
    parser.add_argument(
        "--granularity",
        choices=("verse", "pair", "line"),
        default="verse",
        help="verse=1 Short per stanza (~6087, ~2030 days); pair=split 4-line chaupai (~10.8k); line=every line",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "prompts.txt",
    )
    args = parser.parse_args()
    rows = iter_scenes(args.granularity)
    if len(rows) < 100:
        raise SystemExit(f"Too few scenes ({len(rows)}); download failed?")
    write_prompts(rows, args.output)
    days = len(rows) // 3
    print(f"Wrote {len(rows)} scenes → {args.output}")
    print(f"At 3 Shorts/day ≈ {days} days (~{days / 365:.1f} years)")


if __name__ == "__main__":
    main()
