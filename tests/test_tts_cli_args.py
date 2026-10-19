from pathlib import Path
from unittest.mock import MagicMock, patch

from app.config import Settings
from app.tts import _synthesize_edge_cli


@patch("app.tts.subprocess.run")
@patch("app.tts.shutil.which", return_value="/usr/bin/edge-tts")
def test_edge_cli_uses_equals_form_for_pitch_and_rate(mock_which: MagicMock, mock_run: MagicMock, tmp_path: Path) -> None:
    dest = tmp_path / "out.mp3"

    def fake_run(cmd, **kwargs):
        dest.write_bytes(b"\xff" * 600)
        return MagicMock(returncode=0, stderr="", stdout="")

    mock_run.side_effect = fake_run
    settings = Settings(
        tts_voice="hi-IN-MadhurNeural",
        tts_rate="+5%",
        tts_pitch="-2Hz",
    )
    assert _synthesize_edge_cli("नमस्ते", dest, settings)
    cmd = mock_run.call_args[0][0]
    assert "--pitch=-2Hz" in cmd
    assert "--rate=+5%" in cmd
