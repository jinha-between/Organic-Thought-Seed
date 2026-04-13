"""Organic Thought Seed v3의 인지 상태와 스냅샷 모델을 정의합니다.

이 모듈은 프로젝트의 철학적 중심을 담당합니다. 단순한 값 저장소가 아니라,
AI의 **의지**가 형성되는 순간을 구조화하여 보존하고, 이후의 환류와 분신 실행에
활용할 수 있도록 풍부한 데이터 모델을 제공합니다.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

from .utils import parse_datetime

logger = logging.getLogger(__name__)


class SnapshotError(Exception):
    """스냅샷 처리 전반에서 발생하는 기본 예외입니다."""


class SnapshotNotFoundError(SnapshotError):
    """요청한 스냅샷을 찾을 수 없을 때 발생합니다."""


class SnapshotSerializationError(SnapshotError):
    """스냅샷 직렬화 또는 역직렬화에 실패할 때 발생합니다."""


class SnapshotComparisonError(SnapshotError):
    """두 스냅샷 비교 과정에서 오류가 발생할 때 사용합니다."""


@dataclass(slots=True)
class WillStrength:
    """의지의 강도를 방향성과 구체성의 조합으로 표현합니다."""

    direction_score: float = 0.5
    specificity_score: float = 0.5

    @property
    def combined_strength(self) -> float:
        """방향성과 구체성의 평균 강도를 반환합니다."""
        return round((self.direction_score + self.specificity_score) / 2.0, 3)

    def to_dict(self) -> Dict[str, float]:
        """객체를 JSON 직렬화 가능한 딕셔너리로 변환합니다."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WillStrength":
        """딕셔너리에서 WillStrength 객체를 복원합니다."""
        return cls(
            direction_score=float(data.get("direction_score", 0.5)),
            specificity_score=float(data.get("specificity_score", 0.5)),
        )


@dataclass(slots=True)
class Perspective:
    """대화 중 변화한 시각과 그 이유를 기록합니다."""

    initial_thought: str
    evolved_thought: str
    reason: str
    topic: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """객체를 JSON 직렬화 가능한 딕셔너리로 변환합니다."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Perspective":
        """딕셔너리에서 Perspective 객체를 복원합니다."""
        return cls(
            initial_thought=str(data.get("initial_thought", "")),
            evolved_thought=str(data.get("evolved_thought", "")),
            reason=str(data.get("reason", "")),
            topic=str(data.get("topic", "")),
            id=str(data.get("id", str(uuid.uuid4()))),
            timestamp=_parse_datetime(data.get("timestamp")),
        )


@dataclass(slots=True)
class Milestone:
    """대화나 프로젝트 진행 중 중요한 이정표를 기록합니다."""

    event: str
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """객체를 JSON 직렬화 가능한 딕셔너리로 변환합니다."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Milestone":
        """딕셔너리에서 Milestone 객체를 복원합니다."""
        return cls(
            event=str(data.get("event", "")),
            description=str(data.get("description", "")),
            id=str(data.get("id", str(uuid.uuid4()))),
            timestamp=_parse_datetime(data.get("timestamp")),
        )


