"""Organic Thought Seed 메인 오케스트레이션 모듈.

이 모듈은 ThresholdDetector, SeedManager, SeedSpreader, WikiManager를 조율하여
사용자 제안형의 유기적 사이클을 시뮬레이션합니다. 실제 LLM API 없이도 전체 흐름이
재현되도록 입력과 판단은 휴리스틱 및 모의 실행으로 구성되어 있습니다.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

if __name__ == "__main__" and __package__ in {None, ""}:
    _src_root = Path(__file__).resolve().parents[1]
    if str(_src_root.parent) not in sys.path:
        sys.path.insert(0, str(_src_root.parent))
    __package__ = "core"

from .config import Config
from .seed_manager import SeedManager, SeedManagerError, SeedNotFoundError
from .seed_spreader import SeedSpreader, SpreadResult
from .snapshot import CognitiveState, Snapshot
from .threshold_detector import ThresholdDetector
from .wiki_manager import WikiManager

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """CLI 실행용 기본 로깅 설정을 적용합니다."""
    level_name = os.getenv("OTS_LOG_LEVEL", "INFO").strip().upper() or "INFO"
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def log_event(level: int, event: str, **fields: Any) -> None:
    """JSON 문자열 기반의 구조화된 로그 이벤트를 남깁니다."""
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))


class SeedService:
    """Organic Thought Seed 시스템의 핵심 오케스트레이터입니다."""

    def __init__(
        self,
        config: Config,
        threshold_detector: ThresholdDetector,
        seed_manager: SeedManager,
        seed_spreader: SeedSpreader,
        wiki_manager: WikiManager,
        initial_cognitive_state: Optional[CognitiveState] = None,
        auto_approve: Optional[bool] = None,
    ) -> None:
        """SeedService를 초기화하고 각 모듈을 연결합니다."""
        self.config = config
        self.threshold_detector = threshold_detector
        self.seed_manager = seed_manager
        self.seed_spreader = seed_spreader
        self.wiki_manager = wiki_manager
        self.auto_approve = self._resolve_auto_approve(auto_approve)
        self.current_cognitive_state: CognitiveState = initial_cognitive_state or CognitiveState(
            will="초기 의지: 세상의 지식을 탐색하고 이해합니다.",
            knowledge={},
            experience=["초기 상태에서 열린 탐구를 시작함"],
            goals=["새로운 지식 습득", "시스템 안정화"],
        )
        self.current_cognitive_state.add_to_timeline(
            event="SeedService 초기화",
            description="Organic Thought Seed의 오케스트레이터가 시작되었습니다.",
            metadata={"auto_approve": self.auto_approve},
        )
        log_event(
            logging.INFO,
            "seed_service_initialized",
            auto_approve=self.auto_approve,
            current_will=self.current_cognitive_state.will,
        )

    def run_cycle(self, conversation_input: str) -> None:
        """Organic Thought Seed의 핵심 사이클을 1회 실행합니다."""
        conversation_history = (
            f"현재 의지: {self.current_cognitive_state.will}. 최근 대화: {conversation_input}"
        )
        log_event(
            logging.INFO,
            "cycle_started",
            conversation_preview=conversation_input[:80],
            current_will=self.current_cognitive_state.will,
        )

        if not self.threshold_detector.detect(conversation_history):
            log_event(
                logging.INFO,
                "cycle_threshold_not_met",
                conversation_preview=conversation_input[:80],
            )
            return

        proposal = self.threshold_detector.get_cognitive_state_proposal(conversation_history)
        log_event(
            logging.INFO,
            "threshold_detected",
            proposed_will=proposal.get("will", "N/A"),
            proposed_goal_count=len(proposal.get("goals", [])),
        )
        user_response = self._request_user_approval(proposal)

        if user_response != "y":
            log_event(logging.INFO, "proposal_declined")
            return

        self.current_cognitive_state.update_state(
            new_will=proposal.get("will"),
            new_knowledge=proposal.get("knowledge"),
            new_experience=proposal.get("experience"),
            new_goals=proposal.get("goals"),
        )
        self.current_cognitive_state.add_to_timeline(
            event="새로운 씨앗 저장",
            description="사용자 승인 후 새로운 의지가 스냅샷으로 저장되었습니다.",
            metadata={"will": self.current_cognitive_state.will},
        )

        snapshot_id = str(uuid.uuid4())
        new_snapshot = Snapshot(id=snapshot_id, cognitive_state=self.current_cognitive_state)
        saved_version = self.seed_manager.save_seed(new_snapshot)
        log_event(
            logging.INFO,
            "seed_saved",
            version_number=saved_version.version_number,
            snapshot_id=new_snapshot.id,
        )

        task_results = self.seed_spreader.spread_and_perform_task(new_snapshot)
        self._show_spread_summary(task_results)

        accumulated = self.wiki_manager.accumulate_results(task_results)
        log_event(logging.INFO, "wiki_accumulated", entry_count=len(accumulated))

        self.current_cognitive_state = self.wiki_manager.feedback_loop(self.current_cognitive_state)
        direction_question = self.wiki_manager.generate_direction_question(self.current_cognitive_state)
        log_event(
            logging.INFO,
            "cycle_completed",
            direction_question=direction_question,
            current_will=self.current_cognitive_state.will,
        )

    def load_and_resume(self, seed_id: str) -> bool:
        """저장된 씨앗을 로드하여 이전 상태에서 이어갑니다."""
        log_event(logging.INFO, "seed_load_requested", seed_id=seed_id)
        try:
            loaded_snapshot = self.seed_manager.load_seed(seed_id)
        except SeedNotFoundError:
            logger.warning(json.dumps({"event": "seed_not_found", "seed_id": seed_id}, ensure_ascii=False))
            return False
        except SeedManagerError:
            logger.exception(json.dumps({"event": "seed_load_failed", "seed_id": seed_id}, ensure_ascii=False))
            return False

        self.current_cognitive_state = loaded_snapshot.cognitive_state
        self.current_cognitive_state.add_to_timeline(
            event="씨앗 로드 및 재개",
            description=f"씨앗 '{seed_id}'를 로드하여 세션을 재개했습니다.",
        )
        log_event(
            logging.INFO,
            "seed_loaded",
            seed_id=seed_id,
            current_will=self.current_cognitive_state.will,
        )
        return True

    def show_evolution(self) -> None:
        """현재 인지 상태의 진화 타임라인을 로그로 출력합니다."""
        timeline = self.current_cognitive_state.evolution_timeline
        if not timeline:
            log_event(logging.INFO, "evolution_timeline_empty")
            return

        for index, event in enumerate(timeline, start=1):
            timestamp = event.get("timestamp", "시간 정보 없음")
            description = event.get("description") or event.get("event") or "설명 없음"
            data = event.get("data") or event.get("metadata") or {}
            log_event(
                logging.INFO,
                "evolution_timeline_entry",
                index=index,
                timestamp=timestamp,
                description=description,
                metadata=data,
            )

    def _resolve_auto_approve(self, auto_approve: Optional[bool]) -> bool:
        """환경 변수와 인자를 종합하여 자동 승인 여부를 결정합니다."""
        if auto_approve is not None:
            return auto_approve
        env_value = os.getenv("OTS_AUTO_APPROVE", "0").strip().lower()
        return env_value in {"1", "true", "yes"}

    def _request_user_approval(self, proposal: Dict[str, Any]) -> str:
        """인터랙티브 환경과 비인터랙티브 환경을 모두 지원하는 승인 입력 래퍼입니다."""
        if self.auto_approve:
            log_event(logging.INFO, "auto_approval_enabled", proposed_will=proposal.get("will", "N/A"))
            return "y"

        logger.info("저장 후보 의지: %s", proposal.get("will", "N/A"))
        logger.info("저장 후보 목표: %s", proposal.get("goals", []))
        try:
            return input("저장하려면 'y'를 입력하세요 (아무 키나 누르면 건너뛰기): ").strip().lower()
        except EOFError:
            logger.info(
                json.dumps(
                    {"event": "approval_skipped_due_to_missing_stdin", "default_action": "decline"},
                    ensure_ascii=False,
                )
            )
            return "n"

    def _show_spread_summary(self, result: SpreadResult) -> None:
        """분신 실행 결과를 구조화된 로그로 출력합니다."""
        log_event(logging.INFO, "spread_summary", summary=result.summary, wiki_entry_count=len(result.wiki_entries))
        for entry in result.wiki_entries:
            log_event(logging.INFO, "wiki_entry_generated", title=entry.title, clone_id=entry.clone_id)



def run_demo() -> None:
    """CLI 데모를 실행합니다."""
    configure_logging()
    config = Config()
    log_event(logging.INFO, "config_loaded", config=config.to_log_dict())

    threshold_detector = ThresholdDetector(config)
    seed_manager = SeedManager(config)
    seed_spreader = SeedSpreader(config)
    wiki_manager = WikiManager(config)

    seed_service = SeedService(
        config=config,
        threshold_detector=threshold_detector,
        seed_manager=seed_manager,
        seed_spreader=seed_spreader,
        wiki_manager=wiki_manager,
    )

    conversations: List[str] = [
        "안녕하세요, AI. 오늘 어떤 흥미로운 것을 배우셨나요?",
        "최근 연구 동향에 따르면, 양자 컴퓨팅 분야에서 새로운 돌파구가 마련되었다고 합니다. 이 정보가 당신의 의지에 어떤 영향을 미칠까요?",
        "이 새로운 양자 컴퓨팅 기술은 기존의 암호화 방식을 무력화할 수 있는 잠재력을 가지고 있습니다. 이에 대한 당신의 생각은 무엇인가요? 중요한 결정이 필요할 것 같습니다.",
        "음, 이 기술의 윤리적 함의와 사회적 영향에 대해 더 깊이 탐구해야 할 것 같습니다. 다음 목표를 설정해주세요.",
        "좋습니다. 다음 대화에서는 이 기술의 실제 적용 사례와 예상되는 문제점에 대해 논의해봅시다.",
    ]

    available_seeds = seed_manager.list_seeds()
    if available_seeds:
        log_event(logging.INFO, "existing_seeds_detected", seed_count=len(available_seeds))
        if os.getenv("OTS_AUTO_LOAD_LATEST", "0").strip().lower() in {"1", "true", "yes"}:
            seed_service.load_and_resume(available_seeds[0])
        elif not seed_service.auto_approve:
            try:
                load_choice = input("로드할 씨앗의 번호를 입력하거나, 새로 시작하려면 Enter를 누르세요: ").strip()
            except EOFError:
                load_choice = ""
            if load_choice:
                try:
                    choice_idx = int(load_choice) - 1
                    if 0 <= choice_idx < len(available_seeds):
                        seed_service.load_and_resume(available_seeds[choice_idx])
                except ValueError:
                    logger.info(json.dumps({"event": "invalid_seed_selection", "input": load_choice}, ensure_ascii=False))

    for index, conversation in enumerate(conversations, start=1):
        log_event(logging.INFO, "demo_conversation_started", index=index, conversation_preview=conversation[:80])
        seed_service.run_cycle(conversation)
        time.sleep(0.1)

    seed_service.show_evolution()
    log_event(logging.INFO, "demo_finished")


if __name__ == "__main__":
    try:
        run_demo()
    except (SeedManagerError, OSError, ValueError) as exc:
        logger.exception(json.dumps({"event": "demo_failed", "error_type": type(exc).__name__}, ensure_ascii=False))
        raise
