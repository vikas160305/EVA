"""Autonomous Multi-Step Agent Task Planner for MARK-L.

Decomposes complex high-level goals into sequential executable action steps,
maintains plan state, and executes actions with step-by-step verification.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanStep:
    step_id: int
    description: str
    action_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[str] = None


class AgentTaskPlanner:
    """Decomposes goals and manages multi-step execution plans."""

    def __init__(self, goal: str) -> None:
        self.goal = goal
        self.steps: List[PlanStep] = []
        self._build_plan()

    def _build_plan(self) -> None:
        """Simple rule-based task planning heuristics."""
        lower = self.goal.lower()
        
        # Example pattern: Search news and save to file
        if "search" in lower and "save" in lower:
            self.steps.append(PlanStep(
                step_id=1,
                description=f"Perform web search for: {self.goal}",
                action_type="web_search",
                params={"query": self.goal}
            ))
            self.steps.append(PlanStep(
                step_id=2,
                description="Format search results into document",
                action_type="format_summary",
                params={}
            ))
            self.steps.append(PlanStep(
                step_id=3,
                description="Save summary to output file",
                action_type="save_file",
                params={"filename": "search_results.txt"}
            ))
        else:
            # Default single goal step
            self.steps.append(PlanStep(
                step_id=1,
                description=self.goal,
                action_type="general",
                params={"goal": self.goal}
            ))

    def execute_next_step(self) -> Optional[PlanStep]:
        for step in self.steps:
            if step.status == "pending":
                step.status = "running"
                return step
        return None

    def mark_completed(self, step_id: int, result: str) -> None:
        for step in self.steps:
            if step.step_id == step_id:
                step.status = "completed"
                step.result = result
                break

    def mark_failed(self, step_id: int, error: str) -> None:
        for step in self.steps:
            if step.step_id == step_id:
                step.status = "failed"
                step.result = error
                break

    def get_summary(self) -> str:
        lines = [f"Goal: {self.goal}"]
        for s in self.steps:
            icon = "✅" if s.status == "completed" else ("❌" if s.status == "failed" else "⏳")
            lines.append(f"{icon} Step {s.step_id}: {s.description} [{s.status}]")
        return "\n".join(lines)
