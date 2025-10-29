"""Helpers for uploading drafts to the WeChat Official Account platform."""
from __future__ import annotations

import logging
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)

_API_ENDPOINT = "https://api.weixin.qq.com/cgi-bin/draft/add"


def _convert_content(content: str, is_markdown: bool) -> str:
    """Convert article content to HTML when requested."""
    if not is_markdown:
        return content

    try:  # pragma: no cover - optional dependency branch
        import markdown2  # type: ignore
    except ModuleNotFoundError:
        message = (
            "markdown2 library is not installed. Uploading original content without "
            "Markdown conversion."
        )
        logger.warning(message)
        print(message)
        return content

    return markdown2.markdown(content)


def upload_draft(
    access_token: str,
    title: str,
    content: str,
    *,
    is_markdown: bool = False,
    digest: str | None = None,
    show_cover_pic: int = 0,
    need_open_comment: int = 0,
    only_fans_can_comment: int = 0,
) -> str:
    """Upload an article draft to the WeChat Official Account platform.

    Parameters
    ----------
    access_token: str
        A valid WeChat access token.
    title: str
        The article title.
    content: str
        The article body content (HTML or Markdown).
    is_markdown: bool, optional
        When ``True`` the content will be converted from Markdown to HTML using
        :mod:`markdown2` if available.
    digest: str | None, optional
        Optional article digest/summary.
    show_cover_pic: int, optional
        Indicates whether to display the cover image (0 or 1).
    need_open_comment: int, optional
        Indicates whether comments are enabled for the article (0 or 1).
    only_fans_can_comment: int, optional
        Indicates whether only followers can comment on the article (0 or 1).

    Returns
    -------
    str
        The ``media_id`` returned by the WeChat API when the upload succeeds.
        Returns an empty string when the request fails and logs error details.
    """
    if not access_token:
        message = "Access token is required to upload drafts."
        logger.error(message)
        print(message)
        return ""

    if not title or not content:
        message = "Both title and content are required to upload drafts."
        logger.error(message)
        print(message)
        return ""

    html_content = _convert_content(content, is_markdown)

    url = f"{_API_ENDPOINT}?access_token={access_token}"

    article_payload: Dict[str, Any] = {
        "title": title,
        "content": html_content,
        "show_cover_pic": int(bool(show_cover_pic)),
        "need_open_comment": int(bool(need_open_comment)),
        "only_fans_can_comment": int(bool(only_fans_can_comment)),
    }

    if digest:
        article_payload["digest"] = digest

    payload = {"articles": [article_payload]}

    try:
        response = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as exc:
        message = f"Network error while uploading draft: {exc}"
        logger.error(message)
        print(message)
        return ""

    if response.status_code != 200:
        message = (
            "WeChat API responded with unexpected status code "
            f"{response.status_code} while uploading draft."
        )
        logger.error(message)
        print(message)
        return ""

    try:
        data = response.json()
    except ValueError as exc:  # pragma: no cover - defensive
        message = f"Failed to parse JSON response from WeChat API: {exc}"
        logger.error(message)
        print(message)
        return ""

    media_id = data.get("media_id")
    if isinstance(media_id, str) and media_id:
        return media_id

    errcode = data.get("errcode")
    errmsg = data.get("errmsg", "Unknown error")
    message = f"Failed to upload draft. errcode={errcode}, errmsg={errmsg}"
    logger.error(message)
    print(message)
    return ""
