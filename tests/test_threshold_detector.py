"""threshold_detector.py의 핵심 공개 동작과 제안 페이로드를 검증합니다."""

from __future__ import annotations

from src.core.config import Config
from src.core.threshold_detector import ThresholdDetector


SHORT_INPUT = "안녕하세요. 지금은 아직 방향이 없습니다."
LONG_INPUT = """
현재 의지: 사용자와 함께 지식을 구조화하고 위키 환류를 통해 지속적으로 진화하는 시스템을 설계한다.
최근 대화: 사용자는 이 구조의 방향과 목표를 더 구체적으로 정리해 달라고 요청했다.
우리는 단계별 로드맵과 모듈 구조, 테스트 전략, 저장 방식, 버전 관리, 실행 계획을 함께 검토했다.
특히 사용자 승인과 제안 중심의 상호작용을 유지하면서도 실제로 구현하고 실행 가능한 형태로 만들고자 한다.
왜 이런 구조가 중요한지, 어떤 질문을 다음 단계에서 탐구해야 하는지, 그리고 환류와 축적이 어떤 의미를 가지는지까지 논의했다.
이제 이 의지를 바탕으로 구체적인 목표를 설정하고, 지식을 축적하며, 반복적으로 검토하고, 다음 질문을 만들 수 있는 준비가 되어 있다.
""".strip()


class TestThresholdDetector:
    """ThresholdDetector의 감지와 페이로드 생성을 검증합니다."""

    def test_short_input_does_not_reach_threshold(self) -> None:
        detector = ThresholdDetector(Config())

        proposal = detector.detect_threshold(SHORT_INPUT)

        assert proposal.should_propose is False
        assert detector.detect(SHORT_INPUT) is False
        assert proposal.confidence < detector.threshold

    def test_long_input_reaches_threshold(self) -> None:
        detector = ThresholdDetector(Config())

        proposal = detector.detect_threshold(LONG_INPUT)

        assert proposal.should_propose is True
        assert detector.detect(LONG_INPUT) is True
        assert proposal.confidence >= detector.threshold
        assert proposal.suggested_will
        assert proposal.suggested_goals

    def test_cognitive_state_proposal_contains_required_fields(self) -> None:
        detector = ThresholdDetector(Config())

        payload = detector.get_cognitive_state_proposal(LONG_INPUT)

        assert {"will", "goals", "knowledge", "experience", "confidence", "reasoning", "should_propose"} <= payload.keys()
        assert isinstance(payload["will"], str) and payload["will"]
        assert isinstance(payload["goals"], list) and payload["goals"]
        assert isinstance(payload["knowledge"], dict)
        assert isinstance(payload["experience"], list) and payload["experience"]
        assert isinstance(payload["knowledge"].get("detector_signals"), dict)
        assert "detector_keywords" in payload["knowledge"]
        assert payload["should_propose"] is True

    def test_keyword_extraction_and_normalization(self) -> None:
        detector = ThresholdDetector(Config())
        turns = [
            {
                "role": "user",
                "content": "위키를 구축합니다. 테스트를 반복하고 TEST를 정리합니다.",
                "source": "conversation",
            },
            {
                "role": "assistant",
                "content": "구축과 테스트의 연결 구조를 설명합니다.",
                "source": "recent_conversation",
            },
        ]

        keywords = detector._extract_core_keywords(turns)

        normalized_keywords = [detector._normalize_keyword(keyword) for keyword in keywords]

        assert detector._normalize_keyword("구축합니다") == "구축"
        assert detector._normalize_keyword("테스트를") == "테스트"
        assert detector._normalize_keyword("TEST") == "test"
        assert "구축" in normalized_keywords
        assert "테스트" in normalized_keywords
        assert "test" in normalized_keywords

    def test_constructor_uses_config_threshold(self) -> None:
        config = Config(THRESHOLD_SCORE=1.01)
        detector = ThresholdDetector(config)

        proposal = detector.detect_threshold(LONG_INPUT)

        assert detector.threshold == 1.01
        assert proposal.confidence < detector.threshold
        assert proposal.should_propose is False
