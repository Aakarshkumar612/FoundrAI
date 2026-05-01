"""Tests for Layer 4 agent orchestration.

Covers:
- Each agent in isolation with mocked Groq responses
- Valid JSON schema output from each agent
- Fallback output when Groq call fails
- Full orchestrator pipeline SSE event sequence
- SSE events contain correct agent names and structure
"""

import json
from typing import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest

from backend.agents import market_agent, risk_agent, revenue_agent, strategy_agent
from backend.agents.orchestrator import run_pipeline

# ── Groq mock helpers ─────────────────────────────────────────────────────────

def _mock_groq_response(content: str) -> MagicMock:
    """Build a mock Groq completion response with the given JSON content."""
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _mock_groq_client(content: str) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_groq_response(content)
    return client


# ── Market agent tests ────────────────────────────────────────────────────────

class TestMarketAgent:
    VALID_OUTPUT = json.dumps({
        "market_size_assessment": "TAM is $50B with 15% YoY growth.",
        "competitor_threats": ["CompetitorA", "CompetitorB"],
        "opportunity_areas": ["SMB segment", "Vertical SaaS"],
        "confidence": 0.85,
    })

    def test_returns_valid_output(self) -> None:
        client = _mock_groq_client(self.VALID_OUTPUT)
        result = market_agent.run("What is my market?", "Revenue grew 12%.", client)
        assert result.market_size_assessment
        assert len(result.competitor_threats) > 0
        assert 0.0 <= result.confidence <= 1.0

    def test_confidence_within_bounds(self) -> None:
        client = _mock_groq_client(self.VALID_OUTPUT)
        result = market_agent.run("question", "context", client)
        assert 0.0 <= result.confidence <= 1.0

    def test_fallback_on_groq_failure(self) -> None:
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("API timeout")
        result = market_agent.run("question", "context", client)
        assert result.confidence == 0.0
        assert result.market_size_assessment  # fallback is non-empty

    def test_fallback_on_invalid_json(self) -> None:
        client = _mock_groq_client("not valid json at all")
        result = market_agent.run("question", "context", client)
        assert result.confidence == 0.0


# ── Risk agent tests ──────────────────────────────────────────────────────────

class TestRiskAgent:
    VALID_OUTPUT = json.dumps({
        "risk_score": 6.5,
        "primary_risks": [{"risk": "CAC rising", "severity": "high"}],
        "runway_assessment": "14 months at current burn.",
        "mitigation_recommendations": ["Cut CAC", "Improve NRR"],
    })

    def test_returns_valid_output(self) -> None:
        client = _mock_groq_client(self.VALID_OUTPUT)
        result = risk_agent.run("What is my risk?", "context", {}, client)
        assert 0.0 <= result.risk_score <= 10.0
        assert result.runway_assessment
        assert len(result.primary_risks) > 0

    def test_risk_score_within_bounds(self) -> None:
        client = _mock_groq_client(self.VALID_OUTPUT)
        result = risk_agent.run("q", "c", {}, client)
        assert 0.0 <= result.risk_score <= 10.0

    def test_severity_valid_values(self) -> None:
        client = _mock_groq_client(self.VALID_OUTPUT)
        result = risk_agent.run("q", "c", {}, client)
        for risk in result.primary_risks:
            assert risk.severity in ("high", "medium", "low")

    def test_fallback_on_groq_failure(self) -> None:
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("rate limit")
        result = risk_agent.run("q", "c", {}, client)
        assert result.risk_score == 5.0  # fallback default


# ── Revenue agent tests ───────────────────────────────────────────────────────

class TestRevenueAgent:
    VALID_OUTPUT = json.dumps({
        "forecast_narrative": "Revenue will reach $2M ARR in 12 months.",
        "key_drivers": ["Enterprise upsell", "New logos"],
        "growth_levers": ["Pricing optimization"],
        "forecast_confidence": "medium",
    })

    def test_returns_valid_output(self) -> None:
        client = _mock_groq_client(self.VALID_OUTPUT)
        result = revenue_agent.run("What is my forecast?", "context", {}, client)
        assert result.forecast_narrative
        assert result.forecast_confidence in ("high", "medium", "low")

    def test_strips_think_tags(self) -> None:
        content_with_think = (
            "<think>Let me reason through this...</think>\n" + self.VALID_OUTPUT
        )
        client = _mock_groq_client(content_with_think)
        result = revenue_agent.run("q", "c", {}, client)
        assert result.forecast_narrative  # parsed correctly despite <think> tags

    def test_fallback_on_groq_failure(self) -> None:
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("model unavailable")
        result = revenue_agent.run("q", "c", {}, client)
        assert result.forecast_confidence == "low"


# ── Strategy agent tests ──────────────────────────────────────────────────────

