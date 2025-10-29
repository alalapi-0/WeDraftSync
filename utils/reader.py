"""Utility helpers for loading text articles from disk."""
from __future__ import annotations

from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def load_articles_from_folder(folder_path: str, use_filename_as_title: bool = True) -> list[dict[str, str]]:
    """Load ``.txt`` articles from ``folder_path`` sorted by file name.

    This helper iterates over the immediate children of ``folder_path`` and
    collects every file whose extension is ``.txt`` (case insensitive).
    Each file is read using UTF-8 encoding and truncated to the first 20,000
    characters to prevent excessive memory usage. Files that cannot be decoded
    are skipped with a warning message. The resulting list preserves the file
    name order, making it suitable for uploading drafts sequentially.

    Args:
        folder_path: Path to the directory containing ``.txt`` files.
        use_filename_as_title: When ``True`` the returned article titles will be
            derived from the file names (without extension). When ``False`` the
            first 100 characters of the article content will be used as the
            title instead (falling back to the file name when the content is
            empty).

    Returns:
        A list of dictionaries where each dictionary includes ``title`` and
        ``content`` keys representing an article. An empty list is returned when
        the directory is missing, not a directory, or does not contain ``.txt``
        files.
    """
    folder = Path(folder_path)
    articles: list[dict[str, str]] = []

    if not folder.exists() or not folder.is_dir():
        logger.warning("The folder '%s' does not exist or is not a directory.", folder)
        return articles

    txt_files = sorted(
        (path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".txt"),
        key=lambda path: path.name.lower(),
    )

    if not txt_files:
        logger.info("No .txt files found in folder '%s'.", folder)
        return articles

    for txt_file in txt_files:
        try:
            content = txt_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            logger.warning(
                "Skipping file '%s' because it could not be decoded with UTF-8.",
                txt_file,
            )
            continue
        except OSError as exc:
            logger.warning("Unable to read file '%s': %s", txt_file, exc)
            continue

        if len(content) > 20000:
            content = content[:20000]

        normalized_content = content.strip()

        if use_filename_as_title:
            title = txt_file.stem
        else:
            title_candidate = normalized_content[:100]
            title = title_candidate if title_candidate else txt_file.stem

        articles.append(
            {
                "title": title,
                "content": content,
            }
        )

    return articles
