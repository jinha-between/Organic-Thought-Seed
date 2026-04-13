"""프로젝트 전반에서 공통으로 사용하는 유틸리티 함수를 모아둡니다."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional


def parse_datetime(value: Any) -> datetime:
    """다양한 입력을 datetime 객체로 안전하게 정규화합니다.

    Args:
        value: datetime 객체, ISO 형식 문자열, 또는 None/빈 문자열.

    Returns:
        변환된 datetime 객체. 파싱 불가 시 현재 시각을 반환합니다.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value)
    return datetime.now()


def parse_optional_datetime(value: Any) -> Optional[datetime]:
    """None을 허용하는 datetime 필드를 복원합니다.

    Args:
        value: datetime 객체, ISO 형식 문자열, None, 또는 빈 문자열.

    Returns:
        변환된 datetime 객체 또는 None.
    """
    if value in (None, ""):
        return None
    return parse_datetime(value)


__all__ = [
    "parse_datetime",
    "parse_optional_datetime",
]
