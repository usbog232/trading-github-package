import os
from pathlib import Path

from env_loader import load_local_env


def test_env_loader_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    load_local_env()
    assert True
