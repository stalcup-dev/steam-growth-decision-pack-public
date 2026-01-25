from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple
import logging

import pandas as pd
from pandas.io.parsers import TextFileReader

LOGGER = logging.getLogger(__name__)
ENCODINGS: Tuple[str, ...] = ("utf-8", "cp1252", "latin1")


class _BadLineCounter:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self, _bad_line: Iterable[str]) -> None:
        self.count += 1
        return None


class _ChunkIterator:
    def __init__(
        self, reader: TextFileReader, counter: _BadLineCounter | None, path: Path, encoding: str, sep: object
    ):
        self._reader = reader
        self._counter = counter
        self._path = path
        self._encoding = encoding
        self._sep = sep
        self._logged = False

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self._reader)
        except StopIteration:
            self._log_skipped()
            raise

    def _log_skipped(self) -> None:
        if self._logged or self._counter is None or self._counter.count == 0:
            return
        self._logged = True
        LOGGER.warning(
            "safe_read_csv skipped %d bad lines path=%s encoding=%s sep=%s",
            self._counter.count,
            self._path,
            self._encoding,
            self._sep,
        )


def _log_success(path: Path, encoding: str, sep: object, used_fallback: bool) -> None:
    LOGGER.info(
        "safe_read_csv success path=%s encoding=%s sep=%s fallback=%s",
        path,
        encoding,
        sep,
        used_fallback,
    )


def safe_read_csv(path: str | Path, **kwargs):
    path = Path(path)
    kwargs = dict(kwargs)
    kwargs.pop("low_memory", None)

    requested_on_bad_lines = kwargs.get("on_bad_lines")
    if requested_on_bad_lines is None:
        requested_on_bad_lines = "skip"
    use_counter = requested_on_bad_lines in ("skip", None)
    if requested_on_bad_lines == "skip":
        kwargs.pop("on_bad_lines", None)

    sep = kwargs.get("sep")
    last_error: Exception | None = None

    for encoding in ENCODINGS:
        counter = _BadLineCounter() if use_counter else None
        primary_kwargs = dict(kwargs)
        primary_kwargs["encoding"] = encoding
        if use_counter:
            primary_kwargs["on_bad_lines"] = counter
            primary_kwargs["engine"] = "python"

        try:
            result = pd.read_csv(path, **primary_kwargs)
            _log_success(path, encoding, sep, used_fallback=False)
            if isinstance(result, TextFileReader):
                return _ChunkIterator(result, counter, path, encoding, sep)
            if counter is not None and counter.count:
                LOGGER.warning(
                    "safe_read_csv skipped %d bad lines path=%s encoding=%s sep=%s",
                    counter.count,
                    path,
                    encoding,
                    sep,
                )
            return result
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        except Exception as exc:
            last_error = exc

        fallback_counter = _BadLineCounter() if use_counter else None
        fallback_kwargs = dict(primary_kwargs)
        fallback_kwargs["engine"] = "python"
        fallback_kwargs["sep"] = None
        if use_counter:
            fallback_kwargs["on_bad_lines"] = fallback_counter

        try:
            result = pd.read_csv(path, **fallback_kwargs)
            _log_success(path, encoding, None, used_fallback=True)
            if isinstance(result, TextFileReader):
                return _ChunkIterator(result, fallback_counter, path, encoding, None)
            if fallback_counter is not None and fallback_counter.count:
                LOGGER.warning(
                    "safe_read_csv skipped %d bad lines path=%s encoding=%s sep=%s",
                    fallback_counter.count,
                    path,
                    encoding,
                    None,
                )
            return result
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        except Exception as exc:
            last_error = exc
            continue

    LOGGER.error(
        "safe_read_csv failed path=%s encodings=%s error=%s",
        path,
        ENCODINGS,
        last_error,
    )
    if last_error is None:
        raise ValueError(f"safe_read_csv failed for {path}")
    raise last_error