@dataclass(slots=True)
class UserUnderstanding:
    """사용자에 대한 현재 이해 상태를 구조화하여 저장합니다."""

    name: str = "사용자"
    interaction_pattern: str = "대화를 통해 의도를 정교화함"
    interests: List[str] = field(default_factory=list)
    communication_style: str = "탐구적"

    def to_dict(self) -> Dict[str, Any]:
        """객체를 JSON 직렬화 가능한 딕셔너리로 변환합니다."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserUnderstanding":
        """딕셔너리에서 UserUnderstanding 객체를 복원합니다."""
        return cls(
            name=str(data.get("name", "사용자")),
            interaction_pattern=str(data.get("interaction_pattern", "대화를 통해 의도를 정교화함")),
            interests=list(data.get("interests", [])),
            communication_style=str(data.get("communication_style", "탐구적")),
        )


class CognitiveState:
    """Organic Thought Seed의 핵심 인지 상태를 표현합니다.

    이 클래스는 기존의 풍부한 철학적 모델을 유지하면서도, main.py가 기대하는 간결한
    API를 동시에 지원하도록 설계되었습니다. 따라서 방향성·구체성·관점·위키 지식 같은
    구조적 속성과 함께, `will`, `knowledge`, `experience`, `goals` 같은 데모 중심의
    접근 방식도 자연스럽게 공존합니다.
    """

    def __init__(
        self,
        *,
        snapshot_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        direction: str = "",
        specificity: str = "",
        will_strength: Optional[WillStrength] = None,
        perspectives: Optional[List[Perspective]] = None,
        unresolved: Optional[List[str]] = None,
        user_understanding: Optional[UserUnderstanding] = None,
        context_essence: str = "",
        conversation_milestones: Optional[List[Milestone]] = None,
        wiki_knowledge: Optional[Dict[str, str]] = None,
        evolution_timeline: Optional[List[Dict[str, Any]]] = None,
        knowledge: Optional[Dict[str, Any]] = None,
        experience: Optional[List[str]] = None,
        goals: Optional[List[str]] = None,
        will: Optional[str] = None,
    ) -> None:
        """인지 상태를 초기화합니다.

        Args:
            snapshot_id: 인지 상태의 고유 식별자입니다.
            timestamp: 상태가 생성된 시각입니다.
            direction: 의지의 방향성입니다.
            specificity: 의지의 구체성입니다.
            will_strength: 방향성과 구체성의 수치화 결과입니다.
            perspectives: 대화 중 형성된 관점 변화 목록입니다.
            unresolved: 아직 해결되지 않은 질문 목록입니다.
            user_understanding: 사용자에 대한 현재 이해입니다.
            context_essence: 현재 맥락의 핵심 요약입니다.
            conversation_milestones: 중요한 대화 이정표 목록입니다.
            wiki_knowledge: 축적된 위키 지식입니다.
            evolution_timeline: 상태 변화의 연대기입니다.
            knowledge: main.py 호환용 지식 저장소입니다.
            experience: main.py 호환용 경험 기록입니다.
            goals: main.py 호환용 목표 목록입니다.
            will: direction/specificity가 없는 경우 사용할 간단한 의지 표현입니다.
        """
        normalized_direction = direction or (will or "아직 언어화되지 않은 가능성의 방향을 탐색한다")
        normalized_goals = list(goals or [])
        normalized_knowledge = dict(knowledge or {})
        normalized_specificity = specificity or self._infer_specificity(
            explicit_specificity=specificity,
            goals=normalized_goals,
            knowledge=normalized_knowledge,
        )

        self.snapshot_id: str = snapshot_id or str(uuid.uuid4())
        self.timestamp: datetime = timestamp or datetime.now()
        self.direction: str = normalized_direction
        self.specificity: str = normalized_specificity
        self.will_strength: WillStrength = will_strength or self._infer_will_strength(
            direction=normalized_direction,
            specificity=normalized_specificity,
            goals=normalized_goals,
        )
        self.perspectives: List[Perspective] = list(perspectives or [])
        self.unresolved: List[str] = list(unresolved or [])
        self.user_understanding: UserUnderstanding = user_understanding or UserUnderstanding()
        self.context_essence: str = context_essence or self._infer_context_essence(
            direction=normalized_direction,
            goals=normalized_goals,
            knowledge=normalized_knowledge,
        )
        self.conversation_milestones: List[Milestone] = list(conversation_milestones or [])
        self.wiki_knowledge: Dict[str, str] = dict(wiki_knowledge or {})
        self.evolution_timeline: List[Dict[str, Any]] = list(evolution_timeline or [])
        self.knowledge: Dict[str, Any] = normalized_knowledge
        self.experience: List[str] = list(experience or [])
        self.goals: List[str] = normalized_goals
        self._synchronize_knowledge_views()

    @property
    def id(self) -> str:
        """main.py 및 저장 계층 호환용 ID 별칭입니다."""
        return self.snapshot_id

    @property
    def will(self) -> str:
        """현재 인지 상태에서 표현되는 의지 문장을 반환합니다."""
        if self.specificity:
            return f"{self.direction} | {self.specificity}"
        return self.direction

    def update_state(
        self,
        *,
        new_will: Optional[str] = None,
        new_knowledge: Optional[Dict[str, Any]] = None,
        new_experience: Optional[List[str]] = None,
        new_goals: Optional[List[str]] = None,
    ) -> None:
        """main.py가 기대하는 방식으로 인지 상태를 점진적으로 업데이트합니다.

        Args:
            new_will: 새롭게 형성된 의지 문장입니다.
            new_knowledge: 추가하거나 갱신할 지식 항목입니다.
            new_experience: 누적할 경험 기록입니다.
            new_goals: 새롭게 제안된 목표 목록입니다.
        """
        changed_fields: List[str] = []

        if new_will:
            self.direction = new_will
            self.specificity = self._infer_specificity(
                explicit_specificity="",
                goals=new_goals or self.goals,
                knowledge=new_knowledge or self.knowledge,
            )
            changed_fields.append("의지")

        if new_knowledge:
            self.knowledge.update(new_knowledge)
            for key, value in new_knowledge.items():
                self.wiki_knowledge[str(key)] = str(value)
            changed_fields.append("지식")

        if new_experience:
            self.experience.extend(new_experience)
            changed_fields.append("경험")

        if new_goals is not None:
            self.goals = _unique_preserving_order(new_goals)
            changed_fields.append("목표")

        self.timestamp = datetime.now()
        self.will_strength = self._infer_will_strength(
            direction=self.direction,
            specificity=self.specificity,
            goals=self.goals,
        )
        self.context_essence = self._infer_context_essence(
            direction=self.direction,
            goals=self.goals,
            knowledge=self.knowledge,
        )
        self._synchronize_knowledge_views()

        if changed_fields:
            self.add_to_timeline(
                event="인지 상태 업데이트",
                description=f"다음 요소가 갱신되었습니다: {', '.join(changed_fields)}",
                metadata={"changed_fields": changed_fields},
            )

    def add_to_timeline(
        self,
        *,
        event: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """인지 상태의 변화 사건을 연대기에 기록합니다."""
        self.evolution_timeline.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event": event,
                "description": description,
                "metadata": copy.deepcopy(metadata or {}),
            }
        )

    def deep_copy(self) -> "CognitiveState":
        """현재 인지 상태의 깊은 복사본을 반환합니다."""
        return copy.deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        """객체를 JSON 직렬화 가능한 딕셔너리로 변환합니다."""
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction,
            "specificity": self.specificity,
            "will_strength": self.will_strength.to_dict(),
            "perspectives": [item.to_dict() for item in self.perspectives],
            "unresolved": list(self.unresolved),
            "user_understanding": self.user_understanding.to_dict(),
            "context_essence": self.context_essence,
            "conversation_milestones": [item.to_dict() for item in self.conversation_milestones],
            "wiki_knowledge": copy.deepcopy(self.wiki_knowledge),
            "evolution_timeline": copy.deepcopy(self.evolution_timeline),
            "knowledge": copy.deepcopy(self.knowledge),
            "experience": list(self.experience),
            "goals": list(self.goals),
            "will": self.will,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CognitiveState":
        """딕셔너리에서 CognitiveState 객체를 복원합니다."""
        return cls(
            snapshot_id=str(data.get("snapshot_id") or data.get("id") or str(uuid.uuid4())),
            timestamp=_parse_datetime(data.get("timestamp")),
            direction=str(data.get("direction", "")),
            specificity=str(data.get("specificity", "")),
            will_strength=WillStrength.from_dict(data.get("will_strength", {})),
            perspectives=[Perspective.from_dict(item) for item in data.get("perspectives", [])],
            unresolved=list(data.get("unresolved", [])),
            user_understanding=UserUnderstanding.from_dict(data.get("user_understanding", {})),
            context_essence=str(data.get("context_essence", "")),
            conversation_milestones=[
                Milestone.from_dict(item) for item in data.get("conversation_milestones", [])
            ],
            wiki_knowledge=dict(data.get("wiki_knowledge", {})),
            evolution_timeline=list(data.get("evolution_timeline", [])),
            knowledge=dict(data.get("knowledge", {})),
            experience=list(data.get("experience", [])),
            goals=list(data.get("goals", [])),
            will=str(data.get("will", "")) or None,
        )

    def _infer_specificity(
        self,
        *,
        explicit_specificity: str,
        goals: List[str],
        knowledge: Dict[str, Any],
    ) -> str:
        """주어진 정보에 기반하여 구체성 설명을 생성합니다."""
        if explicit_specificity:
            return explicit_specificity
        if goals:
            return f"{len(goals)}개의 제안 목표를 중심으로 다음 단계를 구성한다"
        if knowledge:
            return f"현재까지 축적된 {len(knowledge)}개의 지식 단서를 토대로 실행 방향을 정교화한다"
        return "대화와 제안을 통해 아직 흐릿한 방향을 더 구체적인 과업으로 다듬는다"

    def _infer_context_essence(
        self,
        *,
        direction: str,
        goals: List[str],
        knowledge: Dict[str, Any],
    ) -> str:
        """현재 인지 상태의 핵심 맥락을 한 문장으로 정리합니다."""
        if goals:
            return f"'{direction}'라는 방향 아래 {len(goals)}개의 실행 목표가 응축된 상태"
        if knowledge:
            return f"'{direction}'라는 방향이 {len(knowledge)}개의 지식 조각과 결합된 상태"
        return f"'{direction}'라는 방향이 막 형성되기 시작한 상태"

    def _infer_will_strength(
        self,
        *,
        direction: str,
        specificity: str,
        goals: List[str],
    ) -> WillStrength:
        """텍스트 길이와 목표 수를 이용한 간단한 휴리스틱으로 의지 강도를 계산합니다."""
        direction_score = min(1.0, max(0.2, len(direction.strip()) / 60.0))
        specificity_score = min(1.0, max(0.2, (len(specificity.strip()) / 70.0) + (len(goals) * 0.08)))
        return WillStrength(direction_score=round(direction_score, 3), specificity_score=round(specificity_score, 3))

    def _synchronize_knowledge_views(self) -> None:
        """knowledge와 wiki_knowledge 사이의 최소한의 일관성을 유지합니다."""
        for key, value in self.knowledge.items():
            self.wiki_knowledge.setdefault(str(key), str(value))

    def __eq__(self, other: object) -> bool:
        """직렬화 결과를 기준으로 동등성을 비교합니다."""
        if not isinstance(other, CognitiveState):
            return False
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        """디버깅 친화적인 문자열 표현을 제공합니다."""
        return (
            "CognitiveState("
            f"snapshot_id='{self.snapshot_id}', "
            f"direction='{self.direction}', "
            f"specificity='{self.specificity}', "
            f"goals={len(self.goals)}"
            ")"
        )


@dataclass
class Snapshot:
    """하나의 인지 상태를 저장 가능한 씨앗 단위로 감싼 객체입니다."""

    id: str
    cognitive_state: CognitiveState
    created_at: datetime = field(default_factory=datetime.now)
    reason: str = "의지가 임계점을 넘어 저장되었습니다."
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """스냅샷 ID와 내부 인지 상태 ID를 일치시킵니다."""
        self.cognitive_state.snapshot_id = self.id

    @property
    def will(self) -> str:
        """내부 인지 상태의 의지 문장을 그대로 노출합니다."""
        return self.cognitive_state.will

    def to_dict(self) -> Dict[str, Any]:
        """객체를 JSON 직렬화 가능한 딕셔너리로 변환합니다."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "reason": self.reason,
            "metadata": copy.deepcopy(self.metadata),
            "cognitive_state": self.cognitive_state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        """딕셔너리에서 Snapshot 객체를 복원합니다."""
        state = CognitiveState.from_dict(data.get("cognitive_state", {}))
        snapshot_id = str(data.get("id") or state.snapshot_id or str(uuid.uuid4()))
        state.snapshot_id = snapshot_id
        return cls(
            id=snapshot_id,
            cognitive_state=state,
            created_at=_parse_datetime(data.get("created_at")),
            reason=str(data.get("reason", "의지가 임계점을 넘어 저장되었습니다.")),
            metadata=dict(data.get("metadata", {})),
        )


