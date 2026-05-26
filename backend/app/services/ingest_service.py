import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.exceptions import InvalidUrlError, UnsupportedContentTypeError, UpstreamFetchError

# HTTP 요청 타임아웃 (초)
WEB_FETCH_TIMEOUT = 15.0
HEAD_TIMEOUT = 5.0
PDF_PARSE_TIMEOUT = 60.0
# 노트 제목 자동 추출 최대 길이
NOTE_TITLE_MAX_LENGTH = 50
# HTML 파싱 시 제거할 태그 목록
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]
# Upstage Document Parse API 엔드포인트
UPSTAGE_DOCUMENT_PARSE_URL = "https://api.upstage.ai/v1/document-ai/document-parse"


# SSRF 방어용 차단 IP 대역
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]


def validate_url(url: str) -> str:
    """URL 스킴 및 내부 IP 차단 검증 (SSRF 방어).

    http/https만 허용하고, 내부 네트워크 IP로 해석되는 호스트를 차단한다.
    검증 통과 시 정규화된 URL을 반환한다.

    Raises:
        InvalidUrlError: 스킴/호스트명/SSRF 정책 위반. router에서 HTTPException으로 매핑.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise InvalidUrlError(
            f"허용되지 않는 URL 스킴: {parsed.scheme}. http 또는 https만 지원합니다."
        )

    hostname = parsed.hostname
    if not hostname:
        raise InvalidUrlError("URL에서 호스트명을 추출할 수 없습니다.")

    # DNS 해석 후 IP 주소가 내부 대역인지 검사
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise InvalidUrlError(f"호스트를 해석할 수 없습니다: {hostname}") from None

    for addr_info in addr_infos:
        ip = ipaddress.ip_address(addr_info[4][0])
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                raise InvalidUrlError("내부 네트워크 주소에 대한 요청은 허용되지 않습니다.")

    return url


async def validate_content_type(url: str) -> None:
    """HEAD 요청으로 Content-Type 사전 검증.

    text/html 또는 text/plain이 아닌 응답은 거부한다.
    HEAD를 지원하지 않는 서버는 조용히 통과시킨다.

    Raises:
        UnsupportedContentTypeError: text/html/plain 외 응답
        UpstreamFetchError: 타임아웃/연결 실패 (수복 불가)
    """
    try:
        async with httpx.AsyncClient(timeout=HEAD_TIMEOUT) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = await client.head(url, headers=headers, follow_redirects=True)

            content_type = resp.headers.get("content-type", "")
            if (
                resp.status_code < 400
                and content_type
                and "text/html" not in content_type
                and "text/plain" not in content_type
            ):
                raise UnsupportedContentTypeError(
                    f"지원하지 않는 콘텐츠 타입: {content_type}. text/html 또는 text/plain만 지원합니다."
                )
    except UnsupportedContentTypeError:
        raise
    except httpx.TimeoutException:
        raise UpstreamFetchError(
            "URL 접근 시 타임아웃이 발생했습니다. 잠시 후 다시 시도해주세요."
        ) from None
    except httpx.ConnectError:
        raise UpstreamFetchError("URL에 연결할 수 없습니다. 주소를 확인해주세요.") from None
    except Exception:
        # HEAD를 지원하지 않는 서버 등 기타 오류는 무시하고 GET으로 진행
        pass


_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
_MAX_REDIRECTS = 5


async def _fetch_with_redirect_validation(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
) -> httpx.Response:
    """리다이렉트를 수동으로 추적하며 각 홉마다 SSRF 검증을 수행."""
    for _ in range(_MAX_REDIRECTS):
        response = await client.get(url, headers=headers, follow_redirects=False)
        if response.status_code not in _REDIRECT_STATUSES:
            return response

        location = response.headers.get("location", "")
        if not location:
            raise UpstreamFetchError("리다이렉트 응답에 Location 헤더가 없습니다.")

        redirect_url = urljoin(url, location)
        validate_url(redirect_url)
        url = redirect_url

    raise UpstreamFetchError("리다이렉트가 너무 많습니다 (최대 5회).")


async def fetch_url_content(url: str) -> tuple[str, str]:
    """URL에서 HTML을 가져와 클린 텍스트 추출. (title, content) 튜플 반환."""
    url = validate_url(url)
    await validate_content_type(url)

    async with httpx.AsyncClient(timeout=WEB_FETCH_TIMEOUT) as client:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = await _fetch_with_redirect_validation(client, url, headers)
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
