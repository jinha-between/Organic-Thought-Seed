"""wiki_manager.py의 누적, 환류, 질문 생성 동작을 검증합니다."""

from __future__ import annotations

from pathlib import Path

from src.core.config import Config
from src.core.seed_spreader import SpreadResult, WikiEntry
from src.core.snapshot import CognitiveState, WillStrength
from src.core.wiki_manager import WikiManager


def make_entry(*, clone_id: str, title: str, summary: str, content: str, tags: list[str]) -> WikiEntry:
    return WikiEntry(
        title=title,
        summary=summary,
        content=content,
        tags=tags,
        source_snapshot_id="seed-001",
        clone_id=clone_id,
    )


def make_state() -> CognitiveState:
    return CognitiveState(
        direction="위키 환류 구조를 정교화한다",
        will_strength=WillStrength(direction_score=0.8, specificity_score=0.7),
        goals=["환류 질문 설계", "분신 결과 누적"],
        knowledge={"baseline": "seed"},
        experience=["초기 상태"],
    )


class TestWikiManager:
    """WikiManager의 핵심 공개 동작을 검증합니다."""

    def test_accumulate_results_adds_entries_and_returns_copies(self, tmp_path: Path) -> None:
        manager = WikiManager(Config(WIKI_SAVE_PATH=str(tmp_path)))
        entries = [
            make_entry(
                clone_id="clone-a",
                title="위키 환류 분석",
                summary="환류 포인트를 정리했습니다.",
                content="위키 환류 구조의 핵심 단계를 분석했습니다.",
                tags=["위키", "환류"],
            ),
            make_entry(
                clone_id="clone-b",
                title="분신 결과 요약",
                summary="분신 산출물을 축적했습니다.",
                content="분신 결과를 위키 지식으로 누적하는 전략입니다.",
                tags=["분신", "축적"],
            ),
        ]
        spread_result = SpreadResult(
            original_seed_id="seed-001",
            wiki_entries=entries,
            completed_tasks=["task-a", "task-b"],
            failed_tasks=[],
            summary="정상 완료",
        )

        accumulated = manager.accumulate_results(spread_result)

        assert len(accumulated) == 2
        assert len(manager.entries) == 2
        assert accumulated[0] is not entries[0]
        assert [entry.title for entry in manager.entries] == ["위키 환류 분석", "분신 결과 요약"]

    def test_feedback_loop_returns_updated_state_without_mutating_original(self, tmp_path: Path) -> None:
        manager = WikiManager(Config(WIKI_SAVE_PATH=str(tmp_path)))
        manager.add_entry(
            make_entry(
                clone_id="clone-a",
                title="위키 환류 분석",
                summary="위키 환류가 현재 의지를 강화합니다.",
                content="위키 환류 구조를 정교화하는 방법과 다음 질문 후보를 정리했습니다.",
                tags=["위키", "환류", "질문"],
            )
        )
        manager.add_entry(
            make_entry(
                clone_id="clone-b",
                title="구조 실험 메모",
                summary="구조 정교화 아이디어를 제안합니다.",
                content="구조와 환류의 연결 맥락을 설명합니다.",
                tags=["구조", "정교화"],
            )
        )
        original_state = make_state()

        updated_state = manager.feedback_loop(original_state)

        assert updated_state is not original_state
        assert original_state.knowledge == {"baseline": "seed"}
        assert any(key.startswith("wiki_feedback_") for key in updated_state.knowledge)
        assert any(key.startswith("wiki_feedback_") for key in updated_state.wiki_knowledge)
        assert len(updated_state.experience) > len(original_state.experience)
        assert updated_state.evolution_timeline[-1]["event"] == "피드백 루프"
        assert updated_state.context_essence != original_state.context_essence
        assert updated_state.perspectives
        assert updated_state.conversation_milestones

    def test_generate_direction_question_uses_state_goal_and_recent_titles(self, tmp_path: Path) -> None:
        manager = WikiManager(Config(WIKI_SAVE_PATH=str(tmp_path)))
        manager.add_entry(
            make_entry(
                clone_id="clone-a",
                title="최근 환류 메모",
                summary="최근 메모 요약",
                content="최근 환류 내용",
                tags=["환류"],
            )
        )
        manager.add_entry(
            make_entry(
                clone_id="clone-b",
                title="다음 단계 로드맵",
                summary="로드맵 요약",
                content="로드맵 상세",
                tags=["로드맵"],
            )
        )
        state = make_state()

        question = manager.generate_direction_question(state)

        assert state.direction in question
        assert state.goals[0] in question
        assert "최근 환류 메모" in question
        assert "다음 단계 로드맵" in question

    def test_constructor_uses_config_path(self, tmp_path: Path) -> None:
        config = Config(WIKI_SAVE_PATH=str(tmp_path / "wiki-store"))

        manager = WikiManager(config)

        assert manager.base_dir == str((tmp_path / "wiki-store").resolve())
        assert manager.entries == []
        assert Path(manager.base_dir).exists()
