"""Organic Thought Seed - Snapshot 테스트

수정된 snapshot.py의 핵심 공개 API를 검증합니다.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from src.core.snapshot import CognitiveState, Perspective, Snapshot, SnapshotManager, WillStrength


class TestWillStrength:
    """의지 강도 테스트"""

    def test_creation(self) -> None:
        ws = WillStrength(direction_score=0.8, specificity_score=0.6)
        assert ws.direction_score == 0.8
        assert ws.specificity_score == 0.6

    def test_combined_strength(self) -> None:
        ws = WillStrength(direction_score=1.0, specificity_score=1.0)
        assert ws.combined_strength == 1.0

    def test_combined_strength_zero(self) -> None:
        ws = WillStrength(direction_score=0.0, specificity_score=0.0)
        assert ws.combined_strength == 0.0

    def test_threshold_check(self) -> None:
        ws_high = WillStrength(direction_score=0.8, specificity_score=0.7)
        ws_low = WillStrength(direction_score=0.2, specificity_score=0.1)
        assert ws_high.combined_strength > 0.5
        assert ws_low.combined_strength < 0.5


class TestPerspective:
    """관점 변화 테스트"""

    def test_creation(self) -> None:
        perspective = Perspective(
            topic="구조 vs 컨텍스트",
            initial_thought="구조가 먼저다",
            evolved_thought="의지가 먼저고 구조는 이를 돕는 도구다",
            reason="대화 속에서 의지의 형성 순간이 더 중요하다는 통찰이 생겼기 때문이다.",
        )
        assert perspective.topic == "구조 vs 컨텍스트"
        assert "의지" in perspective.evolved_thought


class TestCognitiveState:
    """인지 상태 테스트"""

    def test_creation(self) -> None:
        state = CognitiveState(
            direction="인공지능 뇌 만들기",
            will_strength=WillStrength(direction_score=0.8, specificity_score=0.7),
        )
        assert state.direction == "인공지능 뇌 만들기"
        assert state.will_strength.direction_score == 0.8
        assert state.will.startswith("인공지능 뇌 만들기")

    def test_deep_copy(self) -> None:
        original = CognitiveState(
            direction="인공지능 뇌 만들기",
            will_strength=WillStrength(direction_score=0.8, specificity_score=0.7),
            perspectives=[
                Perspective(
                    topic="테스트",
                    initial_thought="처음",
                    evolved_thought="나중",
                    reason="변화",
                )
            ],
            unresolved=["5번 질문"],
            wiki_knowledge={"key": "value"},
            knowledge={"concept": "seed"},
            goals=["실험 설계"],
        )
        clone = original.deep_copy()

        assert clone.direction == original.direction
        assert clone.will_strength.direction_score == original.will_strength.direction_score
        assert len(clone.perspectives) == len(original.perspectives)
        assert clone.unresolved == original.unresolved
        assert clone.wiki_knowledge == original.wiki_knowledge

        clone.unresolved.append("새 질문")
        assert len(clone.unresolved) != len(original.unresolved)

    def test_update_state(self) -> None:
        state = CognitiveState(will="초기 의지")
        state.update_state(
            new_will="새로운 방향으로 위키를 축적한다",
            new_knowledge={"core": "feedback loop"},
            new_experience=["환류 실험 수행"],
            new_goals=["스냅샷 저장", "분신 실행"],
        )
        assert "새로운 방향" in state.direction
        assert state.knowledge["core"] == "feedback loop"
        assert "환류 실험 수행" in state.experience
        assert state.goals == ["스냅샷 저장", "분신 실행"]
        assert state.evolution_timeline

    def test_serialization(self) -> None:
        state = CognitiveState(
            direction="테스트 방향",
            will_strength=WillStrength(direction_score=0.5, specificity_score=0.5),
            knowledge={"k": "v"},
            goals=["검증"],
        )
        data = state.to_dict()
        restored = CognitiveState.from_dict(data)
        assert restored.direction == state.direction
        assert restored.will_strength.direction_score == state.will_strength.direction_score
        assert restored.knowledge == state.knowledge


class TestSnapshotManager:
    """스냅샷 매니저 테스트"""

    def test_save_and_load_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)
            state = CognitiveState(
                direction="테스트",
                will_strength=WillStrength(direction_score=0.7, specificity_score=0.6),
            )
            snapshot = Snapshot(id="seed-001", cognitive_state=state)
            filepath = manager.save(snapshot)
            assert Path(filepath).exists()

            loaded = manager.load("seed-001")
            assert loaded.id == "seed-001"
            assert loaded.cognitive_state.direction == "테스트"

    def test_save_snapshot_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)
            state = CognitiveState(
                direction="호환성 테스트",
                will_strength=WillStrength(direction_score=0.7, specificity_score=0.6),
            )
            filepath = manager.save_snapshot(state)
            assert Path(filepath).exists()
            loaded_state = manager.load_snapshot(state.snapshot_id)
            assert loaded_state.direction == "호환성 테스트"

    def test_list_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SnapshotManager(base_dir=tmpdir)
            snapshot_a = Snapshot(id="seed-a", cognitive_state=CognitiveState(direction="A"))
            snapshot_b = Snapshot(id="seed-b", cognitive_state=CognitiveState(direction="B"))
            manager.save(snapshot_a)
            manager.save(snapshot_b)

            snapshots = manager.list_snapshots()
            assert snapshots == ["seed-a", "seed-b"]

