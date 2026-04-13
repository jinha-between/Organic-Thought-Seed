"""Organic Thought Seed v3의 위키 축적 및 환류 관리 모듈입니다.

분신 실행 결과를 단순 로그로 남기지 않고, 다시 현재 인지 상태를 더 깊게 만드는
환류 구조를 제공합니다. 이 모듈은 `seed_spreader`의 WikiEntry와 `snapshot`의
CognitiveState를 그대로 재사용하여 타입 불일치를 제거합니다.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from .config import Config
from .seed_spreader import SpreadResult, WikiEntry
from .snapshot import CognitiveState, Milestone, Perspective
from .utils import parse_datetime

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProgressReport:
    """위키 축적 상태와 환류 결과를 설명하는 간단한 보고서입니다."""

    title: str
    summary: str
    total_entries: int
    generated_at: datetime = field(default_factory=datetime.now)


class FlowChartGenerator:
    """프로젝트 철학을 텍스트 다이어그램으로 요약하는 도우미입니다."""

    def generate(self, entries: List[WikiEntry]) -> str:
        """위키 항목 목록을 바탕으로 간단한 흐름 설명을 생성합니다."""
        lines = ["Threshold Detector -> Snapshot -> Seed Spreader -> Wiki Manager -> Feedback Loop"]
        if entries:
            lines.append(f"현재 누적 위키 항목 수: {len(entries)}")
            for entry in entries[-3:]:
                lines.append(f"- {entry.title}")
        return "\n".join(lines)


class WikiManager:
    """분신 결과를 위키 지식으로 누적하고 인지 상태로 환류시키는 관리자입니다."""

    WIKI_FILE_NAME = "wiki_entries.json"

    def __init__(self, config: Config) -> None:
        """Config 객체를 받아 위키 저장소를 초기화합니다."""
        self.config = config
        self.base_dir = os.path.abspath(getattr(config, "WIKI_SAVE_PATH", config.SEED_SAVE_PATH))
        os.makedirs(self.base_dir, exist_ok=True)
        self._wiki_file_path = os.path.join(self.base_dir, self.WIKI_FILE_NAME)
        self.entries: List[WikiEntry] = self._load_entries()
        self.flow_chart_generator = FlowChartGenerator()

    def add_entry(self, entry: WikiEntry) -> None:
        """하나의 위키 항목을 누적하고 저장합니다."""
        self.entries.append(copy.deepcopy(entry))
        self._persist_entries()

    def accumulate_results(self, spread_result: SpreadResult) -> List[WikiEntry]:
        """SeedSpreader의 결과를 위키에 누적하고 누적된 항목들을 반환합니다."""
        for entry in spread_result.wiki_entries:
            self.add_entry(entry)
        return copy.deepcopy(spread_result.wiki_entries)

    def search_by_keyword(self, keyword: str) -> List[WikiEntry]:
        """제목, 요약, 본문, 태그에서 키워드를 검색합니다."""
        lowered_keyword = keyword.lower().strip()
        if not lowered_keyword:
            return []
        matched: List[WikiEntry] = []
        for entry in self.entries:
            haystack = " ".join([entry.title, entry.summary, entry.content, " ".join(entry.tags)]).lower()
            if lowered_keyword in haystack:
                matched.append(copy.deepcopy(entry))
        return matched

    def feedback_loop(self, state: CognitiveState) -> CognitiveState:
        """누적된 위키 결과를 현재 인지 상태로 환류시켜 더 깊은 맥락을 형성합니다."""
        updated_state = state.deep_copy()
        direction_keywords = self._extract_keywords(updated_state.direction)
        relevant_entries: List[WikiEntry] = []
        for keyword in direction_keywords[:3]:
            relevant_entries.extend(self.search_by_keyword(keyword))

        if not relevant_entries:
            recent_entries = self.entries[-2:]
            relevant_entries = copy.deepcopy(recent_entries)

        unique_entries = self._unique_entries(relevant_entries)
        for index, entry in enumerate(unique_entries, start=1):
            knowledge_key = f"wiki_feedback_{index}_{entry.clone_id[:8]}"
            updated_state.knowledge[knowledge_key] = entry.summary
            updated_state.wiki_knowledge[knowledge_key] = entry.content[:240]

        if unique_entries:
            updated_state.experience.append(
                f"위키 환류를 통해 {len(unique_entries)}개의 관련 결과가 현재 의지에 연결되었다"
            )
            updated_state.context_essence = (
                f"'{updated_state.direction}'라는 의지가 {len(unique_entries)}개의 환류 결과를 흡수한 상태"
            )
            updated_state.perspectives.append(
                Perspective(
                    initial_thought="분신 결과는 외부 산출물로만 남는다.",
                    evolved_thought="분신 결과는 다시 현재 의지를 깊게 만드는 내부 맥락이 된다.",
                    reason="위키 환류 구조를 통해 결과가 다음 방향 형성의 재료가 되었기 때문이다.",
                    topic="피드백 루프",
                )
            )
            updated_state.conversation_milestones.append(
                Milestone(
                    event="위키 환류 완료",
                    description=f"{len(unique_entries)}개의 위키 결과가 현재 인지 상태에 반영되었습니다.",
                )
            )
            if not any("환류" in goal for goal in updated_state.goals):
                updated_state.goals.append("누적된 위키 지식을 바탕으로 다음 환류 질문을 정교화한다")

        updated_state.add_to_timeline(
            event="피드백 루프",
            description="위키에 누적된 분신 결과가 현재 인지 상태에 반영되었습니다.",
            metadata={
                "reflected_entries": len(unique_entries),
                "available_total_entries": len(self.entries),
            },
        )
        return updated_state

    def generate_direction_question(self, state: CognitiveState) -> str:
        """다음 대화에서 방향성을 더 정교화하기 위한 질문을 생성합니다."""
        recent_titles = ", ".join(entry.title for entry in self.entries[-3:]) if self.entries else "최근 위키 항목 없음"
        primary_goal = state.goals[0] if state.goals else "현재 의지의 다음 단계를 더 구체화하기"
        return (
            f"지금까지의 환류 결과를 보면 '{state.direction}'라는 방향이 형성되어 있습니다. "
            f"특히 '{primary_goal}'를 더 선명하게 만들기 위해, 최근 위키 항목({recent_titles}) 중 어떤 통찰을 다음 스냅샷의 중심으로 삼는 것이 좋을까요?"
        )

    def create_progress_report(self) -> ProgressReport:
        """현재 위키 축적 현황에 대한 간단한 진행 보고서를 생성합니다."""
        summary = (
            f"누적 위키 항목 수는 {len(self.entries)}개이며, 최근 흐름은 다음과 같습니다.\n"
            f"{self.flow_chart_generator.generate(self.entries)}"
        )
        return ProgressReport(
            title="Organic Thought Seed 위키 진행 보고서",
            summary=summary,
            total_entries=len(self.entries),
        )

    def export_json(self) -> str:
        """현재 위키 항목 전체를 JSON 문자열로 내보냅니다."""
        return json.dumps([entry.to_dict() for entry in self.entries], ensure_ascii=False, indent=2)

    def _load_entries(self) -> List[WikiEntry]:
        """저장된 위키 항목 파일을 읽어 복원합니다."""
        if not os.path.exists(self._wiki_file_path):
            return []
        try:
            with open(self._wiki_file_path, "r", encoding="utf-8") as file_handle:
                raw_entries = json.load(file_handle)
        except (OSError, json.JSONDecodeError):
            return []

        entries: List[WikiEntry] = []
        for item in raw_entries:
            entries.append(
                WikiEntry(
                    title=str(item.get("title", "제목 없음")),
                    summary=str(item.get("summary", "")),
                    content=str(item.get("content", "")),
                    tags=list(item.get("tags", [])),
                    source_snapshot_id=str(item.get("source_snapshot_id", "")),
                    clone_id=str(item.get("clone_id", "")) or str(len(entries) + 1),
                    created_at=parse_datetime(item.get("created_at")),
                )
            )
        return entries

    def _persist_entries(self) -> None:
        """위키 항목 목록을 JSON 파일로 저장합니다."""
        temp_path = f"{self._wiki_file_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as file_handle:
                json.dump([entry.to_dict() for entry in self.entries], file_handle, ensure_ascii=False, indent=2)
            os.replace(temp_path, self._wiki_file_path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _extract_keywords(self, text: str) -> List[str]:
        """방향성 문장에서 핵심 키워드를 추출합니다."""
        candidates = re.findall(r"[가-힣A-Za-z]{2,}", text)
        keywords: List[str] = []
        for candidate in candidates:
            if candidate not in keywords:
                keywords.append(candidate)
        return keywords

    def _unique_entries(self, entries: List[WikiEntry]) -> List[WikiEntry]:
        """clone_id를 기준으로 중복 위키 항목을 제거합니다."""
        unique: List[WikiEntry] = []
        seen: set[str] = set()
        for entry in entries:
            if entry.clone_id in seen:
                continue
            seen.add(entry.clone_id)
            unique.append(entry)
        return unique



__all__ = [
    "FlowChartGenerator",
    "ProgressReport",
    "WikiManager",
]
