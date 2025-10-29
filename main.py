"""WeDraftSync command line entry point."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import logging

try:  # pragma: no cover - optional dependency handling
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - executed only when PyYAML is missing
    yaml = None  # type: ignore[assignment]

from utils.reader import load_articles_from_folder
from utils.uploader import upload_draft
from utils.wx_token import get_access_token

LOG_FILE_NAME = "upload_log.txt"


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


def _write_log_entry(log_path: Path, status: str, title: str, detail: str) -> None:
    """Append a formatted entry to the upload log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{timestamp} | {status} | 标题：{title} | {detail}\n"

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(entry)
    except OSError as exc:
        logging.error("Failed to write log entry to %s: %s", log_path, exc)


def _extract_credentials(config: dict[str, Any]) -> tuple[str, str]:
    """Return the appid and secret using multiple possible keys."""
    appid = config.get("appid") or config.get("wx_appid") or ""
    secret = config.get("secret") or config.get("wx_appsecret") or ""
    return str(appid), str(secret)


def _to_bool(value: Any, default: bool) -> bool:
    """Best-effort conversion of configuration values to booleans."""
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off"}:
            return False

    return bool(value)


def main() -> None:
    """Main entry point coordinating WeChat draft uploads."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config_path = Path("config.yaml")
    config = _load_config(config_path)

    text_folder = Path(str(config.get("text_folder", "./articles")))
    use_filename_as_title = _to_bool(config.get("use_filename_as_title", True), True)

    try:
        articles = load_articles_from_folder(str(text_folder), use_filename_as_title)
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Failed to load articles from %s: %s", text_folder, exc)
        return

    if not articles:
        logging.info("No articles were loaded from folder %s.", text_folder)
        return

    appid, appsecret = _extract_credentials(config)

    if not appid or not appsecret:
        logging.error("AppID or AppSecret is missing in the configuration.")
        return

    try:
        access_token = get_access_token(appid, appsecret)
    except Exception as exc:  # pylint: disable=broad-except
        logging.error("Unexpected error occurred while retrieving access token: %s", exc)
        return

    if not access_token:
        logging.error("Failed to retrieve a valid access token. Aborting upload.")
        return

    log_path = Path(LOG_FILE_NAME)
    total_articles = len(articles)
    success_count = 0
    failure_count = 0

    logging.info("开始上传，共 %s 篇文章。", total_articles)

    for index, article in enumerate(articles, start=1):
        title = article.get("title", "未命名")
        content = article.get("content", "")
        progress_prefix = f"[{index}/{total_articles}]"

        print(f"{progress_prefix} 正在上传：《{title}》")

        try:
            media_id = upload_draft(access_token, title, content)
        except Exception as exc:  # pylint: disable=broad-except
            failure_count += 1
            error_message = f"异常: {exc}"
            print(f"{progress_prefix} 上传失败：《{title}》 | {error_message}")
            logging.error("Failed to upload article '%s': %s", title, exc)
            _write_log_entry(log_path, "失败", title, f"原因: {error_message}")
            continue

        if media_id:
            success_count += 1
            print(f"{progress_prefix} 上传成功：《{title}》 | media_id: {media_id}")
            logging.info("文章《%s》上传成功，media_id=%s", title, media_id)
            _write_log_entry(log_path, "成功", title, f"media_id: {media_id}")
        else:
            failure_count += 1
            error_message = "上传失败，未返回 media_id"
            print(f"{progress_prefix} 上传失败：《{title}》 | {error_message}")
            logging.error("Article '%s' upload did not return a media_id.", title)
            _write_log_entry(log_path, "失败", title, f"原因: {error_message}")

    print("上传完成")
    print(f"成功: {success_count} 篇，失败: {failure_count} 篇")
    logging.info("上传完成，成功 %s 篇，失败 %s 篇。", success_count, failure_count)


if __name__ == "__main__":
    main()
