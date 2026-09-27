"""Pydantic data models for the code review agent."""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingSource(str, Enum):
    STATIC_ANALYSIS = "static_analysis"
    GENERAL_REASONING = "general_reasoning"
    TEAM_CONVENTION = "team_convention"
    HISTORICAL_MEMORY = "historical_memory"


class MemoryType(str, Enum):
    TEAM_CONVENTION = "team_convention"
    ARCHITECTURAL_DECISION = "architectural_decision"
    RECURRING_ISSUE = "recurring_issue"
    REVIEW_FEEDBACK = "review_feedback"


class PRInfo(BaseModel):
    """Pull request metadata."""
    url: str
    owner: str
    repo: str
    number: int
    title: str = ""
    author: str = ""
    description: str = ""
    base_branch: str = "main"
    head_branch: str = ""


class FileDiff(BaseModel):
    """A single file's diff from a PR."""
    filename: str
    status: str = "modified"
    patch: str = ""
    additions: int = 0
    deletions: int = 0
    content: Optional[str] = None


class ReviewFinding(BaseModel):
    """A single finding from the code review."""
    severity: Severity
    file: str
    line: Optional[str] = None
    issue: str
    explanation: str
    suggestion: str = ""
    source: FindingSource
    memory_reference: Optional[str] = None


class MemoryEntry(BaseModel):
    """Structured memory entry to store in Hindsight."""
    type: MemoryType
    content: str
    source_pr: str = ""
    context: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_hindsight_text(self) -> str:
        """Format as rich text for Hindsight retention."""
        lines = [
            f"[{self.type.value.upper()}] Source: {self.source_pr}",
            f"Content: {self.content}",
        ]
        if self.context:
            lines.append(f"Context: {self.context}")
        lines.append(f"Date: {self.timestamp}")
        return "\n".join(lines)


class MemoryStats(BaseModel):
    """Statistics about memory usage in a review."""
    total_memories_retrieved: int = 0
    team_conventions_matched: int = 0
    recurring_issues_detected: int = 0
    architectural_decisions_applied: int = 0
    review_feedback_used: int = 0


class ReviewResult(BaseModel):
    """Complete review output."""
    pr_info: PRInfo
    summary: str
    findings: list[ReviewFinding] = []
    memory_insights: list[ReviewFinding] = []
    ruff_findings: list[ReviewFinding] = []
    memory_stats: MemoryStats = Field(default_factory=MemoryStats)
    memory_context_used: str = ""
    review_mode: str = "with_memory"
    stored_learnings: list[MemoryEntry] = []
    bank_total_after: int = -1
