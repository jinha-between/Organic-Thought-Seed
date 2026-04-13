"""seed_spreader.py의 분신 생성과 실행 결과 구조를 검증합니다."""

from __future__ import annotations

import asyncio

from src.core.config import Config
from src.core.seed_spreader import SeedSpreader, WikiEntry
from src.core.snapshot import CognitiveState, Snapshot, WillStrength


class DeterministicExecutor:
    """테스트용 고정 결과 실행기입니다."""

    async def execute_task(self, clone) -> WikiEntry:  # type: ignore[no-untyped-def]
        return WikiEntry(
            title=f"{clone.assigned_task} 결과",
            summary=f"{clone.id[:8]}가 {clone.assigned_task}를 완료했습니다.",
            content=f"방향: {clone.cognitive_state.direction}\n작업: {clone.assigned_task}",
            tags=["test", clone.assigned_task.split()[0]],
            source_snapshot_id=clone.cognitive_state.snapshot_id,
            clone_id=clone.id,
        )


def make_snapshot() -> Snapshot:
    state = CognitiveState(
        direction="분신 기반 위키 환류 실험",
        will_strength=WillStrength(direction_score=0.85, specificity_score=0.75),
        goals=["핵심 목표 구조화", "위키 축적 전략 검토", "다음 단계 로드맵 제안"],
        knowledge={"phase": "seed spreading"},
    )
    return Snapshot(id="spread-seed-001", cognitive_state=state)


class TestSeedSpreader:
    """SeedSpreader의 생성과 결과 구조를 검증합니다."""

    def test_create_clones_and_execute_tasks(self) -> None:
        snapshot = make_snapshot()
        spreader = SeedSpreader(Config(NUM_CLONES=2), task_executor=DeterministicExecutor())
        tasks = spreader._build_tasks(snapshot)

        clones = spreader._create_clones(snapshot, tasks)
        result = asyncio.run(spreader.spread_seed(snapshot, tasks))

        assert len(clones) == 2
        assert all(clone.assigned_task for clone in clones)
        assert all(clone.cognitive_state.snapshot_id == snapshot.id for clone in clones)
        assert all(clone.cognitive_state.evolution_timeline[-1]["event"] == "분신 생성" for clone in clones)
        assert len(result.wiki_entries) == 2
        assert result.failed_tasks == []
        assert len(result.completed_tasks) == 2

    def test_spread_and_perform_task_returns_expected_structure(self) -> None:
        snapshot = make_snapshot()
        spreader = SeedSpreader(Config(NUM_CLONES=3), task_executor=DeterministicExecutor())

        result = spreader.spread_and_perform_task(snapshot)

        assert result.original_seed_id == snapshot.id
        assert isinstance(result.summary, str) and result.summary
        assert isinstance(result.wiki_entries, list)
        assert isinstance(result.completed_tasks, list)
        assert isinstance(result.failed_tasks, list)
        assert len(result.wiki_entries) == 3
        assert len(result.completed_tasks) == 3
        assert result.failed_tasks == []
        assert all(entry.source_snapshot_id == snapshot.id for entry in result.wiki_entries)
        assert all(entry.tags for entry in result.wiki_entries)

    def test_constructor_uses_config_values(self) -> None:
        config = Config(NUM_CLONES=4, CLONE_TIMEOUT_SECONDS=1.25)

        spreader = SeedSpreader(config, task_executor=DeterministicExecutor())

        assert spreader.clone_count == 4
        assert spreader.default_timeout == 1.25
        assert spreader.config is config
