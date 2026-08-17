from pathlib import Path

from src.main import main, print_summary
from src.organizer import RunResult
from tests.helpers import make_jpeg


def _write_env(tmp_path: Path, source: Path, output: Path) -> Path:
    env = tmp_path / ".env"
    env.write_text(
        "\n".join(
            [
                f"SOURCE_DIR={source}",
                f"OUTPUT_DIR={output}",
                "EXTENSIONS=.jpg,.jpeg,.heic,.heif,.png,.tiff,.tif",
                "NO_DATE_FOLDER=no_date",
                "OUTPUT_PREFIX=extraction_",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return env


def test_main_success_copies_and_returns_zero(tmp_path: Path, capsys):
    source = tmp_path / "foto"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()
    make_jpeg(source / "a.jpg", datetime_original="2024:03:15 10:00:00")
    env = _write_env(tmp_path, source, output)
    assert main(env) == 0
    captured = capsys.readouterr()
    assert "Files scanned: 1" in captured.out
    assert "2024_03_15" in captured.out


def test_main_missing_env_returns_one(tmp_path: Path, capsys):
    assert main(tmp_path / "nope.env") == 1
    captured = capsys.readouterr()
    assert captured.err
    assert "Files scanned" not in captured.out


def test_main_empty_source_returns_one(tmp_path: Path, capsys):
    source = tmp_path / "foto"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()
    env = _write_env(tmp_path, source, output)
    assert main(env) == 1
    captured = capsys.readouterr()
    assert "No files" in captured.err
    assert "Files scanned" not in captured.out


def test_print_summary_includes_counts(capsys):
    result = RunResult(
        files_seen=3,
        copied_by_date={"2024_03_15": 2},
        no_date_count=1,
        copy_errors=["x.jpg: boom"],
    )
    print_summary(result)
    text = capsys.readouterr().out
    assert "Files scanned: 3" in text
    assert "2024_03_15: 2" in text
    assert "No date: 1" in text
    assert "x.jpg: boom" in text
