"""Organic Thought Seed v3의 씨앗 확산기입니다.

저장된 스냅샷을 여러 작업 분신으로 복제하여 병렬 탐색을 수행하고, 각 결과를 위키
항목으로 되돌립니다. 실제 외부 API 없이도 실행 가능하도록 모든 작업 수행은 모의
시뮬레이션 기반으로 설계되어 있습니다.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol

from .config import Config
from .snapshot import CognitiveState, Snapshot

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WikiEntry:
    """분신 실행 결과가 환류되어 축적되는 최소 위키 단위입니다."""

    title: str
    summary: str
    content: str
    tags: List[str]
    source_snapshot_id: str
    clone_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """객체를 JSON 직렬화 가능한 딕셔너리로 변환합니다."""
        return {
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "tags": list(self.tags),
            "source_snapshot_id": self.source_snapshot_id,
            "clone_id": self.clone_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class CloneAgent:
    """원본 인지 상태에서 복제된 작업 분신입니다."""

    id: str
    cognitive_state: CognitiveState
    assigned_task: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SpreadResult:
    """씨앗 확산 실행의 종합 결과입니다."""

    original_seed_id: str
    wiki_entries: List[WikiEntry]
    completed_tasks: List[str]
    failed_tasks: List[str]
    summary: str
    created_at: datetime = field(default_factory=datetime.now)


class TaskExecutor(Protocol):
    """분신이 맡은 작업을 실제 또는 모의 방식으로 수행하는 인터페이스입니다."""

    async def execute_task(self, clone: CloneAgent) -> WikiEntry:
        """주어진 분신의 작업을 실행하고 WikiEntry를 반환합니다."""


class MockTaskExecutor:
    """LLM API 없이도 씨앗 확산 데모를 수행하기 위한 모의 실행기입니다."""

    async def execute_task(self, clone: CloneAgent) -> WikiEntry:
        """작업 설명과 인지 상태를 바탕으로 시뮬레이션된 위키 항목을 생성합니다."""
        await asyncio.sleep(0.05)
        state = clone.cognitive_state
        task = clone.assigned_task
        summary = (
            f"분신 {clone.id[:8]}은(는) '{state.direction}'라는 의지를 '{task}' 관점에서 해석했습니다."
        )
        content = (
            f"원본 의지: {state.will}\n\n"
            f"할당 작업: {task}\n\n"
            f"분석 결과: 이 작업은 '{state.context_essence}'라는 맥락을 바탕으로, "
            f"사용자 승인형 구조를 유지하면서도 구체적인 실행 가능성을 높이는 방향으로 정리되었습니다. "
            f"현재 목표 수는 {len(state.goals)}개이며, 누적 지식 수는 {len(state.knowledge)}개입니다."
        )
        tags = [
            "organic-thought-seed",
            task.split()[0],
            state.direction.split()[0] if state.direction.split() else "의지",
        ]
        return WikiEntry(
            title=f"{task} 관점 결과",
            summary=summary,
            content=content,
            tags=list(dict.fromkeys(tags)),
            source_snapshot_id=state.snapshot_id,
        )


class SeedSpreader:
    """저장된 씨앗을 작업 분신으로 확산시키는 클래스입니다."""

    def __init__(self, config: Config, task_executor: Optional[TaskExecutor] = None) -> None:
        """Config 객체와 실행기를 받아 분신 확산기를 초기화합니다."""
        self.config = config
        self.task_executor: TaskExecutor = task_executor or MockTaskExecutor()
        self.clone_count = int(getattr(config, "NUM_CLONES", 3))
        self.default_timeout = float(getattr(config, "CLONE_TIMEOUT_SECONDS", 5.0))

    def spread_and_perform_task(self, snapshot: Snapshot) -> SpreadResult:
        """main.py 호환용 동기 래퍼로, Snapshot을 받아 확산 결과를 반환합니다."""
        tasks = self._build_tasks(snapshot)
        try:
            return asyncio.run(self.spread_seed(snapshot, tasks))
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.spread_seed(snapshot, tasks))
            finally:
                loop.close()

    async def spread_seed(
        self,
        snapshot: Snapshot,
        tasks: List[str],
        timeout_per_clone: Optional[float] = None,
    ) -> SpreadResult:
        """Snapshot을 여러 분신으로 확산하여 위키 항목을 생성합니다."""
        clones = self._create_clones(snapshot, tasks)
        timeout = timeout_per_clone or self.default_timeout
        results = await asyncio.gather(
            *(self._execute_clone(clone, timeout) for clone in clones),
            return_exceptions=True,
        )

        wiki_entries: List[WikiEntry] = []
        completed_tasks: List[str] = []
        failed_tasks: List[str] = []

        for clone, result in zip(clones, results):
            if isinstance(result, Exception):
                failed_tasks.append(f"{clone.assigned_task}: {result}")
                continue
            wiki_entries.append(result)
            completed_tasks.append(clone.assigned_task)

        summary = self._build_summary(snapshot, completed_tasks, failed_tasks, wiki_entries)
        return SpreadResult(
            original_seed_id=snapshot.id,
            wiki_entries=wiki_entries,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            summary=summary,
        )

    def _build_tasks(self, snapshot: Snapshot) -> List[str]:
        """현재 스냅샷의 목표를 기반으로 분신 작업 목록을 생성합니다."""
        goals = snapshot.cognitive_state.goals
        candidate_tasks = [f"핵심 목표 분석: {goal}" for goal in goals]
        fallback_tasks = [
            "개념 구조화 및 핵심 질문 도출",
            "리스크와 한계 분석",
            "다음 단계 실행 로드맵 제안",
            "사용자 승인형 상호작용 개선안 도출",
            "위키 환류 포인트 정리",
        ]
        for task in fallback_tasks:
            if task not in candidate_tasks:
                candidate_tasks.append(task)
        return candidate_tasks[: self.clone_count]

    def _create_clones(self, snapshot: Snapshot, tasks: List[str]) -> List[CloneAgent]:
        """원본 스냅샷으로부터 작업 분신들을 생성합니다."""
        clones: List[CloneAgent] = []
        for task in tasks:
            state_copy = snapshot.cognitive_state.deep_copy()
            state_copy.add_to_timeline(
                event="분신 생성",
                description=f"'{task}' 작업을 위한 분신이 생성되었습니다.",
                metadata={"task": task},
            )
            clones.append(
                CloneAgent(
                    id=str(uuid.uuid4()),
                    cognitive_state=state_copy,
                    assigned_task=task,
                )
            )
        return clones

    async def _execute_clone(self, clone: CloneAgent, timeout: float) -> WikiEntry:
        """개별 분신 작업을 타임아웃과 함께 실행합니다."""
        return await asyncio.wait_for(self.task_executor.execute_task(clone), timeout=timeout)

    def _build_summary(
        self,
        snapshot: Snapshot,
        completed_tasks: List[str],
        failed_tasks: List[str],
        wiki_entries: List[WikiEntry],
    ) -> str:
        """확산 실행 결과를 한 문단 요약으로 정리합니다."""
        return (
            f"스냅샷 {snapshot.id}에서 시작된 씨앗 확산이 완료되었습니다. "
            f"총 {len(completed_tasks)}개의 작업이 성공했고 {len(failed_tasks)}개의 작업이 실패했습니다. "
            f"생성된 위키 항목은 {len(wiki_entries)}개이며, 현재 의지는 '{snapshot.cognitive_state.direction}'입니다."
        )


__all__ = [
    "CloneAgent",
    "MockTaskExecutor",
    "SeedSpreader",
    "SpreadResult",
    "TaskExecutor",
    "WikiEntry",
]
