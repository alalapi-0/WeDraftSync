"""WeDraftSync command line entry point."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import logging

try:  # pragma: no cover - optional dependency handling
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - executed only when PyYAML is missing
    yaml = None  # type: ignore[assignment]

from utils.reader import load_articles_from_folder
from utils.wx_token import get_access_token


def _load_config(config_path: Path) -> dict[str, Any]:
    """Load configuration from ``config.yaml`` when available."""
    if not config_path.exists():
        logging.warning("Configuration file %s not found. Using default values.", config_path)
        return {}

    if yaml is None:
        logging.warning(
            "PyYAML is not installed. Unable to parse %s; falling back to defaults.",
            config_path,
        )
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as file:
            loaded_config = yaml.safe_load(file)
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Failed to load configuration file %s: %s", config_path, exc)
        return {}

    if not isinstance(loaded_config, dict):
        logging.warning("Configuration file %s did not contain a mapping.", config_path)
        return {}

    return {str(key): value for key, value in loaded_config.items()}


def main() -> None:
    """Load text articles and display a preview using project configuration."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config_path = Path("config.yaml")
    config = _load_config(config_path)

    folder = str(config.get("text_folder", "./articles"))
    use_title = bool(config.get("use_filename_as_title", True))

    articles = load_articles_from_folder(folder, use_title)

    if not articles:
        logging.info("No articles were loaded from folder %s.", folder)
        return

    for article in articles:
        preview = article["content"].replace("\n", " ")[:50]
        logging.info("标题: %s | 内容预览: %s", article["title"], preview)

    appid = config.get("wx_appid")
    appsecret = config.get("wx_appsecret")

    if appid and appsecret:
        token = get_access_token(str(appid), str(appsecret))
        print(f"当前 access_token：{token}")
    else:
        logging.info("WeChat credentials are not configured; skipping access token retrieval.")


if __name__ == "__main__":
    main()
