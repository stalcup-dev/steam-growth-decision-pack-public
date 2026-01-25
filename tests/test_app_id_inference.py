from pathlib import Path

from src.normalize import infer_app_id_from_path


def test_infer_app_id_from_numeric_stem():
    assert infer_app_id_from_path(Path("data/raw/10.csv")) == 10
    assert infer_app_id_from_path(Path("data/raw/10090.csv")) == 10090


def test_infer_app_id_from_mixed_stem():
    assert infer_app_id_from_path(Path("data/raw/app_12345_history.csv")) == 12345


def test_infer_app_id_from_no_digits():
    assert infer_app_id_from_path(Path("data/raw/no_digits.csv")) is None
