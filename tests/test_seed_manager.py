"""seed_manager.py의 저장, 로드, 버전 이력 동작을 검증합니다."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.config import Config
from src.core.seed_manager import SeedManager, SeedNotFoundError
from src.core.snapshot import CognitiveState, Snapshot, WillStrength


def make_snapshot(*, snapshot_id: str = "seed-001", direction: str = "위키 환류 구조 고도화") -> Snapshot:
    state = CognitiveState(
        direction=direction,
        will_strength=WillStrength(direction_score=0.8, specificity_score=0.7),
        knowledge={"core": "feedback loop", "status": "draft"},
        experience=["첫 번째 탐색 수행"],
        goals=["스냅샷 저장", "위키 환류 검증"],
        wiki_knowledge={"baseline": "초기 지식"},
    )
    return Snapshot(id=snapshot_id, cognitive_state=state, reason="테스트 저장")


class TestSeedManager:
    """SeedManager의 핵심 저장 계층을 검증합니다."""

    def test_save_and_load_round_trip_preserves_snapshot_state(self, tmp_path: Path) -> None:
        manager = SeedManager(Config(SEED_SAVE_PATH=str(tmp_path)))
        snapshot = make_snapshot()

        saved_version = manager.save_seed(snapshot)
        loaded_snapshot = manager.load_seed(saved_version.version_id)

        assert loaded_snapshot.id == snapshot.id
        assert loaded_snapshot.to_dict() == snapshot.to_dict()
        assert loaded_snapshot.cognitive_state.knowledge == snapshot.cognitive_state.knowledge
        assert loaded_snapshot.cognitive_state.goals == snapshot.cognitive_state.goals

    def test_multiple_saves_increase_version_history(self, tmp_path: Path) -> None:
        manager = SeedManager(Config(SEED_SAVE_PATH=str(tmp_path)))

        first = manager.save_seed(make_snapshot(direction="첫 방향 정리"))
        second = manager.save_seed(make_snapshot(direction="두 번째 방향 정리"))
        third = manager.save_seed(make_snapshot(direction="세 번째 방향 정리"))
        versions = manager.list_versions()
        history = manager.get_evolution_history()

        assert [version.version_number for version in versions] == [1, 2, 3]
        assert first.parent_version_id is None
        assert second.parent_version_id == first.version_id
        assert third.parent_version_id == second.version_id
        assert history.total_versions == 3
        assert history.last_updated is not None

    def test_list_seeds_returns_saved_snapshot_ids_in_latest_first_order(self, tmp_path: Path) -> None:
        manager = SeedManager(Config(SEED_SAVE_PATH=str(tmp_path)))

        manager.save_seed(make_snapshot(snapshot_id="seed-a", direction="A 방향"))
        manager.save_seed(make_snapshot(snapshot_id="seed-b", direction="B 방향"))
        manager.save_seed(make_snapshot(snapshot_id="seed-c", direction="C 방향"))

        assert manager.list_seeds() == ["seed-c", "seed-b", "seed-a"]

    def test_load_seed_raises_error_for_missing_seed(self, tmp_path: Path) -> None:
        manager = SeedManager(Config(SEED_SAVE_PATH=str(tmp_path)))

        with pytest.raises(SeedNotFoundError):
            manager.load_seed("missing-seed-id")
