

from pathlib import Path
from typing import List

PREVIEW_CHARS = 400


def get_repo_root() -> Path:
    """Return the repository root (parent of the `Backend` directory).

    This avoids hard-coded relative strings like '../' and instead resolves the
    actual location of the current file at runtime.
    """
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    data_dir = get_repo_root() / "Data"
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found at expected location: {data_dir}")
    if not data_dir.is_dir():
        raise NotADirectoryError(f"Data path exists but is not a directory: {data_dir}")
    return data_dir


def list_text_files(data_dir: Path) -> List[Path]:
    """Return a sorted list of .txt files in the Data directory."""
    return sorted([p for p in data_dir.iterdir() if p.is_file() and p.suffix.lower() == ".txt"])


def load_text_file(path: Path) -> str:
    """Read and return text from `path` using UTF-8 encoding."""
    with path.open("r", encoding="utf-8") as f:
        return f.read()


def summarize_file(path: Path, preview_chars: int = PREVIEW_CHARS) -> None:
    text = load_text_file(path)
    print(f"File: {path.name}")
    print(f"Path: {path.resolve()}")
    print(f"Characters: {len(text)}")
    print("\nPreview:\n")
    preview = text[:preview_chars]
    print(preview)
    if len(text) > preview_chars:
        print("... [truncated]")
    print("-" * 60)


# --- Chunking utilities ---
import re


def split_sentences(text: str) -> List[str]:
    """A lightweight sentence splitter.

    This uses a simple regex to split on sentence-ending punctuation followed
    by whitespace. It is not a full NLP sentence-tagger but works well for
    cleanly formatted book text and avoids heavy dependencies.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def chunk_text_by_sentences(text: str, chunk_size: int = 200, overlap: int = 50) -> List[str]:
   
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    sentences = split_sentences(text)
    if not sentences:
        return []

    words_per_sentence = [len(s.split()) for s in sentences]
    chunks: List[str] = []
    start = 0
    n = len(sentences)

    while start < n:
        cum = 0
        end = start
        while end < n and cum < chunk_size:
            cum += words_per_sentence[end]
            end += 1
        # join sentences to form a chunk
        chunk = " ".join(sentences[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        # advance by roughly (chunk_size - overlap) words
        words_to_advance = max(1, chunk_size - overlap)
        advanced = 0
        new_start = start
        while new_start < n and advanced < words_to_advance:
            advanced += words_per_sentence[new_start]
            new_start += 1
        if new_start <= start:
            new_start = start + 1
        start = new_start

    return chunks


def chunk_text_by_words(text: str, chunk_size: int = 200, overlap: int = 50) -> List[str]:
    """Simple word-based chunker with fixed-size windows and overlap."""
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    words = text.split()
    if not words:
        return []

    step = chunk_size - overlap
    if step <= 0:
        raise ValueError("chunk_size must be greater than overlap")

    chunks: List[str] = []
    for i in range(0, len(words), step):
        chunk_words = words[i : i + chunk_size]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if i + chunk_size >= len(words):
            break

    return chunks


def summarize_and_chunk(path: Path, method: str = "sentence", chunk_size: int = 200, overlap: int = 50, preview_chunks: int = 3) -> None:
    """Summarize a file and print chunk statistics and short previews."""
    text = load_text_file(path)
    if method == "sentence":
        chunks = chunk_text_by_sentences(text, chunk_size=chunk_size, overlap=overlap)
    else:
        chunks = chunk_text_by_words(text, chunk_size=chunk_size, overlap=overlap)

    print(f"Total chunks: {len(chunks)}")
    for i, c in enumerate(chunks[:preview_chunks]):
        words = len(c.split())
        print(f"\nChunk {i+1} — {words} words — Preview:\n")
        print(c[:400])
        if len(c) > 400:
            print("... [truncated]")
    print("=" * 60)


def main() -> None:
    import argparse
    import fnmatch

    parser = argparse.ArgumentParser(description="Load and summarize text files from Data/")
    parser.add_argument("--chunk", action="store_true", help="Also chunk files after loading")
    parser.add_argument("--chunk-size", type=int, default=200, help="Chunk size in words")
    parser.add_argument("--overlap", type=int, default=50, help="Overlap size in words")
    parser.add_argument("--method", choices=("sentence", "word"), default="sentence", help="Chunking method")
    parser.add_argument("--preview-chunks", type=int, default=3, help="Number of chunk previews to show")
    parser.add_argument("--filter", type=str, default="*", help="Glob pattern to filter file names (e.g., '*Summary*.txt')")
    args = parser.parse_args()

    try:
        data_dir = get_data_dir()
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"Error: {exc}")
        return

    files = list_text_files(data_dir)
    if not files:
        print(f"No .txt files found in {data_dir}")
        return

    # Apply optional glob filter to filenames
    if args.filter and args.filter != "*":
        filtered = [p for p in files if fnmatch.fnmatch(p.name, args.filter)]
        if not filtered:
            print(f"No files matched the filter '{args.filter}' in {data_dir}")
            return
        files = filtered

    # Informative notices for common filename changes
    filenames = [p.name for p in files]
    if "Prologue.txt" not in filenames:
        print("Note: 'Prologue.txt' not found in Data/ (it may have been removed).")
    if "Bridgerton Summary.txt" in filenames:
        print("Note: 'Bridgerton Summary.txt' found and will be processed.")

    for path in files:
        try:
            summarize_file(path)
            if args.chunk:
                summarize_and_chunk(path, method=args.method, chunk_size=args.chunk_size, overlap=args.overlap, preview_chunks=args.preview_chunks)
        except Exception as exc:
            print(f"Failed to read {path.name}: {exc}")


if __name__ == "__main__":
    main()
    