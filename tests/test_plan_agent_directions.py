"""
Tests for PlanAgent new_directions parsing, phase validation,
merge_research_plans, and JSON failure fallback.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.models.research_plan import (
    ResearchPlan,
    ResearchDirection,
    ResearchMode,
    DirectionStatus,
)
from src.models.state import merge_research_plans
from src.agents.plan_agent import PlanAgent, PHASE_AGENT_MAP


# ==================== Fixtures ====================

@pytest.fixture
def plan_agent():
    """Create a PlanAgent with mocked LLM call."""
    with patch("src.agents.base_agent.load_prompt", return_value="mock prompt"):
        agent = PlanAgent()
    return agent


@pytest.fixture
def base_plan():
    """Create a minimal ResearchPlan with one direction."""
    d1 = ResearchDirection(
        id="D1",
        topic="EGFR mutation analysis",
        target_agent="Geneticist",
        priority=1,
        queries=["EGFR L858R"],
        status=DirectionStatus.IN_PROGRESS,
        completion_criteria="Identify actionable mutations",
        entity_ids=[],
    )
    plan = ResearchPlan(
        id="plan_test",
        case_summary="NSCLC patient with EGFR L858R",
        key_entities={"genes": ["EGFR"], "variants": ["L858R"], "drugs": []},
        directions=[d1],
        initial_mode=ResearchMode.BREADTH_FIRST,
        created_at="2025-01-01T00:00:00",
    )
    return plan


@pytest.fixture
def direction_stats():
    """Minimal direction stats for _parse_evaluation_output."""
    return {
        "D1": {
            "topic": "EGFR mutation analysis",
            "target_agent": "Geneticist",
            "evidence_count": 5,
            "grade_distribution": {"A": 1, "B": 2, "C": 1, "D": 1, "E": 0},
            "weighted_score": 15.5,
            "completeness": 31.0,
            "status": "active",
            "low_quality_only": False,
            "has_high_quality": True,
            "priority": 1,
        }
    }


# ==================== PHASE_AGENT_MAP Tests ====================

class TestPhaseAgentMap:
    """Verify PHASE_AGENT_MAP is correctly defined."""

    def test_phase1_agents(self):
        assert "Pathologist" in PHASE_AGENT_MAP["phase1"]
        assert "Geneticist" in PHASE_AGENT_MAP["phase1"]
        assert "Pharmacist" in PHASE_AGENT_MAP["phase1"]
        assert "Oncologist" in PHASE_AGENT_MAP["phase1"]

    def test_phase2a_agents(self):
        assert "Oncologist" in PHASE_AGENT_MAP["phase2a"]
        assert "LocalTherapist" in PHASE_AGENT_MAP["phase2a"]
        assert "Recruiter" in PHASE_AGENT_MAP["phase2a"]
        assert "Nutritionist" in PHASE_AGENT_MAP["phase2a"]
        assert "IntegrativeMed" in PHASE_AGENT_MAP["phase2a"]

    def test_phase2b_agents(self):
        assert PHASE_AGENT_MAP["phase2b"] == {"Pharmacist"}

    def test_phase3_agents(self):
        assert PHASE_AGENT_MAP["phase3"] == {"Oncologist"}

    def test_cross_phase_exclusion(self):
        """Recruiter is not in phase1."""
        assert "Recruiter" not in PHASE_AGENT_MAP["phase1"]
        assert "Pathologist" not in PHASE_AGENT_MAP["phase2a"]


# ==================== New Direction Validation Tests ====================

class TestNewDirectionValidation:
    """Test _parse_evaluation_output with new_directions + phase validation."""

    def test_valid_new_direction_accepted(self, plan_agent, base_plan, direction_stats):
        """A new direction with valid target_agent for the phase should be added."""
        eval_output = json.dumps({
            "decision": "continue",
            "reasoning": "Need more evidence",
            "updated_directions": [
                {"id": "D1", "completeness": 50, "preferred_mode": "depth_first"}
            ],
            "new_directions": [
                {
                    "id": "D_NEW",
                    "topic": "Pharmacogenomics DPYD",
                    "target_agent": "Geneticist",
                    "priority": 2,
                    "queries": ["DPYD polymorphism"],
                    "status": "pending",
                    "completion_criteria": "Check DPYD status",
                    "entity_ids": [],
                }
            ],
            "gaps": [],
            "next_priorities": [],
        })

        result = plan_agent._parse_evaluation_output(
            output=eval_output,
            plan=base_plan,
            direction_stats=direction_stats,
            phase="phase1",
        )

        plan_dict = result["research_plan"]
        direction_ids = [d["id"] for d in plan_dict["directions"]]
        assert "D_NEW" in direction_ids, "Valid new direction should be added"

    def test_invalid_cross_phase_direction_rejected(self, plan_agent, base_plan, direction_stats):
        """A new direction targeting an agent not in the current phase should be rejected."""
        eval_output = json.dumps({
            "decision": "continue",
            "reasoning": "Need trial data",
            "updated_directions": [
                {"id": "D1", "completeness": 50, "preferred_mode": "breadth_first"}
            ],
            "new_directions": [
                {
                    "id": "D_BAD",
                    "topic": "Clinical trial matching",
                    "target_agent": "Recruiter",  # Recruiter not in phase1
                    "priority": 2,
                    "queries": ["EGFR trials"],
                    "status": "pending",
                    "completion_criteria": "Find trials",
                    "entity_ids": [],
                }
            ],
            "gaps": [],
            "next_priorities": [],
        })

        result = plan_agent._parse_evaluation_output(
            output=eval_output,
            plan=base_plan,
            direction_stats=direction_stats,
            phase="phase1",
        )

        plan_dict = result["research_plan"]
        direction_ids = [d["id"] for d in plan_dict["directions"]]
        assert "D_BAD" not in direction_ids, "Cross-phase direction should be rejected"

    def test_no_phase_allows_all_directions(self, plan_agent, base_plan, direction_stats):
        """When phase is empty, all directions should be accepted (backward compat)."""
        eval_output = json.dumps({
            "decision": "continue",
            "reasoning": "test",
            "updated_directions": [
                {"id": "D1", "completeness": 50, "preferred_mode": "breadth_first"}
            ],
            "new_directions": [
                {
                    "id": "D_ANY",
                    "topic": "Any agent direction",
                    "target_agent": "Recruiter",
                    "priority": 2,
                    "queries": [],
                    "status": "pending",
                    "completion_criteria": "test",
                    "entity_ids": [],
                }
            ],
            "gaps": [],
            "next_priorities": [],
        })

        result = plan_agent._parse_evaluation_output(
            output=eval_output,
            plan=base_plan,
            direction_stats=direction_stats,
            phase="",  # empty phase = no validation
        )

        plan_dict = result["research_plan"]
        direction_ids = [d["id"] for d in plan_dict["directions"]]
        assert "D_ANY" in direction_ids, "Empty phase should allow all agents"


# ==================== JSON Parse Failure Fallback Tests ====================

class TestJsonParseFallback:
    """Test graceful fallback when JSON parsing fails."""

    def test_invalid_json_returns_default(self, plan_agent, base_plan, direction_stats):
        """Non-JSON output should trigger default evaluation fallback."""
        result = plan_agent._parse_evaluation_output(
            output="This is not valid JSON at all, just plain text reasoning.",
            plan=base_plan,
            direction_stats=direction_stats,
            phase="phase1",
        )

        # Should return a valid result with default values
        assert "research_plan" in result
        assert "decision" in result

    def test_malformed_json_returns_default(self, plan_agent, base_plan, direction_stats):
        """Malformed JSON should trigger default evaluation fallback."""
        result = plan_agent._parse_evaluation_output(
            output='```json\n{"decision": "continue", "broken_json": }\n```',
            plan=base_plan,
            direction_stats=direction_stats,
            phase="phase1",
        )

        assert "research_plan" in result
        assert "decision" in result


# ==================== merge_research_plans Tests ====================

class TestMergeResearchPlans:
    """Test state reducer merge_research_plans."""

    def test_new_direction_preserved_in_merge(self):
        """New directions added by PlanAgent should be preserved after merge."""
        left = {
            "phase": "phase1",
            "directions": [
                {"id": "D1", "topic": "EGFR", "target_agent": "Geneticist"},
            ],
        }
        right = {
            "phase": "phase1",
            "directions": [
                {"id": "D1", "topic": "EGFR", "target_agent": "Geneticist"},
                {"id": "D_NEW", "topic": "DPYD", "target_agent": "Geneticist"},
            ],
        }

        merged = merge_research_plans(left, right)
        direction_ids = [d["id"] for d in merged["directions"]]
        assert "D_NEW" in direction_ids
        assert "D1" in direction_ids
        assert len(merged["directions"]) == 2

    def test_same_id_right_overwrites_left(self):
        """Right plan's direction should overwrite left's for same ID."""
        left = {
            "phase": "phase1",
            "directions": [
                {"id": "D1", "topic": "old topic", "target_agent": "Geneticist"},
            ],
        }
        right = {
            "phase": "phase1",
            "directions": [
                {"id": "D1", "topic": "updated topic", "target_agent": "Geneticist"},
            ],
        }

        merged = merge_research_plans(left, right)
        assert len(merged["directions"]) == 1
        assert merged["directions"][0]["topic"] == "updated topic"

    def test_phase_switch_replaces_directions(self):
        """Phase switch should completely replace directions."""
        left = {
            "phase": "phase1",
            "directions": [
                {"id": "D1_P1", "topic": "Phase1 dir", "target_agent": "Geneticist"},
            ],
        }
        right = {
            "phase": "phase2a",
            "directions": [
                {"id": "D1_P2A", "topic": "Phase2a dir", "target_agent": "Oncologist"},
            ],
        }

        merged = merge_research_plans(left, right)
        assert merged["phase"] == "phase2a"
        direction_ids = [d["id"] for d in merged["directions"]]
        assert "D1_P1" not in direction_ids, "Old phase directions should be removed"
        assert "D1_P2A" in direction_ids

    def test_empty_left_returns_right(self):
        """Empty left should return right as-is."""
        right = {"phase": "phase1", "directions": [{"id": "D1"}]}
        assert merge_research_plans({}, right) == right

    def test_empty_right_returns_left(self):
        """Empty right should return left as-is."""
        left = {"phase": "phase1", "directions": [{"id": "D1"}]}
        assert merge_research_plans(left, {}) == left
