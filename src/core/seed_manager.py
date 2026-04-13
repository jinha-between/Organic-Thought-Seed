"""Organic Thought Seed v3의 씨앗 저장 및 진화 이력 관리를 담당합니다.

이 모듈은 단일 스냅샷 저장을 넘어, 의지가 어떻게 진화했는지를 버전 이력으로
보존합니다. main.py가 기대하는 간결한 씨앗 API와, 기존 구현이 제공하던 풍부한
분석 기능을 함께 유지하는 것이 목표입니다.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .config import Config
from .snapshot import CognitiveState, Snapshot
from .utils import parse_datetime as _parse_datetime, parse_optional_datetime as _parse_optional_datetime

logger = logging.getLogger(__name__)


class SeedManagerError(Exception):
    """씨앗 저장 및 이력 관리 전반에서 발생하는 기본 예외입니다."""


class SeedNotFoundError(SeedManagerError):
    """요청한 씨앗 또는 버전을 찾을 수 없을 때 발생합니다."""


class EvolutionTrackerError(SeedManagerError):
    """진화 비교 분석 중 오류가 발생할 때 사용합니다."""


@dataclass
class SeedVersion:
    """하나의 저장된 씨앗 버전을 표현합니다."""

    version_number: int
    snapshot: Snapshot
    reason: str
    version_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_version_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def state(self) -> CognitiveState:
        """기존 구현 호환용으로 내부 CognitiveState를 반환합니다."""
        return self.snapshot.cognitive_state

    def to_dict(self) -> Dict[str, Any]:
        """객체를 JSON 직렬화 가능한 딕셔너리로 변환합니다."""
        return {
            "version_number": self.version_number,
            "snapshot": self.snapshot.to_dict(),
            "reason": self.reason,
            "version_id": self.version_id,
            "parent_version_id": self.parent_version_id,
            "created_at": self.created_at.isoformat(),
            "metadata": copy.deepcopy(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SeedVersion":
        """딕셔너리에서 SeedVersion 객체를 복원합니다."""
        return cls(
            version_number=int(data.get("version_number", 1)),
            snapshot=Snapshot.from_dict(data.get("snapshot", {})),
            reason=str(data.get("reason", "씨앗 저장")),
            version_id=str(data.get("version_id", str(uuid.uuid4()))),
            parent_version_id=data.get("parent_version_id"),
            created_at=_parse_datetime(data.get("created_at")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class EvolutionHistory:
    """하나의 씨앗 이름 아래 축적된 전체 버전 이력을 표현합니다."""

    seed_name: str
    versions: List[SeedVersion] = field(default_factory=list)
    first_created: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    @property
    def total_versions(self) -> int:
        """저장된 총 버전 수를 반환합니다."""
        return len(self.versions)

    def add_version(self, version: SeedVersion) -> None:
        """새 버전을 이력에 추가합니다."""
        self.versions.append(version)
        if self.first_created is None:
            self.first_created = version.created_at
        self.last_updated = version.created_at

    def to_dict(self) -> Dict[str, Any]:
        """객체를 JSON 직렬화 가능한 딕셔너리로 변환합니다."""
        return {
            "seed_name": self.seed_name,
            "versions": [version.to_dict() for version in self.versions],
            "first_created": self.first_created.isoformat() if self.first_created else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionHistory":
        """딕셔너리에서 EvolutionHistory 객체를 복원합니다."""
        history = cls(seed_name=str(data.get("seed_name", "organic_thought_seed")))
        history.versions = [SeedVersion.from_dict(item) for item in data.get("versions", [])]
        history.first_created = _parse_optional_datetime(data.get("first_created"))
        history.last_updated = _parse_optional_datetime(data.get("last_updated"))
        return history


@dataclass(slots=True)
class EvolutionDiff:
    """두 버전 간 차이 분석 결과를 담는 객체입니다."""

    from_version: int
    to_version: int
    direction_changed: bool
    direction_diff: Optional[Tuple[str, str]]
    specificity_change: float
    new_perspectives: List[str]
    resolved_questions: List[str]
    new_questions: List[str]
    wiki_knowledge_added: List[str]
    summary: str


class SeedManager:
    """Snapshot 기반의 씨앗 저장·로드·버전 관리 기능을 제공합니다."""

    HISTORY_FILE_NAME = "seed_evolution_history.json"

    def __init__(self, config: Config, seed_name: str = "organic_thought_seed") -> None:
        """SeedManager를 초기화하고 기존 이력을 불러옵니다."""
        self.config = config
        self.seed_name = seed_name
        self.base_dir = os.path.abspath(config.SEED_SAVE_PATH)
        os.makedirs(self.base_dir, exist_ok=True)
        self._history_file_path = os.path.join(self.base_dir, self.HISTORY_FILE_NAME)
        self._evolution_history = self._load_or_initialize_history()

    def save_seed(self, snapshot: Snapshot) -> SeedVersion:
        """Snapshot 객체를 새로운 씨앗 버전으로 저장합니다."""
        if not isinstance(snapshot, Snapshot):
            raise SeedManagerError("save_seed는 Snapshot 객체를 받아야 합니다.")

        latest = self.load_latest_version_object()
        version_number = 1 if latest is None else latest.version_number + 1
        version = SeedVersion(
            version_number=version_number,
            snapshot=copy.deepcopy(snapshot),
            reason=snapshot.reason,
            parent_version_id=latest.version_id if latest else None,
            metadata={"will_strength": snapshot.cognitive_state.will_strength.combined_strength},
        )
        self._evolution_history.add_version(version)
        self._persist_history()
        return copy.deepcopy(version)

    def load_seed(self, seed_id: str) -> Snapshot:
        """version_id, version_number, snapshot.id 중 하나로 씨앗을 로드합니다."""
        for version in self._evolution_history.versions:
            if (
                version.version_id == seed_id
                or str(version.version_number) == seed_id
                or version.snapshot.id == seed_id
            ):
                return copy.deepcopy(version.snapshot)
        raise SeedNotFoundError(f"ID '{seed_id}'에 해당하는 씨앗을 찾을 수 없습니다.")

    def load_latest(self) -> Snapshot:
        """가장 최신 스냅샷을 반환합니다."""
        latest = self.load_latest_version_object()
        if latest is None:
            raise SeedNotFoundError("저장된 씨앗이 없습니다.")
        return copy.deepcopy(latest.snapshot)

    def load_latest_version_object(self) -> Optional[SeedVersion]:
        """가장 최신 SeedVersion 객체를 반환합니다."""
        if not self._evolution_history.versions:
            return None
        return copy.deepcopy(self._evolution_history.versions[-1])

    def list_versions(self) -> List[SeedVersion]:
        """저장된 전체 버전 목록을 반환합니다."""
        return copy.deepcopy(self._evolution_history.versions)

    def list_seeds(self) -> List[str]:
        """저장된 씨앗 ID 목록을 최신순으로 반환합니다."""
        return [version.snapshot.id for version in reversed(self._evolution_history.versions)]

    def get_evolution_history(self) -> EvolutionHistory:
        """전체 진화 이력의 복사본을 반환합니다."""
        return copy.deepcopy(self._evolution_history)

    def _load_or_initialize_history(self) -> EvolutionHistory:
        """기존 이력을 불러오거나 빈 이력을 생성합니다."""
        if not os.path.exists(self._history_file_path):
            return EvolutionHistory(seed_name=self.seed_name)

        try:
            with open(self._history_file_path, "r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)
            return EvolutionHistory.from_dict(data)
        except (OSError, json.JSONDecodeError) as exc:
            raise SeedManagerError(f"씨앗 이력 파일을 읽는 중 오류가 발생했습니다: {exc}") from exc

    def _persist_history(self) -> None:
        """현재 진화 이력을 JSON 파일에 저장합니다."""
        temp_path = f"{self._history_file_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as file_handle:
                json.dump(self._evolution_history.to_dict(), file_handle, ensure_ascii=False, indent=2)
            os.replace(temp_path, self._history_file_path)
        except OSError as exc:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise SeedManagerError(f"씨앗 이력을 저장하는 중 오류가 발생했습니다: {exc}") from exc


class EvolutionTracker:
    """씨앗 버전 간의 진화 과정을 분석하고 설명합니다."""

    def __init__(self, seed_manager: SeedManager) -> None:
        """SeedManager와 연결된 EvolutionTracker를 초기화합니다."""
        self.seed_manager = seed_manager

    def compare_versions(self, v1: SeedVersion, v2: SeedVersion) -> EvolutionDiff:
        """두 버전 사이의 방향성·구체성·관점 변화를 분석합니다."""
        if v1.version_number >= v2.version_number:
            raise EvolutionTrackerError("첫 번째 버전은 두 번째 버전보다 이전이어야 합니다.")

        state1 = v1.state
        state2 = v2.state

        direction_changed = state1.direction != state2.direction
        direction_diff = (state1.direction, state2.direction) if direction_changed else None
        specificity_change = round(
            state2.will_strength.specificity_score - state1.will_strength.specificity_score,
            3,
        )

        perspective_ids = {perspective.id for perspective in state1.perspectives}
        new_perspectives = [
            perspective.evolved_thought
            for perspective in state2.perspectives
            if perspective.id not in perspective_ids
        ]
        resolved_questions = [question for question in state1.unresolved if question not in state2.unresolved]
        new_questions = [question for question in state2.unresolved if question not in state1.unresolved]
        knowledge_keys_added = [
            key for key in state2.wiki_knowledge.keys() if key not in state1.wiki_knowledge.keys()
        ]
        wiki_knowledge_added = [state2.wiki_knowledge[key] for key in knowledge_keys_added]

        summary_lines = [f"v{v1.version_number}에서 v{v2.version_number}로의 변화:"]
        if direction_changed and direction_diff:
            summary_lines.append(f"  - 방향성 변경: '{direction_diff[0]}' -> '{direction_diff[1]}'")
        summary_lines.append(f"  - 구체성 변화: {specificity_change:+.2f}")
        if new_perspectives:
            summary_lines.append(
                f"  - 새로운 관점 ({len(new_perspectives)}개): {', '.join(new_perspectives[:3])}"
            )
        if resolved_questions:
            summary_lines.append(
                f"  - 해결된 질문 ({len(resolved_questions)}개): {', '.join(resolved_questions[:3])}"
            )
        if new_questions:
            summary_lines.append(
                f"  - 새로운 질문 ({len(new_questions)}개): {', '.join(new_questions[:3])}"
            )
        if wiki_knowledge_added:
            summary_lines.append(
                f"  - 추가된 위키 지식 ({len(wiki_knowledge_added)}개): {', '.join(wiki_knowledge_added[:3])}"
            )
        if len(summary_lines) == 2 and not direction_changed and specificity_change == 0:
            summary_lines.append("  - 큰 변화 없음.")

        return EvolutionDiff(
            from_version=v1.version_number,
            to_version=v2.version_number,
            direction_changed=direction_changed,
            direction_diff=direction_diff,
            specificity_change=specificity_change,
            new_perspectives=new_perspectives,
            resolved_questions=resolved_questions,
            new_questions=new_questions,
            wiki_knowledge_added=wiki_knowledge_added,
            summary="\n".join(summary_lines),
        )

    def get_evolution_timeline(self) -> str:
        """전체 버전 이력을 사람이 읽기 쉬운 타임라인 문자열로 반환합니다."""
        history = self.seed_manager.get_evolution_history()
        if not history.versions:
            return "저장된 씨앗 버전이 없습니다."

        lines = [
            f"--- 씨앗 진화 타임라인: '{history.seed_name}' ({history.total_versions} 버전) ---",
            f"최초 생성: {history.first_created.strftime('%Y-%m-%d %H:%M') if history.first_created else 'N/A'}",
            f"최근 업데이트: {history.last_updated.strftime('%Y-%m-%d %H:%M') if history.last_updated else 'N/A'}",
            "",
        ]

        for index, version in enumerate(history.versions):
            prefix = "🌱" if index == 0 else "🌳" if index == len(history.versions) - 1 else "├──"
            lines.append(
                f"{prefix} v{version.version_number} ({version.created_at.strftime('%Y-%m-%d %H:%M')}): {version.reason}"
            )
            if index > 0:
                diff = self.compare_versions(history.versions[index - 1], version)
                for diff_line in diff.summary.splitlines()[1:]:
                    lines.append(f"│   {diff_line}")
            lines.append("│")

        lines.pop()
        lines.append("---------------------------------------------------")
        return "\n".join(lines)

    def get_direction_changes(self) -> List[str]:
        """방향성이 실제로 바뀐 버전만 추려서 반환합니다."""
        history = self.seed_manager.get_evolution_history()
        changes: List[str] = []
        for index in range(1, len(history.versions)):
            previous_version = history.versions[index - 1]
            current_version = history.versions[index]
            if previous_version.state.direction != current_version.state.direction:
                changes.append(
                    f"v{previous_version.version_number} -> v{current_version.version_number}: "
                    f"'{previous_version.state.direction}' -> '{current_version.state.direction}'"
                )
        return changes

    def get_specificity_growth(self) -> List[Tuple[int, float]]:
        """버전별 구체성 점수 추이를 반환합니다."""
        history = self.seed_manager.get_evolution_history()
        return [
            (version.version_number, version.state.will_strength.specificity_score)
            for version in history.versions
        ]


__all__ = [
    "EvolutionDiff",
    "EvolutionHistory",
    "EvolutionTracker",
    "EvolutionTrackerError",
    "SeedManager",
    "SeedManagerError",
    "SeedNotFoundError",
    "SeedVersion",
]