class TestStrategyAgent:
    VALID_OUTPUT = json.dumps({
        "executive_summary": "Focus on retention before scaling acquisition.",
        "top_3_recommendations": ["Cut CAC", "Improve onboarding", "Launch upsell"],
        "immediate_actions": ["Audit churn", "NPS survey"],
        "30_60_90_day_plan": {
            "30_days": ["Hire CS lead"],
            "60_days": ["Launch PLG tier"],
            "90_days": ["Raise Series A"],
        },
    })

    def test_returns_valid_output(self) -> None:
        client = _mock_groq_client(self.VALID_OUTPUT)
        result = strategy_agent.run("What should I do?", {}, {}, {}, client)
        assert result.executive_summary
        assert len(result.top_3_recommendations) == 3

    def test_plan_has_all_phases(self) -> None:
        client = _mock_groq_client(self.VALID_OUTPUT)
        result = strategy_agent.run("q", {}, {}, {}, client)
        assert result.plan_30_60_90.days_30
        assert result.plan_30_60_90.days_60
        assert result.plan_30_60_90.days_90

    def test_fallback_on_groq_failure(self) -> None:
        client = MagicMock()
        client.chat.completions.create.side_effect = Exception("timeout")
        result = strategy_agent.run("q", {}, {}, {}, client)
        assert len(result.top_3_recommendations) == 3


# ── Orchestrator pipeline tests ───────────────────────────────────────────────

class TestOrchestrator:
    """Test the full pipeline SSE event sequence with all Groq calls mocked."""

    MARKET_JSON = json.dumps({
        "market_size_assessment": "TAM $50B.",
        "competitor_threats": ["A"],
        "opportunity_areas": ["B"],
        "confidence": 0.8,
    })
    RISK_JSON = json.dumps({
        "risk_score": 5.0,
        "primary_risks": [{"risk": "CAC rising", "severity": "medium"}],
        "runway_assessment": "12 months.",
        "mitigation_recommendations": ["Cut spend"],
    })
    REVENUE_JSON = json.dumps({
        "forecast_narrative": "ARR will reach $2M.",
        "key_drivers": ["Upsell"],
        "growth_levers": ["Pricing"],
        "forecast_confidence": "medium",
    })
    STRATEGY_JSON = json.dumps({
        "executive_summary": "Focus on retention.",
        "top_3_recommendations": ["R1", "R2", "R3"],
        "immediate_actions": ["A1"],
        "30_60_90_day_plan": {
            "30_days": ["T1"], "60_days": ["T2"], "90_days": ["T3"]
        },
    })

    def _mock_groq_sequence(self) -> MagicMock:
        """Return a Groq client that cycles through agent responses in order."""
        responses = [
            _mock_groq_response(self.MARKET_JSON),
            _mock_groq_response(self.RISK_JSON),
            _mock_groq_response(self.REVENUE_JSON),
            _mock_groq_response(self.STRATEGY_JSON),
        ]
        client = MagicMock()
        client.chat.completions.create.side_effect = responses
        return client

    @pytest.mark.asyncio
    async def test_pipeline_emits_rag_context_first(self) -> None:
        with patch("backend.agents.orchestrator.Groq", return_value=self._mock_groq_sequence()), \
             patch("backend.agents.orchestrator.get_settings", return_value=MagicMock(groq_api_key="test")):
            events = []
            async for chunk in run_pipeline("What is my runway?", []):
                events.append(chunk)

        assert events[0].startswith("event: rag_context")

    @pytest.mark.asyncio
    async def test_pipeline_emits_four_agent_updates(self) -> None:
        with patch("backend.agents.orchestrator.Groq", return_value=self._mock_groq_sequence()), \
             patch("backend.agents.orchestrator.get_settings", return_value=MagicMock(groq_api_key="test")):
            events = []
            async for chunk in run_pipeline("What is my risk?", []):
                events.append(chunk)

        agent_events = [e for e in events if "event: agent_update" in e]
        assert len(agent_events) == 4

    @pytest.mark.asyncio
    async def test_pipeline_contains_all_agent_names(self) -> None:
        with patch("backend.agents.orchestrator.Groq", return_value=self._mock_groq_sequence()), \
             patch("backend.agents.orchestrator.get_settings", return_value=MagicMock(groq_api_key="test")):
            raw = ""
            async for chunk in run_pipeline("question", []):
                raw += chunk

        for name in ["MarketAgent", "RiskAgent", "RevenueAgent", "StrategyAgent"]:
            assert name in raw

    @pytest.mark.asyncio
    async def test_pipeline_ends_with_final_event(self) -> None:
        with patch("backend.agents.orchestrator.Groq", return_value=self._mock_groq_sequence()), \
             patch("backend.agents.orchestrator.get_settings", return_value=MagicMock(groq_api_key="test")):
            events = []
            async for chunk in run_pipeline("question", []):
                events.append(chunk)

        assert "event: final" in events[-1]
        assert "complete" in events[-1]

    @pytest.mark.asyncio
    async def test_pipeline_continues_if_one_agent_fails(self) -> None:
        """Pipeline must not crash when one agent raises — partial results expected."""
        client = MagicMock()
        client.chat.completions.create.side_effect = [
            Exception("MarketAgent down"),  # market fails
            _mock_groq_response(self.RISK_JSON),
            _mock_groq_response(self.REVENUE_JSON),
            _mock_groq_response(self.STRATEGY_JSON),
        ]
        with patch("backend.agents.orchestrator.Groq", return_value=client), \
             patch("backend.agents.orchestrator.get_settings", return_value=MagicMock(groq_api_key="test")):
            events = []
            async for chunk in run_pipeline("question", []):
                events.append(chunk)

        # Should still get 4 agent_update events (market has fallback) + final
        agent_events = [e for e in events if "event: agent_update" in e]
        assert len(agent_events) == 4
        final_events = [e for e in events if "event: final" in e]
        assert len(final_events) == 1
