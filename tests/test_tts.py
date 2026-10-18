from app.tts import build_atempo_chain


def test_build_atempo_chain_single_in_range() -> None:
    assert build_atempo_chain(1.25) == "atempo=1.2500"


def test_build_atempo_chain_slow_requires_multiple_filters() -> None:
    chain = build_atempo_chain(0.22)
    assert chain.count("atempo=") >= 2
    assert chain.startswith("atempo=0.5")
