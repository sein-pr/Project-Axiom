from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
DEFAULT_CHUNK_SIZE = 100_000
DEFAULT_SAMPLE_ROWS = 50_000


def read_dataset_profile(
    path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    sample_rows: int = DEFAULT_SAMPLE_ROWS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")

    extension = path.suffix.lower()
    if extension == ".csv":
        return _read_csv_profile(path, chunk_size=chunk_size, sample_rows=sample_rows)

    frame = read_dataset(path)
    return frame, {
        "source_path": str(path),
        "processing_mode": "full_file",
        "total_rows": int(len(frame)),
        "sample_rows": int(len(frame)),
        "chunks_processed": 1,
        "chunk_size": None,
    }


def read_dataset(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")

    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Supported types: {supported}")

    if extension == ".csv":
        return pd.read_csv(path)

    return pd.read_excel(path)


def read_datasets(paths: list[Path]) -> dict[str, pd.DataFrame]:
    return {dataset_name(path): read_dataset(path) for path in paths}


def dataset_name(path: Path) -> str:
    name = path.stem.strip().lower()
    normalized = "".join(character if character.isalnum() else "_" for character in name)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_") or "dataset"


def _read_csv_profile(
    path: Path,
    chunk_size: int,
    sample_rows: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    chunks: list[pd.DataFrame] = []
    total_rows = 0
    chunks_processed = 0

    for chunk in pd.read_csv(path, chunksize=chunk_size):
        chunks_processed += 1
        total_rows += len(chunk)

        if sample_rows <= 0:
            continue

        remaining = sample_rows - sum(len(existing) for existing in chunks)
        if remaining > 0:
            chunks.append(chunk.head(remaining))

    sample = pd.concat(chunks, ignore_index=True) if chunks else pd.read_csv(path, nrows=0)
    metadata = {
        "source_path": str(path),
        "processing_mode": "chunked_csv",
        "total_rows": int(total_rows),
        "sample_rows": int(len(sample)),
        "chunks_processed": int(chunks_processed),
        "chunk_size": int(chunk_size),
    }
    return sample, metadata
