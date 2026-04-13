"""Organic Thought Seed 프로젝트의 중앙 설정 관리 모듈입니다."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, get_type_hints

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Organic Thought Seed 프로젝트의 중앙 설정 관리 클래스입니다.

    모델명, 임계값, 저장 경로, 가중치 등 주요 설정을 한곳에서 관리하며,
    환경 변수 오버라이드를 지원합니다. 경로는 항상 프로젝트 루트 기준의 절대 경로로
    정규화되어 실행 위치와 무관하게 동일한 저장 위치를 사용합니다.
    """

    PROJECT_NAME: str = field(default="Organic Thought Seed")
    ENVIRONMENT: str = field(default="development")
    PROJECT_ROOT: str = field(default_factory=lambda: str(Path(__file__).resolve().parents[2]))

    THRESHOLD_MODEL_NAME: str = field(default="mock-threshold-detector")
    THRESHOLD_LENGTH: int = field(default=500)
    THRESHOLD_SCORE: float = field(default=0.7)

    SEED_SAVE_PATH: str = field(default="seeds")

    NUM_CLONES: int = field(default=3)
    TASK_EXECUTION_MODEL: str = field(default="mock-task-executor")
    CLONE_TIMEOUT_SECONDS: float = field(default=5.0)

    WIKI_UPDATE_MODEL: str = field(default="mock-wiki-manager")
    FEEDBACK_LOOP_WEIGHT: float = field(default=0.5)
    WIKI_SAVE_PATH: str = field(default="wiki")

    OPENAI_API_KEY: str = field(default="")

    _SENSITIVE_TOKENS = ("KEY", "TOKEN", "SECRET", "PASSWORD")

    def __post_init__(self) -> None:
        """환경 변수를 반영하고 경로를 절대 경로로 정규화합니다."""
        type_hints = get_type_hints(type(self))

        for dataclass_field in fields(self):
            key = dataclass_field.name
            if key.startswith("_"):
                continue

            env_var = os.getenv(key)
            if env_var is None:
                continue

            expected_type = type_hints.get(key, str)
            try:
                setattr(self, key, self._coerce_value(expected_type, env_var))
            except ValueError:
                logger.warning(
                    "환경 변수 형변환에 실패하여 기본값을 유지합니다.",
                    extra={"config_key": key, "raw_value": env_var},
                )

        self.PROJECT_ROOT = str(self._normalize_project_root(self.PROJECT_ROOT))
        self.SEED_SAVE_PATH = str(self._resolve_path(self.SEED_SAVE_PATH))
        self.WIKI_SAVE_PATH = str(self._resolve_path(self.WIKI_SAVE_PATH))

    def _coerce_value(self, expected_type: Any, raw_value: str) -> Any:
        """환경 변수 문자열을 설정 타입에 맞춰 변환합니다."""
        if expected_type is bool:
            return raw_value.strip().lower() in {"true", "1", "t", "yes"}
        if expected_type is int:
            return int(raw_value)
        if expected_type is float:
            return float(raw_value)
        return raw_value

    def _normalize_project_root(self, value: str | Path) -> Path:
        """프로젝트 루트 경로를 절대 경로로 정규화합니다."""
        project_root = Path(value).expanduser()
        if not project_root.is_absolute():
            project_root = (Path(__file__).resolve().parents[2] / project_root).resolve()
        return project_root

    def _resolve_path(self, value: str | Path) -> Path:
        """상대 경로를 프로젝트 루트 기준 절대 경로로 변환합니다."""
        candidate = Path(value).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
        return (Path(self.PROJECT_ROOT) / candidate).resolve()

    def to_dict(self) -> Dict[str, Any]:
        """설정 객체를 딕셔너리 형태로 반환합니다."""
        return {
            dataclass_field.name: getattr(self, dataclass_field.name)
            for dataclass_field in fields(self)
            if not dataclass_field.name.startswith("_")
        }

    def to_log_dict(self) -> Dict[str, Any]:
        """로그 출력에 안전한 민감 정보 마스킹 딕셔너리를 반환합니다.

        ``to_dict()`` 는 프로그래밍 용도로 원본 값을 반환하고,
        이 메서드는 로그·디버그 출력 시 민감 필드를 마스킹하여 반환합니다.
        """
        return self._to_display_dict()

    def _is_sensitive_field(self, key: str) -> bool:
        """민감 정보로 간주해야 하는 필드인지 판단합니다."""
        normalized_key = key.upper()
        return any(token in normalized_key for token in self._SENSITIVE_TOKENS)

    def _mask_sensitive_value(self, value: Any) -> Any:
        """민감한 값을 로그 출력용으로 마스킹합니다."""
        if not isinstance(value, str):
            return value
        if not value:
            return value
        if len(value) <= 8:
            return f"{value[:2]}..."
        return f"{value[:5]}...{value[-3:]}"

    def _to_display_dict(self) -> Dict[str, Any]:
        """민감 정보를 마스킹한 표시용 딕셔너리를 반환합니다."""
        display_dict: Dict[str, Any] = {}
        for key, value in self.to_dict().items():
            display_dict[key] = self._mask_sensitive_value(value) if self._is_sensitive_field(key) else value
        return display_dict

    def __str__(self) -> str:
        """설정 내용을 민감 정보 마스킹과 함께 보기 좋게 출력합니다."""
        return "\n".join(f"{key}: {value}" for key, value in self._to_display_dict().items())

    def __repr__(self) -> str:
        """디버그 출력에서도 민감 정보가 평문으로 드러나지 않도록 합니다."""
        items = ", ".join(f"{key}={value!r}" for key, value in self._to_display_dict().items())
        return f"Config({items})"
