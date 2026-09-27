"""Hindsight memory abstraction layer.

This is the core differentiator of the project. Provides a clean abstraction
around the Hindsight SDK for storing and retrieving team engineering knowledge.
"""

from __future__ import annotations
from typing import Optional
from config import settings
from core.models import (
    MemoryEntry,
    MemoryType,
    MemoryStats,
    PRInfo,
    FileDiff,
    ReviewFinding,
)


class HindsightMemoryManager:
    """Abstraction layer around Hindsight for persistent team memory."""

    def __init__(self):
        self._client = None
        self._bank_id = settings.HINDSIGHT_BANK_ID
        self._available = False

        if settings.has_hindsight:
            try:
                from hindsight_client import Hindsight

                self._client = Hindsight(
                    base_url=settings.HINDSIGHT_BASE_URL,
                    api_key=settings.HINDSIGHT_API_KEY,
                )
                self._available = True
                print(f"✅ Hindsight connected: {settings.HINDSIGHT_BASE_URL}")
                print(f"   Bank ID: {self._bank_id}")
            except Exception as e:
                print(f"⚠️  Hindsight initialization failed: {e}")
                self._available = False
        else:
            print("⚠️  HINDSIGHT_API_KEY not set. Memory features disabled.")

    @property
    def is_available(self) -> bool:
        return self._available

    def store_memory(self, entry: MemoryEntry) -> bool:
        """Store a structured memory entry in Hindsight.

        Converts the MemoryEntry to rich text and calls retain().
        Returns True on success, False on failure.
        """
        if not self._available:
            print("  ⚠️  Hindsight unavailable, skipping memory storage.")
            return False

        try:
            text = entry.to_hindsight_text()
            self._client.retain(
                bank_id=self._bank_id,
                content=text,
            )
            print(f"  💾 Stored [{entry.type.value}]: {entry.content[:80]}...")
            return True
        except Exception as e:
            print(f"  ❌ Failed to store memory: {e}")
            return False

    def search_memory(self, query: str) -> list[str]:
        """Search Hindsight for relevant memories.

        Uses recall() for multi-strategy retrieval (semantic, keyword, graph, temporal).
        RecallResponse.results is list[RecallResult], each with .text, .type, .context.
        """
        if not self._available:
            return []

        try:
            response = self._client.recall(
                bank_id=self._bank_id,
                query=query,
            )

            results = []
            if response.results:
                for mem in response.results:
                    if mem.text:
                        results.append(str(mem.text))
            return results
        except Exception as e:
            print(f"  ⚠️  Memory search failed: {e}")
            return []

    def reflect_memory(self, query: str) -> str:
        """Get a synthesized reflection from Hindsight.

        Uses reflect() to generate a reasoned summary from stored memories.
        ReflectResponse has .text field with the synthesized response.
        """
        if not self._available:
            return ""

        try:
            response = self._client.reflect(
                bank_id=self._bank_id,
                query=query,
            )
            return str(response.text) if response.text else ""
        except Exception as e:
            print(f"  ⚠️  Memory reflection failed: {e}")
            return ""

    def build_memory_context(
        self, pr_info: PRInfo, files: list[FileDiff]
    ) -> tuple[str, MemoryStats]:
        """Build comprehensive memory context for the LLM.

        Runs multiple targeted queries against Hindsight based on
        the PR content and aggregates relevant team knowledge.

        Returns (formatted_context_string, memory_statistics).
        """
        if not self._available:
            return "", MemoryStats()

        all_memories: list[str] = []
        stats = MemoryStats()

        # Analyze the PR to build smart queries
        queries = self._build_smart_queries(pr_info, files)

        print(f"  🔍 Running {len(queries)} targeted memory queries...")

        # Map query labels to stat counters
        label_to_stat = {
            "team conventions": "team_conventions_matched",
            "review patterns": "review_feedback_used",
            "API conventions": "team_conventions_matched",
            "database patterns": "team_conventions_matched",
            "async conventions": "team_conventions_matched",
            "error handling": "team_conventions_matched",
            "validation patterns": "team_conventions_matched",
            "security practices": "architectural_decisions_applied",
            "dependency management": "architectural_decisions_applied",
        }

        for label, query in queries:
            results = self.search_memory(query)
            if results:
                print(f"     ✓ '{label}': {len(results)} memories found")
                stat_attr = label_to_stat.get(label, "review_feedback_used")
                # Limit to top 1 per query to avoid token bloat
                for mem_text in results[:1]:
                    if mem_text not in all_memories:
                        all_memories.append(mem_text)
                        setattr(stats, stat_attr, getattr(stats, stat_attr) + 1)

        stats.total_memories_retrieved = len(all_memories)

        if not all_memories:
            return "", stats

        # Also get a synthesized reflection
        reflection = self.reflect_memory(
            f"What are the key team coding conventions and review patterns "
            f"relevant to a PR that modifies: "
            f"{', '.join(f.filename for f in files[:5])}?"
        )

        # Format the context
        context_parts = [
            "== TEAM MEMORY CONTEXT ==",
            f"Retrieved {len(all_memories)} relevant memories from previous reviews.\n",
        ]

        # Group by type
        conventions = [m for m in all_memories if "[TEAM_CONVENTION]" in m]
        arch_decisions = [
            m for m in all_memories if "[ARCHITECTURAL_DECISION]" in m
        ]
        recurring = [m for m in all_memories if "[RECURRING_ISSUE]" in m]
        feedback = [m for m in all_memories if "[REVIEW_FEEDBACK]" in m]
        other = [
            m
            for m in all_memories
            if not any(
                tag in m
                for tag in [
                    "[TEAM_CONVENTION]",
                    "[ARCHITECTURAL_DECISION]",
                    "[RECURRING_ISSUE]",
                    "[REVIEW_FEEDBACK]",
                ]
            )
        ]

        if conventions:
            context_parts.append("--- Team Conventions ---")
            for c in conventions:
                context_parts.append(f"• {c}")
            context_parts.append("")

        if arch_decisions:
            context_parts.append("--- Architectural Decisions ---")
            for a in arch_decisions:
                context_parts.append(f"• {a}")
            context_parts.append("")

        if recurring:
            context_parts.append("--- Recurring Issues ---")
            for r in recurring:
                context_parts.append(f"• {r}")
            context_parts.append("")

        if feedback:
            context_parts.append("--- Previous Review Feedback ---")
            for f in feedback:
                context_parts.append(f"• {f}")
            context_parts.append("")

        if other:
            context_parts.append("--- Other Relevant Memories ---")
            for o in other:
                context_parts.append(f"• {o}")
            context_parts.append("")

        if reflection:
            context_parts.append("--- Synthesized Team Insights ---")
            context_parts.append(reflection)

        return "\n".join(context_parts), stats

    def store_review_learnings(
        self, findings: list[ReviewFinding], pr_info: PRInfo
    ) -> int:
        """Extract and store learnings from a completed review.

        Converts significant review findings into memory entries
        and stores them in Hindsight.
        Returns count of memories stored.
        """
        if not self._available:
            return 0

        stored = 0
        significant = [
            f
            for f in findings
            if f.severity.value in ("critical", "high", "medium")
            and f.source != "static_analysis"
        ]

        for finding in significant[:5]:
            entry = MemoryEntry(
                type=self._classify_finding(finding),
                content=f"{finding.issue}. {finding.explanation}",
                source_pr=f"PR #{pr_info.number} ({pr_info.owner}/{pr_info.repo})",
                context=f"File: {finding.file}. {finding.suggestion}"
                if finding.suggestion
                else f"File: {finding.file}",
            )
            if self.store_memory(entry):
                stored += 1

        return stored

    def _build_smart_queries(
        self, pr_info: PRInfo, files: list[FileDiff]
    ) -> list[tuple[str, str]]:
        """Build targeted queries based on the PR content."""
        queries = [
            ("team conventions", "team coding conventions and standards"),
            ("review patterns", "common code review patterns and recurring feedback"),
        ]

        filenames = [f.filename.lower() for f in files]
        all_patches = " ".join(f.patch.lower() for f in files if f.patch)

        # API/route patterns
        if any(
            kw in fn
            for fn in filenames
            for kw in ("route", "api", "endpoint", "view", "handler")
        ):
            queries.append(
                (
                    "API conventions",
                    "API endpoint conventions error handling route handlers",
                )
            )

        # Database patterns
        if any(
            kw in all_patches
            for kw in (
                "sqlite",
                "psycopg",
                "sqlalchemy",
                "database",
                "cursor",
                "execute",
                "sql",
                "query",
                "db",
                "connect",
            )
        ):
            queries.append(
                (
                    "database patterns",
                    "database access patterns repository layer SQL queries ORM",
                )
            )

        # Async patterns
        if any(
            kw in all_patches
            for kw in ("requests.post", "requests.get", "urllib", "http")
        ):
            queries.append(
                (
                    "async conventions",
                    "async await external API calls network I/O synchronous",
                )
            )

        # Error handling
        if any(
            kw in all_patches
            for kw in ("exception", "error", "raise", "httpexception", "try")
        ):
            queries.append(
                (
                    "error handling",
                    "error handling conventions error wrapper AppError",
                )
            )

        # Validation
        if any(
            kw in all_patches
            for kw in ("validate", "validation", "pydantic", "schema")
        ):
            queries.append(
                (
                    "validation patterns",
                    "input validation Pydantic schemas request validation",
                )
            )

        # Security
        if any(
            kw in all_patches
            for kw in ("password", "secret", "token", "auth", "credential")
        ):
            queries.append(
                (
                    "security practices",
                    "security practices hardcoded credentials secrets management",
                )
            )

        # Dependencies
        if any(kw in all_patches for kw in ("import ", "from ", "require")):
            queries.append(
                (
                    "dependency management",
                    "internal utilities third-party dependencies existing modules",
                )
            )

        return queries

    def _update_stats(self, stats: MemoryStats, memory_text: str) -> None:
        """Update memory statistics based on memory content type."""
        upper_text = memory_text.upper()
        if "[TEAM_CONVENTION]" in upper_text:
            stats.team_conventions_matched += 1
        elif "[ARCHITECTURAL_DECISION]" in upper_text:
            stats.architectural_decisions_applied += 1
        elif "[RECURRING_ISSUE]" in upper_text:
            stats.recurring_issues_detected += 1
        elif "[REVIEW_FEEDBACK]" in upper_text:
            stats.review_feedback_used += 1

    def _classify_finding(self, finding: ReviewFinding) -> MemoryType:
        """Classify a review finding into a memory type."""
        issue_lower = (finding.issue + " " + finding.explanation).lower()

        if any(
            kw in issue_lower
            for kw in ("convention", "standard", "practice", "pattern", "always")
        ):
            return MemoryType.TEAM_CONVENTION
        if any(
            kw in issue_lower
            for kw in ("architecture", "layer", "structure", "design")
        ):
            return MemoryType.ARCHITECTURAL_DECISION
        if any(
            kw in issue_lower
            for kw in ("recurring", "again", "repeated", "common")
        ):
            return MemoryType.RECURRING_ISSUE

        return MemoryType.REVIEW_FEEDBACK
