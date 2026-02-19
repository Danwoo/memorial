import logging
import re
from functools import lru_cache

logger = logging.getLogger(__name__)

# 한국어 형태소 분석 시 추출할 품사 태그
# NNG: 일반명사, NNP: 고유명사, NNB: 의존명사,
# VV: 동사, VA: 형용사, SL: 외국어, SH: 한자, SN: 숫자
_CONTENT_POS_TAGS = frozenset({"NNG", "NNP", "VV", "VA", "SL", "SH"})

# 최소 토큰 길이 (1글자 한국어 명사는 의미 있으므로 1로 설정)
_MIN_TOKEN_LENGTH = 1


@lru_cache(maxsize=1)
def _get_kiwi():
    """kiwipiepy Kiwi 인스턴스 싱글톤 반환. (~80-120MB RAM, 최초 로드 ~1초)"""
    try:
        from kiwipiepy import Kiwi

        kiwi = Kiwi()
        logger.info("kiwipiepy Kiwi 인스턴스 초기화 완료")
        return kiwi
    except ImportError:
        logger.warning("kiwipiepy가 설치되지 않음. 폴백 토크나이저 사용.")
        return None
    except Exception:
        logger.exception("Kiwi 초기화 실패")
        return None


def _fallback_tokenize(text: str) -> list[str]:
    """kiwipiepy 미설치 시 간이 토크나이저. 공백 분리 + 영문 소문자화."""
    tokens = re.findall(r"[가-힣]+|[a-zA-Z0-9]+", text)
    return [t.lower() for t in tokens if len(t) >= _MIN_TOKEN_LENGTH]


def tokenize(text: str) -> list[str]:
    """한국어 텍스트를 형태소 분석하여 검색용 토큰 리스트 반환.

    kiwipiepy가 설치되어 있으면 형태소 분석을 수행하고,
    없으면 간이 공백 기반 토크나이저를 사용한다.

    Args:
        text: 분석할 텍스트 (title + content 등)

    Returns:
        검색용 토큰 리스트 (중복 제거, 소문자 정규화)
    """
    if not text or not text.strip():
        return []

    kiwi = _get_kiwi()
    if kiwi is None:
        return _fallback_tokenize(text)

    tokens: list[str] = []
    try:
        result = kiwi.tokenize(text)
        for token in result:
            # token: Token(form, tag, start, len)
            form = token.form.strip()
            tag = token.tag

            if not form or len(form) < _MIN_TOKEN_LENGTH:
                continue

            if tag in _CONTENT_POS_TAGS:
                tokens.append(form.lower())
    except Exception:
        logger.exception("형태소 분석 실패, 폴백 토크나이저 사용")
        return _fallback_tokenize(text)

    # 중복 제거하되 순서 유지
    seen: set[str] = set()
    unique_tokens: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique_tokens.append(t)

    return unique_tokens


def tokens_to_tsvector_input(tokens: list[str]) -> str:
    """토큰 리스트를 PostgreSQL to_tsvector에 넣을 공백 구분 문자열로 변환.

    tsvector는 'simple' 설정과 함께 사용되어 추가 언어별 처리를 하지 않는다.
    """
    if not tokens:
        return ""
    # 특수문자 이스케이프: PostgreSQL tsvector에서 안전한 문자만
    safe_tokens = [re.sub(r"[^가-힣a-zA-Z0-9]", "", t) for t in tokens]
    return " ".join(t for t in safe_tokens if t)