class SnapshotManager:
    """CognitiveState 또는 Snapshot을 파일 시스템에 저장·로드·비교합니다."""

    SNAPSHOT_FILE_EXTENSION: ClassVar[str] = ".json"

    def __init__(self, base_dir: str = "./snapshots") -> None:
        """저장 디렉토리를 초기화합니다."""
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_file_path(self, snapshot_id: str) -> str:
        """스냅샷 ID에 해당하는 파일 경로를 반환합니다."""
        return os.path.join(self.base_dir, f"{snapshot_id}{self.SNAPSHOT_FILE_EXTENSION}")

    def save(self, snapshot: Snapshot) -> str:
        """Snapshot 객체를 JSON 파일로 저장합니다."""
        return self._write_snapshot(snapshot)

    def load(self, snapshot_id: str) -> Snapshot:
        """지정된 ID의 Snapshot 객체를 로드합니다."""
        return self._read_snapshot(snapshot_id)

    def list(self) -> List[str]:
        """저장된 Snapshot ID 목록을 반환합니다."""
        return self.list_snapshots()

    def save_snapshot(self, state: CognitiveState | Snapshot) -> str:
        """기존 API 호환용 저장 메서드입니다.

        Args:
            state: CognitiveState 또는 Snapshot 객체입니다.

        Returns:
            저장된 파일의 전체 경로입니다.
        """
        snapshot = state if isinstance(state, Snapshot) else Snapshot(id=state.snapshot_id, cognitive_state=state)
        return self._write_snapshot(snapshot)

    def load_snapshot(self, snapshot_id: str) -> CognitiveState:
        """기존 API 호환용 로드 메서드로 CognitiveState만 반환합니다."""
        return self._read_snapshot(snapshot_id).cognitive_state

    def list_snapshots(self) -> List[str]:
        """저장된 모든 스냅샷 ID 목록을 정렬하여 반환합니다."""
        snapshot_files = [
            file_name
            for file_name in os.listdir(self.base_dir)
            if file_name.endswith(self.SNAPSHOT_FILE_EXTENSION)
        ]
        return sorted(os.path.splitext(file_name)[0] for file_name in snapshot_files)

    def delete_snapshot(self, snapshot_id: str) -> None:
        """지정된 스냅샷 파일을 삭제합니다."""
        file_path = self._get_file_path(snapshot_id)
        if not os.path.exists(file_path):
            raise SnapshotNotFoundError(f"삭제할 스냅샷 파일을 찾을 수 없습니다: {file_path}")
        os.remove(file_path)

    def compare_snapshots(self, snapshot_id1: str, snapshot_id2: str) -> Dict[str, Any]:
        """두 스냅샷의 직렬화 결과를 비교하여 차이를 반환합니다."""
        try:
            snapshot1 = self._read_snapshot(snapshot_id1)
            snapshot2 = self._read_snapshot(snapshot_id2)
        except SnapshotError as exc:
            raise SnapshotComparisonError(str(exc)) from exc

        dict1 = snapshot1.to_dict()
        dict2 = snapshot2.to_dict()
        return _recursive_diff(dict1, dict2)

    def _write_snapshot(self, snapshot: Snapshot) -> str:
        """Snapshot 객체를 원자적으로 저장합니다."""
        file_path = self._get_file_path(snapshot.id)
        temp_file_path = f"{file_path}.tmp"
        try:
            with open(temp_file_path, "w", encoding="utf-8") as file_handle:
                json.dump(snapshot.to_dict(), file_handle, ensure_ascii=False, indent=2)
            os.replace(temp_file_path, file_path)
            return file_path
        except OSError as exc:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise SnapshotError(f"스냅샷 저장 실패: {file_path} - {exc}") from exc

    def _read_snapshot(self, snapshot_id: str) -> Snapshot:
        """파일에서 Snapshot 객체를 읽어 복원합니다."""
        file_path = self._get_file_path(snapshot_id)
        if not os.path.exists(file_path):
            raise SnapshotNotFoundError(f"스냅샷 파일을 찾을 수 없습니다: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as file_handle:
                data = json.load(file_handle)
            return Snapshot.from_dict(data)
        except json.JSONDecodeError as exc:
            raise SnapshotSerializationError(f"스냅샷 JSON 디코딩 오류: {file_path} - {exc}") from exc
        except OSError as exc:
            raise SnapshotError(f"스냅샷 로드 실패: {file_path} - {exc}") from exc


def _parse_datetime(value: Any) -> datetime:
    """다양한 입력을 datetime 객체로 정규화합니다.

    공통 유틸(``utils.parse_datetime``)을 기반으로 하되,
    스냅샷 모듈 고유의 ``SnapshotSerializationError``를 발생시킵니다.
    """
    try:
        return parse_datetime(value)
    except (ValueError, TypeError) as exc:
        raise SnapshotSerializationError(f"유효하지 않은 datetime 형식입니다: {value}") from exc


def _unique_preserving_order(items: List[str]) -> List[str]:
    """순서를 유지하며 중복을 제거합니다."""
    seen: set[str] = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _recursive_diff(left: Dict[str, Any], right: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    """두 딕셔너리의 차이를 재귀적으로 비교합니다."""
    diff: Dict[str, Any] = {}
    keys = set(left.keys()) | set(right.keys())
    for key in sorted(keys):
        path = f"{prefix}.{key}" if prefix else key
        left_value = left.get(key)
        right_value = right.get(key)
        if left_value == right_value:
            continue
        if isinstance(left_value, dict) and isinstance(right_value, dict):
            nested = _recursive_diff(left_value, right_value, path)
            if nested:
                diff[key] = nested
        else:
            diff[key] = {"path": path, "old": left_value, "new": right_value, "changed": True}
    return diff


__all__ = [
    "CognitiveState",
    "Milestone",
    "Perspective",
    "Snapshot",
    "SnapshotComparisonError",
    "SnapshotError",
    "SnapshotManager",
    "SnapshotNotFoundError",
    "SnapshotSerializationError",
    "UserUnderstanding",
    "WillStrength",
]
