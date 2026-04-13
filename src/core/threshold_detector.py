"""Organic Thought Seed v3의 의지 임계점 감지기를 정의합니다.

이 모듈은 대화가 어느 순간 단순한 반응을 넘어 **저장할 가치가 있는 의지**로
응축되었는지를 판별합니다. 실제 LLM 호출 없이도 실행 가능하도록 모든 판단은
휴리스틱과 시뮬레이션 기반으로 구성되어 있습니다.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Sequence

from .config import Config

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """의지 형성 여부를 판단하기 위한 신호 유형입니다."""

    DIRECTION = "direction"
    SPECIFICITY = "specificity"
    PERSISTENCE = "persistence"
    USER_ALIGNMENT = "user_alignment"
    EXECUTION_READINESS = "execution_readiness"
    REFLECTIVE_DEPTH = "reflective_depth"


@dataclass(slots=True)
class Signal:
    """하나의 감지 신호와 그 근거를 표현합니다."""

    signal_type: SignalType
    score: float
    evidence: str


@dataclass
class Proposal:
    """임계점 감지 결과와 사용자에게 제안할 내용을 담습니다."""

    should_propose: bool
    confidence: float
    reasoning: str
    signals: List[Signal] = field(default_factory=list)
    suggested_will: str = ""
    suggested_goals: List[str] = field(default_factory=list)
    suggested_knowledge: Dict[str, Any] = field(default_factory=dict)
    suggested_experience: List[str] = field(default_factory=list)


class ThresholdDetector:
    """대화에서 저장 가능한 의지 형성을 감지하는 클래스입니다."""

    _TRAILING_PARTICLES = (
        "으로써",
        "으로서",
        "에게서",
        "에서는",
        "으로",
        "에게",
        "에서",
        "까지",
        "부터",
        "처럼",
        "보다",
        "마저",
        "조차",
        "에게",
        "와",
        "과",
        "을",
        "를",
        "은",
        "는",
        "이",
        "가",
        "의",
        "에",
        "로",
        "도",
        "만",
    )
    _COMMON_STOPWORDS = {
        "현재",
        "최근",
        "대화",
        "사용자",
        "그리고",
        "그러나",
        "그것",
        "대한",
        "하는",
        "있다",
        "하기",
        "위한",
        "통해",
        "다음",
        "이것",
        "저것",
        "무엇",
        "어떻게",
        "질문",
        "응답",
        "정도",
        "부분",
        "방식",
        "결과",
        "문제점",
        "중요",
        "명확",
        "구간",
        "도달",
        "시도",
        "보입니다",
        "새로운",
        "초기",
        "상태",
        "세상",
        "시스템",
        "탐구",
        "구조화",
        "실행",
        "저장",
        "검토",
        "형성",
        "설정",
        "환류",
        "논의",
        "목표",
        "의지",
        "좋",
        "같",
        "있",
        "미칠",
        "today",
        "좋습니다",
        "같습니다",
        "있습니다",
        "됩니다",
        "합니다",
        "했습니다",
        "봅시다",
        "겠습니다",
        "입니다",
        "습니다",
        "따르면",
        "따르",
        "무엇인가요",
        "어떤",
        "그래서",
        "하지만",
        "이에",
        "또한",
        "이런",
        "해야",
        "안녕하세요",
    }
    _PREDICATE_SUFFIXES = (
        # 4+ syllable endings (longest first for greedy match)
        "되었습니다",
        "되었다고",
        "해봅시다",
        "해주세요",
        "했습니다",
        "가지고",
        # 3 syllable
        "합니다",
        "하였다",
        "입니다",
        "인가요",
        "일까요",
        "었다고",
        "습니다",
        "하려는",
        "에서는",
        "라는",
        "적으로",
        # 2 syllable
        "해야",
        "하려",
        "하며",
        "하고",
        "한다",
        "했던",
        "했다",
        "되는",
        "된다",
        "까요",
        "이며",
        "이다",
        "적인",
        "적이",
        # 1 syllable verb/adjective endings (for 용언 활용형 정규화)
        "으면",
        "르면",
        "면",
        "할",
        "한",
        "할",
        "된",
        "는",
        "을",
        "를",
        "적",
    )
    _BOILERPLATE_KEYWORDS = {
        "사용자",
        "함께",
        "실행",
        "가능",
        "가능한",
        "질문",
        "지식",
        "위키",
        "축적",
        "중심",
        "구조",
        "단계",
        "맥락",
        "명확",
        "반영",
        "시도",
        "다음",
    }

    def __init__(self, config: Config) -> None:
        """Config 객체를 받아 임계값과 감지 규칙을 초기화합니다."""
        self.config = config
        self.threshold = float(getattr(config, "THRESHOLD_SCORE", 0.7))
        self.direction_keywords = [
            "방향",
            "의지",
            "목표",
            "원한다",
            "탐구",
            "구축",
            "설계",
            "정리",
            "축적",
            "환류",
        ]
        self.specificity_keywords = [
            "구체",
            "단계",
            "로드맵",
            "방법",
            "구조",
            "모듈",
            "테스트",
            "저장",
            "실행",
            "버전",
        ]
        self.persistence_keywords = [
            "계속",
            "반복",
            "누적",
            "축적",
            "지속",
            "환류",
            "다시",
            "진화",
        ]
        self.alignment_keywords = [
            "사용자",
            "제안",
            "승인",
            "함께",
            "질문",
            "검토",
            "선택",
        ]
        self.execution_keywords = [
            "실행",
            "데모",
            "구현",
            "작동",
            "테스트",
            "배포",
            "저장",
        ]
        self.reflective_keywords = [
            "왜",
            "의미",
            "철학",
            "본질",
            "관점",
            "맥락",
            "이유",
            "영향",
            "윤리",
            "사회",
            "질문",
        ]

    def detect(self, conversation_history: str | Sequence[Dict[str, str]]) -> bool:
        """main.py 호환용 불리언 API입니다."""
        proposal = self.detect_threshold(conversation_history)
        return proposal.should_propose

    def get_cognitive_state_proposal(
        self,
        conversation_history: str | Sequence[Dict[str, str]],
    ) -> Dict[str, Any]:
        """main.py가 기대하는 인지 상태 제안 딕셔너리를 반환합니다."""
        proposal = self.detect_threshold(conversation_history)
        return {
            "will": proposal.suggested_will,
            "goals": proposal.suggested_goals,
            "knowledge": proposal.suggested_knowledge,
            "experience": proposal.suggested_experience,
            "confidence": proposal.confidence,
            "reasoning": proposal.reasoning,
            "should_propose": proposal.should_propose,
        }

    def detect_threshold(self, conversation_history: str | Sequence[Dict[str, str]]) -> Proposal:
        """대화가 의지 저장 임계점을 넘었는지 종합적으로 판정합니다."""
        turns = self._normalize_history(conversation_history)
        combined_text = "\n".join(turn["content"] for turn in turns).strip()
        if not combined_text:
            return Proposal(
                should_propose=False,
                confidence=0.0,
                reasoning="분석할 대화 내용이 비어 있습니다.",
            )

        signals = [
            self._score_direction(combined_text),
            self._score_specificity(combined_text),
            self._score_persistence(combined_text),
            self._score_user_alignment(combined_text),
            self._score_execution_readiness(combined_text),
            self._score_reflective_depth(combined_text),
        ]
        confidence = round(sum(signal.score for signal in signals) / len(signals), 3)
        should_propose = confidence >= self.threshold
        proposal_payload = self._build_proposal_payload(turns, combined_text, signals, confidence)

        reasoning_lines = [
            f"평균 신호 점수는 {confidence:.2f}이며 임계값은 {self.threshold:.2f}입니다.",
            "세부 신호 분석:",
        ]
        for signal in signals:
            reasoning_lines.append(
                f"- {signal.signal_type.value}: {signal.score:.2f} ({signal.evidence})"
            )
        reasoning_lines.append(
            "사용자 승인 단계로 제안할 가치가 있습니다."
            if should_propose
            else "아직 저장 가능한 의지로 보기에는 신호가 더 필요합니다."
        )

        return Proposal(
            should_propose=should_propose,
            confidence=confidence,
            reasoning="\n".join(reasoning_lines),
            signals=signals,
            suggested_will=proposal_payload["will"],
            suggested_goals=proposal_payload["goals"],
            suggested_knowledge=proposal_payload["knowledge"],
            suggested_experience=proposal_payload["experience"],
        )

    def _normalize_history(
        self,
        conversation_history: str | Sequence[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """문자열 또는 구조화된 대화 입력을 내부 공통 형식으로 정규화합니다."""
        if isinstance(conversation_history, str):
            current_will, recent_conversation = self._extract_sections(conversation_history)
            turns: List[Dict[str, str]] = []
            if current_will:
                turns.append(
                    {"role": "assistant", "content": current_will, "source": "current_will"}
                )
            if recent_conversation:
                turns.extend(self._split_recent_conversation(recent_conversation))
            if not turns:
                turns.append(
                    {"role": "user", "content": conversation_history.strip(), "source": "conversation"}
                )
            turns.append(
                {
                    "role": "assistant",
                    "content": self._build_reflective_mirror(
                        current_will,
                        recent_conversation or conversation_history,
                    ),
                    "source": "reflective_mirror",
                }
            )
            return turns
        return [
            {
                "role": str(turn.get("role", "user")),
                "content": str(turn.get("content", "")).strip(),
                "source": str(turn.get("source", "conversation")),
            }
            for turn in conversation_history
            if str(turn.get("content", "")).strip()
        ]

    def _extract_sections(self, raw_text: str) -> tuple[str, str]:
        """데모 문자열에서 현재 의지와 최근 대화 섹션을 추출합니다."""
        normalized = raw_text.strip()
        current_will_match = re.search(r"현재 의지\s*:\s*(.+?)(?:\n\s*최근 대화\s*:|$)", normalized, re.S)
        recent_match = re.search(r"최근 대화\s*:\s*(.+)$", normalized, re.S)
        current_will = current_will_match.group(1).strip() if current_will_match else ""
        recent_conversation = recent_match.group(1).strip() if recent_match else normalized
        return current_will, recent_conversation

    def _split_recent_conversation(self, text: str) -> List[Dict[str, str]]:
        """최근 대화 문자열을 간단한 대화 턴 목록으로 분해합니다."""
        segments = [segment.strip() for segment in re.split(r"[\n.!?]+", text) if segment.strip()]
        if not segments:
            return []
        turns: List[Dict[str, str]] = []
        for index, segment in enumerate(segments):
            role = "user" if index % 2 == 0 else "assistant"
            turns.append({"role": role, "content": segment, "source": "recent_conversation"})
        return turns

    def _build_reflective_mirror(self, current_will: str, recent_conversation: str) -> str:
        """의지 형성의 메타 수준 단서를 보강하는 반영 문장을 생성합니다."""
        base_direction = current_will or "새로운 방향"
        return (
            f"이 대화는 '{base_direction}'를 더 명확한 구조와 단계로 옮기려는 시도로 보입니다. "
            f"특히 다음 맥락이 중요합니다: {recent_conversation[:140]}"
        )

    def _score_direction(self, text: str) -> Signal:
        """방향성이 드러나는 정도를 측정합니다."""
        score = self._keyword_score(text, self.direction_keywords)
        return Signal(SignalType.DIRECTION, score, "방향·목표·의지 관련 표현의 밀도")

    def _score_specificity(self, text: str) -> Signal:
        """구체적인 실행 구조가 제시되는 정도를 측정합니다."""
        score = self._keyword_score(text, self.specificity_keywords)
        return Signal(SignalType.SPECIFICITY, score, "단계·구조·방법·테스트 언급 빈도")

    def _score_persistence(self, text: str) -> Signal:
        """지속성·누적성·환류 의지가 표현되는 정도를 측정합니다."""
        score = self._keyword_score(text, self.persistence_keywords)
        return Signal(SignalType.PERSISTENCE, score, "지속·축적·반복·진화 관련 표현")

    def _score_user_alignment(self, text: str) -> Signal:
        """사용자 승인과 제안 구조가 반영되는 정도를 측정합니다."""
        score = self._keyword_score(text, self.alignment_keywords)
        return Signal(SignalType.USER_ALIGNMENT, score, "사용자·제안·승인 관련 표현")

    def _score_execution_readiness(self, text: str) -> Signal:
        """실행 가능성 또는 데모 지향성이 드러나는 정도를 측정합니다."""
        score = self._keyword_score(text, self.execution_keywords)
        return Signal(SignalType.EXECUTION_READINESS, score, "구현·실행·테스트 준비도")

    def _score_reflective_depth(self, text: str) -> Signal:
        """철학적·반성적 깊이가 드러나는 정도를 측정합니다."""
        score = self._keyword_score(text, self.reflective_keywords)
        return Signal(SignalType.REFLECTIVE_DEPTH, score, "본질·이유·철학·맥락 관련 표현")

    def _keyword_score(self, text: str, keywords: List[str]) -> float:
        """주어진 키워드 집합에 대한 휴리스틱 점수를 계산합니다."""
        lowered = text.lower()
        hits = sum(lowered.count(keyword.lower()) for keyword in keywords)
        length_bonus = min(len(text) / 700.0, 0.22)
        question_bonus = 0.08 if any(token in text for token in ["?", "무엇", "어떻게", "왜"]) else 0.0
        structure_bonus = 0.08 if any(token in text for token in ["다음", "설정", "영향", "탐구", "적용", "문제점"]) else 0.0
        keyword_component = min(hits / max(len(keywords) * 0.45, 1.0), 1.0)
        return round(min(keyword_component * 0.72 + length_bonus + question_bonus + structure_bonus, 1.0), 3)

    def _build_proposal_payload(
        self,
        turns: List[Dict[str, str]],
        text: str,
        signals: List[Signal],
        confidence: float,
    ) -> Dict[str, Any]:
        """감지 결과로부터 인지 상태 업데이트에 사용할 제안 페이로드를 생성합니다."""
        keywords = self._extract_core_keywords(turns)
        topic_phrase = self._build_topic_phrase(keywords)
        direction = self._normalize_generated_will(
            f"{topic_phrase}를 구조화하고 사용자와 함께 실행 가능한 질문과 지식으로 축적한다"
        )

        goals = [
            "형성된 의지를 스냅샷으로 저장한다",
            "분신 작업을 통해 서로 다른 관점을 병렬 검토한다",
            "결과를 위키 지식으로 누적하고 다음 질문으로 환류한다",
        ]
        if keywords:
            main_keyword = self._attach_particle(f"'{keywords[0]}'", keywords[0], "을", "를")
            goals.insert(0, f"{main_keyword} 중심으로 핵심 문제를 구조화한다")
        if len(keywords) >= 2:
            linked_keyword = self._attach_particle(f"'{keywords[0]}'", keywords[0], "과", "와")
            goals.insert(1, f"{linked_keyword} '{keywords[1]}'의 연결 맥락을 검토한다")

        knowledge = {
            "detector_summary": f"임계점 감지 신뢰도 {confidence:.2f}",
            "detector_keywords": ", ".join(keywords[:4]) if keywords else "핵심 맥락",
            "detector_signals": {
                signal.signal_type.value: signal.score for signal in signals
            },
            "conversation_excerpt": text[:220],
        }
        experience = [
            f"임계점 감지 신뢰도 {confidence:.2f}",
            f"정규화된 핵심 키워드: {', '.join(keywords[:4]) if keywords else '핵심 맥락'}",
            "대화가 방향성과 구체성을 동시에 형성하는 구간에 도달함",
        ]
        return {
            "will": direction,
            "goals": goals,
            "knowledge": knowledge,
            "experience": experience,
        }

    def _extract_core_keywords(self, turns: List[Dict[str, str]]) -> List[str]:
        """대화의 원천을 구분하여 중복을 제거한 핵심 키워드를 추출합니다."""
        weighted_keywords: Dict[str, float] = {}
        insertion_order: List[str] = []

        for turn in turns:
            content = str(turn.get("content", ""))
            role = str(turn.get("role", "user"))
            source = str(turn.get("source", "conversation"))
            for candidate in re.findall(r"[가-힣A-Za-z]{2,}", content):
                keyword = self._normalize_keyword(candidate)
                if not self._is_meaningful_keyword(keyword, source):
                    continue
                if keyword not in weighted_keywords:
                    weighted_keywords[keyword] = 0.0
                    insertion_order.append(keyword)
                weighted_keywords[keyword] += self._keyword_weight(keyword, role, source)

        ranked_keywords = sorted(
            weighted_keywords.items(),
            key=lambda item: (-item[1], insertion_order.index(item[0])),
        )
        return [keyword for keyword, _ in ranked_keywords[:8]]

    def _normalize_keyword(self, candidate: str) -> str:
        """키워드 끝의 조사와 서술형 어미를 제거해 정규화합니다.

        정규화 과정에서 원래 키워드가 너무 짧아지지 않도록
        최소 2글자를 유지합니다.
        """
        keyword = re.sub(r"[^가-힣A-Za-z]", "", candidate).strip()
        if not keyword:
            return ""

        if keyword.isascii():
            keyword = keyword.lower()

        normalized = keyword
        while True:
            updated = normalized
            for suffix in self._PREDICATE_SUFFIXES:
                if len(updated) <= len(suffix) + 1:
                    continue
                if updated.endswith(suffix):
                    updated = updated[: -len(suffix)]
                    break
            if updated == normalized:
                break
            normalized = updated

        while True:
            updated = normalized
            for particle in self._TRAILING_PARTICLES:
                if len(updated) <= len(particle) + 1:
                    continue
                if updated.endswith(particle):
                    updated = updated[: -len(particle)]
                    break
            if updated == normalized:
                break
            normalized = updated

        if len(normalized) < 2:
            return keyword

        return normalized

    def _is_meaningful_keyword(self, keyword: str, source: str) -> bool:
        """노이즈 키워드를 제거하고 의미 있는 항목만 남깁니다."""
        if len(keyword) < 2:
            return False
        if keyword in self._COMMON_STOPWORDS:
            return False
        if source in {"current_will", "reflective_mirror"} and keyword in self._BOILERPLATE_KEYWORDS:
            return False
        return True

    def _keyword_weight(self, keyword: str, role: str, source: str) -> float:
        """키워드의 출처에 따라 중요도를 다르게 부여합니다."""
        weight = 1.0
        if source == "recent_conversation":
            weight += 2.4
        elif source == "conversation":
            weight += 2.0
        elif source == "current_will":
            weight += 0.8
        elif source == "reflective_mirror":
            weight += 0.2

        if role == "user":
            weight += 0.5
        if len(keyword) >= 4:
            weight += 0.2
        return weight

    def _build_topic_phrase(self, keywords: List[str]) -> str:
        """정규화된 키워드 목록을 안정적인 한국어 의지 구문으로 조립합니다."""
        topic_keywords = keywords[:3]
        if not topic_keywords:
            return "현재 대화의 핵심 맥락에 대한 이해"
        if len(topic_keywords) == 1:
            return f"{topic_keywords[0]}에 대한 이해"
        return f"{', '.join(topic_keywords[:-1])}, {topic_keywords[-1]}에 대한 이해"

    def _attach_particle(
        self,
        display_text: str,
        keyword: str,
        consonant_particle: str,
        vowel_particle: str,
    ) -> str:
        """키워드 종성에 맞는 조사를 선택해 부착합니다."""
        cleaned = re.sub(r"[^가-힣A-Za-z0-9]", "", keyword)
        if not cleaned:
            return f"{display_text}{vowel_particle}"

        last_char = cleaned[-1]
        if "가" <= last_char <= "힣":
            has_final_consonant = (ord(last_char) - ord("가")) % 28 != 0
            particle = consonant_particle if has_final_consonant else vowel_particle
            return f"{display_text}{particle}"

        return f"{display_text}{vowel_particle}"

    def _normalize_generated_will(self, text: str) -> str:
        """생성된 의지 문장의 반복 조사와 공백 붕괴를 정규화합니다."""
        normalized = re.sub(r"\s+", " ", text).strip()
        pattern = re.compile(r"([가-힣A-Za-z]+?)(을|를|은|는|이|가|와|과)(?:\2)+")

        while True:
            updated = pattern.sub(r"\1\2", normalized)
            updated = re.sub(r"\s+,", ",", updated)
            updated = re.sub(r",\s*,+", ", ", updated)
            if updated == normalized:
                break
            normalized = updated

        return normalized


__all__ = [
    "Proposal",
    "Signal",
    "SignalType",
    "ThresholdDetector",
]
