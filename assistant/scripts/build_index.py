"""
Build the ChromaDB knowledge index from methodology text files.

Run from the repo root:
    python -m assistant.scripts.build_index

Reads all .txt files from assistant/data/methodology/, chunks them into
400-600 token windows with 75-token overlap, embeds with e5-small-v2,
and upserts into the ChromaDB collection.

Idempotent: existing docs with the same ID are overwritten.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from assistant.db.chroma import get_collection

METHODOLOGY_DIR = Path(__file__).resolve().parents[2] / "assistant" / "data" / "methodology"

# Target chunk size in approximate word count (words, not tokens; ~1 token ~ 0.75 words)
CHUNK_WORDS = 350     # ~450 tokens
OVERLAP_WORDS = 60    # ~75 tokens overlap


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """
    Extract key: value frontmatter lines at the top of the file.
    Returns (metadata_dict, remaining_body).
    """
    lines = text.splitlines()
    metadata: dict[str, str] = {}
    body_start = 0

    for i, line in enumerate(lines):
        if ":" in line and i < 10:
            key, _, val = line.partition(":")
            metadata[key.strip().lower()] = val.strip()
            body_start = i + 1
        else:
            break

    body = "\n".join(lines[body_start:]).strip()
    return metadata, body


def chunk_text(text: str, chunk_words: int, overlap_words: int) -> list[str]:
    """Split text into overlapping word-count chunks."""
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_words, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_words - overlap_words

    return chunks


def ingest_file(path: Path, collection) -> int:
    """Chunk and embed one .txt file. Returns number of chunks inserted."""
    raw = path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(raw)

    source = metadata.get("source", path.stem)
    indicator = metadata.get("indicator", "General")
    url = metadata.get("url", None)

    chunks = chunk_text(body, CHUNK_WORDS, OVERLAP_WORDS)
    ids = []
    documents = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        doc_id = f"{path.stem}_chunk_{i}"
        ids.append(doc_id)
        documents.append(chunk)
        meta = {
            "source": source,
            "indicator": indicator,
            "file": path.name,
            "chunk_index": i,
        }
        if url:
            meta["url"] = url
        metadatas.append(meta)

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


def main() -> None:
    txt_files = sorted(METHODOLOGY_DIR.glob("*.txt"))
    if not txt_files:
        print(f"No .txt files found in {METHODOLOGY_DIR}")
        return

    collection = get_collection()
    total = 0

    for path in txt_files:
        n = ingest_file(path, collection)
        print(f"  {path.name}: {n} chunk(s)")
        total += n

    print(f"\nDone. {total} chunks indexed into ChromaDB collection.")


if __name__ == "__main__":
    main()
