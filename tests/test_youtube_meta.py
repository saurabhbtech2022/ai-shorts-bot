from app.youtube import (
    _build_description,
    _build_tags,
    _build_title,
    english_summary_from_prompt,
    title_english_from_hindi,
)


def test_bilingual_title_with_part() -> None:
    hi = "लंकाकाण्ड · दोहा 65 · chaupai"
    title = _build_title(hi, 4840)
    assert "भाग 4840" in title
    assert "Part 4840" in title
    assert hi in title
    assert "Lanka Kand" in title
    assert "#Shorts" in title
    assert len(title) <= 100


def test_title_english_from_hindi() -> None:
    assert "Sundar Kand · Doha 41 · Chaupai" in title_english_from_hindi(
        "सुन्दरकाण्ड · दोहा 41 · chaupai"
    )


def test_english_summary_from_prompt() -> None:
    prompt = (
        "Ramcharitmanas illustration, लंकाकाण्ड, chaupai, "
        "The monkey assumed a small form., traditional Indian divine art"
    )
    assert english_summary_from_prompt(prompt) == "The monkey assumed a small form."


def test_description_includes_caption_and_hashtags() -> None:
    desc = _build_description(
        part_number=1,
        scene_title_hindi="बालकाण्ड · दोहा 1 · chaupai",
        scene_title_en="Bal Kand · Doha 1 · Chaupai",
        caption_hindi="जय श्री राम",
        english_summary="Opening verse.",
        hashtags="#Ramcharitmanas #Shorts",
    )
    assert "भाग 1" in desc
    assert "Part 1" in desc
    assert "जय श्री राम" in desc
    assert "Opening verse." in desc
    assert "#Ramcharitmanas" in desc
    assert "Cloudflare" in desc


def test_tags_include_part_and_kand() -> None:
    tags = _build_tags("लंकाकाण्ड · दोहा 1 · chaupai", 99)
    assert "Part 99" in tags
    assert "Ramcharitmanas" in tags
    assert "Lanka Kand" in tags
