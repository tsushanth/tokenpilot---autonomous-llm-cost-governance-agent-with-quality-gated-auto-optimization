import shutil

import pytest

from tokenpilot.cli import main


@pytest.fixture
def runs_dir(tmp_path):
    d = tmp_path / "runs"
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_support_bot_ships(capsys, runs_dir):
    exit_code = main(["run", "examples/support_bot_task.json", "--mock", "--runs-dir", str(runs_dir)])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "SHIP" in out
    assert "REJECT" not in out


def test_refund_bot_rejects(capsys, runs_dir):
    exit_code = main(["run", "examples/refund_bot_task.json", "--mock", "--runs-dir", str(runs_dir)])

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "REJECT" in out
    assert "forfeited" in out


def test_run_is_persisted_and_listable(capsys, runs_dir):
    main(["run", "examples/support_bot_task.json", "--mock", "--runs-dir", str(runs_dir)])
    capsys.readouterr()

    exit_code = main(["list-runs", "support_bot", "--runs-dir", str(runs_dir)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "support_bot" in out
    assert "SHIP" in out
