"""Review orchestrator — main pipeline that ties all components together."""

from core.models import (
    PRInfo,
    FileDiff,
    ReviewFinding,
    ReviewResult,
    MemoryStats,
    FindingSource,
)
from github_client.client import GitHubClient
from analyzer.static_analysis import run_ruff_on_files
from memory.hindsight_manager import HindsightMemoryManager
from llm.reviewer import LLMReviewer


class ReviewOrchestrator:
    """Orchestrates the full code review pipeline."""

    def __init__(self):
        self.github = GitHubClient()
        self.memory = HindsightMemoryManager()
        self.llm = LLMReviewer()

    def review_pr(
        self,
        pr_url: str,
        use_memory: bool = True,
        post_to_github: bool = False,
    ) -> ReviewResult:
        """Execute the full review pipeline.

        Steps:
        1. Fetch PR data from GitHub
        2. Run Ruff static analysis on Python files
        3. Query Hindsight for relevant team knowledge
        4. Generate LLM review with all context
        5. Store new learnings in Hindsight
        6. Optionally post review to GitHub
        """
        print(f"\n{'='*60}")
        print(f"📋 Starting review for: {pr_url}")
        print(f"   Memory mode: {'ENABLED' if use_memory else 'DISABLED'}")
        print(f"{'='*60}\n")

        # Step 1: Fetch PR data
        print("🔍 Step 1: Fetching PR data from GitHub...")
        pr_info, files = self.github.fetch_pr(pr_url)
        print(f"   Found {len(files)} changed files in '{pr_info.title}'")

        # Step 2: Static analysis
        print("\n🔧 Step 2: Running Ruff static analysis...")
        ruff_findings = run_ruff_on_files(files)
        print(f"   Found {len(ruff_findings)} static analysis issues")

        # Step 3: Query memory
        memory_context = None
        memory_stats = MemoryStats()
        if use_memory:
            print("\n🧠 Step 3: Querying Hindsight memory...")
            memory_context, memory_stats = self.memory.build_memory_context(
                pr_info, files
            )
            if memory_context:
                print(f"   Retrieved {memory_stats.total_memories_retrieved} relevant memories")
                print(f"   - {memory_stats.team_conventions_matched} team conventions")
                print(f"   - {memory_stats.recurring_issues_detected} recurring issues")
                print(f"   - {memory_stats.architectural_decisions_applied} architectural decisions")
            else:
                print("   No relevant memories found.")
        else:
            print("\n⏭️  Step 3: Skipping memory (disabled)")

        # Step 4: LLM review
        print("\n🤖 Step 4: Generating LLM review...")
        summary, llm_findings = self.llm.review(
            pr_info, files, ruff_findings, memory_context
        )
        print(f"   Generated {len(llm_findings)} review findings")

        # Separate memory-sourced findings
        memory_insights = [
            f
            for f in llm_findings
            if f.source in (FindingSource.TEAM_CONVENTION, FindingSource.HISTORICAL_MEMORY)
        ]
        general_findings = [
            f
            for f in llm_findings
            if f.source
            not in (FindingSource.TEAM_CONVENTION, FindingSource.HISTORICAL_MEMORY)
        ]

        print(f"   - {len(memory_insights)} findings from team memory")
        print(f"   - {len(general_findings)} general findings")

        # Step 5: Store new learnings
        if use_memory:
            print("\n📝 Step 5: Extracting and storing new learnings...")
            all_findings = ruff_findings + llm_findings
            stored = self.memory.store_review_learnings(all_findings, pr_info)
            print(f"   Stored {stored} new learnings in Hindsight")
        else:
            print("\n⏭️  Step 5: Skipping learning storage (memory disabled)")

        # Build result
        result = ReviewResult(
            pr_info=pr_info,
            summary=summary,
            findings=general_findings,
            memory_insights=memory_insights,
            ruff_findings=ruff_findings,
            memory_stats=memory_stats,
            memory_context_used=memory_context or "",
            review_mode="with_memory" if use_memory else "without_memory",
        )

        # Step 6: Optionally post to GitHub
        if post_to_github:
            print("\n📤 Step 6: Posting review to GitHub...")
            comment = self._format_github_comment(result)
            success = self.github.post_review_comment(pr_url, comment)
            print(f"   {'Posted successfully!' if success else 'Failed to post.'}")

        print(f"\n{'='*60}")
        print("✅ Review complete!")
        print(f"{'='*60}\n")

        return result

    def review_synthetic(
        self,
        pr_info: PRInfo,
        files: list[FileDiff],
        use_memory: bool = True,
    ) -> ReviewResult:
        """Review a synthetic/mock PR (no GitHub API needed).

        Used for demos when GitHub token is unavailable.
        """
        print(f"\n{'='*60}")
        print(f"📋 Starting synthetic review: {pr_info.title}")
        print(f"   Memory mode: {'ENABLED' if use_memory else 'DISABLED'}")
        print(f"{'='*60}\n")

        # Static analysis
        print("🔧 Running Ruff static analysis...")
        ruff_findings = run_ruff_on_files(files)
        print(f"   Found {len(ruff_findings)} static analysis issues")

        # Memory
        memory_context = None
        memory_stats = MemoryStats()
        if use_memory:
            print("\n🧠 Querying Hindsight memory...")
            memory_context, memory_stats = self.memory.build_memory_context(
                pr_info, files
            )
            if memory_context:
                print(f"   Retrieved {memory_stats.total_memories_retrieved} memories")
            else:
                print("   No relevant memories found.")

        # LLM review
        print("\n🤖 Generating LLM review...")
        summary, llm_findings = self.llm.review(
            pr_info, files, ruff_findings, memory_context
        )

        memory_insights = [
            f
            for f in llm_findings
            if f.source in (FindingSource.TEAM_CONVENTION, FindingSource.HISTORICAL_MEMORY)
        ]
        general_findings = [
            f
            for f in llm_findings
            if f.source
            not in (FindingSource.TEAM_CONVENTION, FindingSource.HISTORICAL_MEMORY)
        ]

        # Store learnings
        stored = 0
        if use_memory:
            print("\n📝 Storing new learnings...")
            stored = self.memory.store_review_learnings(
                ruff_findings + llm_findings, pr_info
            )
            print(f"   Stored {stored} new learnings")

        result = ReviewResult(
            pr_info=pr_info,
            summary=summary,
            findings=general_findings,
            memory_insights=memory_insights,
            ruff_findings=ruff_findings,
            memory_stats=memory_stats,
            memory_context_used=memory_context or "",
            review_mode="with_memory" if use_memory else "without_memory",
        )

        print("\n✅ Synthetic review complete!")
        return result

    def _format_github_comment(self, result: ReviewResult) -> str:
        """Format the review result as a GitHub comment."""
        lines = [
            "## 🤖 AI Code Review",
            "",
            f"**{result.summary}**",
            "",
        ]

        if result.memory_stats.total_memories_retrieved > 0:
            lines.append("### 🧠 Memory Used")
            lines.append(f"- {result.memory_stats.total_memories_retrieved} relevant memories retrieved")
            lines.append(f"- {result.memory_stats.team_conventions_matched} team conventions matched")
            lines.append(f"- {result.memory_stats.recurring_issues_detected} recurring issues detected")
            lines.append("")

        if result.memory_insights:
            lines.append("### 📌 Team-Specific Findings")
            for f in result.memory_insights:
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(
                    f.severity.value, "⚪"
                )
                lines.append(f"- {emoji} **[{f.severity.value.upper()}]** `{f.file}` — {f.issue}")
                lines.append(f"  > {f.explanation}")
                if f.memory_reference:
                    lines.append(f"  > 🧠 *{f.memory_reference}*")
                lines.append("")

        if result.findings:
            lines.append("### 📋 General Findings")
            for f in result.findings:
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(
                    f.severity.value, "⚪"
                )
                lines.append(f"- {emoji} **[{f.severity.value.upper()}]** `{f.file}` — {f.issue}")
                if f.suggestion:
                    lines.append(f"  > 💡 {f.suggestion}")
                lines.append("")

        if result.ruff_findings:
            lines.append(f"### 🔧 Static Analysis ({len(result.ruff_findings)} issues)")
            for f in result.ruff_findings[:5]:
                lines.append(f"- `{f.file}:{f.line}` — {f.issue}")
            if len(result.ruff_findings) > 5:
                lines.append(f"- ... and {len(result.ruff_findings) - 5} more")
            lines.append("")

        lines.append("---")
        lines.append("*Generated by AI Code Review Agent with Hindsight Memory*")

        return "\n".join(lines)
