import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# HTTP 요청 타임아웃 (초)
WEB_FETCH_TIMEOUT = 30.0
PDF_PARSE_TIMEOUT = 60.0
# 노트 제목 자동 추출 최대 길이
NOTE_TITLE_MAX_LENGTH = 50
# HTML 파싱 시 제거할 태그 목록
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]
# Upstage Document Parse API 엔드포인트
UPSTAGE_DOCUMENT_PARSE_URL = "https://api.upstage.ai/v1/document-ai/document-parse"


async def fetch_url_content(url: str) -> tuple[str, str]:
    """URL에서 HTML을 가져와 클린 텍스트 추출. (title, content) 튜플 반환."""
    async with httpx.AsyncClient(timeout=WEB_FETCH_TIMEOUT) as client:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = await client.get(url, headers=headers, follow_redirects=True)
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title:
        title = soup.title.string or ""

    # article > main > body 순서로 콘텐츠 탐색
    article = soup.find("article") or soup.find("main") or soup.find("body")

    if article:
        for tag in article.find_all(NOISE_TAGS):
            tag.decompose()

        text = article.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text)
    else:
        text = ""

    return title.strip(), text.strip()


def extract_domain(url: str) -> str:
    """URL에서 도메인 추출."""
    parsed = urlparse(url)
    return parsed.netloc


async def process_web_content(url: str) -> dict:
    """웹 URL을 처리하여 구조화된 데이터 반환.

    Returns:
        {title, content, source_url, source_domain} dict
    """
    title, content = await fetch_url_content(url)

    if not title:
        title = f"Page from {extract_domain(url)}"

    return {"title": title, "content": content, "source_url": url, "source_domain": extract_domain(url)}


async def process_pdf_content(file_bytes: bytes, filename: str) -> dict:
    """Upstage Document Parse API로 PDF 파일 처리.

    Returns:
        {title, content, source_url} dict
    """
    from app.config.settings import get_settings

    settings = get_settings()
    if not settings.UPSTAGE_API_KEY:
        raise ValueError("UPSTAGE_API_KEY is not configured")

    async with httpx.AsyncClient(timeout=PDF_PARSE_TIMEOUT) as client:
        response = await client.post(
            UPSTAGE_DOCUMENT_PARSE_URL,
            headers={"Authorization": f"Bearer {settings.UPSTAGE_API_KEY}"},
            files={"document": (filename, file_bytes, "application/pdf")},
            data={"output_formats": '["text"]'},
        )
        response.raise_for_status()
        result = response.json()

    content = result.get("content", {}).get("text", "")
    if not content:
        elements = result.get("elements", [])
        content = "\n".join(el.get("text", "") for el in elements if el.get("text"))

    title = filename.rsplit(".", 1)[0] if "." in filename else filename

    return {
        "title": title,
        "content": content,
        "source_url": None,
    }


async def process_note_content(content: str, memo: str | None = None) -> dict:
    """텍스트/노트 콘텐츠 처리. 첫 줄에서 NOTE_TITLE_MAX_LENGTH 이내로 제목을 추출.

    Returns:
        {title, content, source_url} dict
    """
    lines = content.strip().split("\n")
    first_line = lines[0] if lines else ""

    title = (
        first_line[:NOTE_TITLE_MAX_LENGTH] + "..."
        if len(first_line) > NOTE_TITLE_MAX_LENGTH
        else first_line or "Untitled Note"
    )

    final_content = content
    if memo:
        final_content = f"{content}\n\n---\n**My thoughts:**\n{memo}"

    return {"title": title, "content": final_content, "source_url": None}
