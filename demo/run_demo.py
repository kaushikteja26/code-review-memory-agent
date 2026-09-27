"""Before/after demo script for the hackathon presentation."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import ReviewOrchestrator
from demo.sample_diffs import get_demo_pr_info, get_demo_files
from demo.seed_memories import seed_demo_memories
from core.models import FindingSource


def print_review(result, label: str):
    """Pretty-print a review result."""
    print(f"\n{'#'*70}")
    print(f"# {label}")
    print(f"{'#'*70}")
    print(f"\n📋 PR: {result.pr_info.title}")
    print(f"👤 Author: {result.pr_info.author}")
    print(f"🔀 Mode: {result.review_mode.upper()}\n")

    print(f"📝 Summary:\n{result.summary}\n")

    if result.memory_stats.total_memories_retrieved > 0:
        print("┌─────────────────────────────────────────────┐")
        print("│          🧠  MEMORY USED                    │")
        print("├─────────────────────────────────────────────┤")
        print(f"│  Memories Retrieved:     {result.memory_stats.total_memories_retrieved:>3}                 │")
        print(f"│  Team Conventions:       {result.memory_stats.team_conventions_matched:>3}                 │")
        print(f"│  Recurring Issues:       {result.memory_stats.recurring_issues_detected:>3}                 │")
        print(f"│  Architectural Decisions:{result.memory_stats.architectural_decisions_applied:>3}                 │")
        print("└─────────────────────────────────────────────┘\n")

    if result.memory_insights:
        print("🧠 TEAM-SPECIFIC FINDINGS (from Hindsight Memory):")
        print("-" * 50)
        for f in result.memory_insights:
            severity_icon = {
                "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"
            }.get(f.severity.value, "⚪")
            print(f"  {severity_icon} [{f.severity.value.upper()}] {f.file}")
            print(f"     Issue: {f.issue}")
            print(f"     Explanation: {f.explanation}")
            if f.memory_reference:
                print(f"     🧠 Memory: {f.memory_reference}")
            if f.suggestion:
                print(f"     💡 Fix: {f.suggestion}")
            print()

    if result.findings:
        print("📋 GENERAL FINDINGS:")
        print("-" * 50)
        for f in result.findings:
            severity_icon = {
                "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"
            }.get(f.severity.value, "⚪")
            print(f"  {severity_icon} [{f.severity.value.upper()}] {f.file}")
            print(f"     Issue: {f.issue}")
            if f.suggestion:
                print(f"     💡 Fix: {f.suggestion}")
            print()

    if result.ruff_findings:
        print(f"🔧 STATIC ANALYSIS ({len(result.ruff_findings)} issues):")
        print("-" * 50)
        for f in result.ruff_findings[:5]:
            print(f"  • {f.file}:{f.line} — {f.issue}")
        if len(result.ruff_findings) > 5:
            print(f"  ... and {len(result.ruff_findings) - 5} more")
        print()

    # Count sources
    memory_count = len(result.memory_insights)
    general_count = len(result.findings)
    ruff_count = len(result.ruff_findings)
    total = memory_count + general_count + ruff_count

    print(f"📊 TOTALS: {total} findings — "
          f"{memory_count} from memory, "
          f"{general_count} general, "
          f"{ruff_count} static analysis\n")


def run_demo():
    """Run the complete before/after demo."""
    print("\n" + "=" * 70)
    print("  🚀 AI Code Review Agent — Before/After Memory Demo")
    print("  HackwithHyderabad 3.0 | PS #8")
    print("=" * 70)

    pr_info = get_demo_pr_info()
    files = get_demo_files()
    orchestrator = ReviewOrchestrator()

    # ─── PHASE 1: WITHOUT MEMORY ─────────────────────────────────────
    print("\n" + "=" * 70)
    print("  📌 PHASE 1: REVIEW WITHOUT MEMORY (Generic)")
    print("  The agent has no team history. Reviews are generic.")
    print("=" * 70)

    result_without = orchestrator.review_synthetic(
        pr_info=pr_info,
        files=files,
        use_memory=False,
    )
    print_review(result_without, "REVIEW WITHOUT MEMORY")

    # ─── PHASE 2: SEED MEMORIES ──────────────────────────────────────
    print("\n" + "=" * 70)
    print("  📌 PHASE 2: SEEDING TEAM KNOWLEDGE INTO HINDSIGHT")
    print("  Simulating what the agent learns from previous PR reviews.")
    print("=" * 70)

    seed_count = seed_demo_memories()
    print(f"\n  ✅ {seed_count} team memories stored in Hindsight.\n")

    # ─── PHASE 3: WITH MEMORY ────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  📌 PHASE 3: REVIEW WITH MEMORY (Team-Specific)")
    print("  The agent now has team history. Watch the difference!")
    print("=" * 70)

    result_with = orchestrator.review_synthetic(
        pr_info=pr_info,
        files=files,
        use_memory=True,
    )
    print_review(result_with, "REVIEW WITH MEMORY")

    # ─── COMPARISON ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  📊 COMPARISON: WITHOUT MEMORY vs WITH MEMORY")
    print("=" * 70)
    print(f"\n  {'Metric':<35} {'Without Memory':>15} {'With Memory':>15}")
    print(f"  {'-'*65}")
    print(f"  {'Total Findings':<35} {len(result_without.findings) + len(result_without.ruff_findings):>15} {len(result_with.findings) + len(result_with.memory_insights) + len(result_with.ruff_findings):>15}")
    print(f"  {'Memory-Based Findings':<35} {len(result_without.memory_insights):>15} {len(result_with.memory_insights):>15}")
    print(f"  {'Memories Retrieved':<35} {result_without.memory_stats.total_memories_retrieved:>15} {result_with.memory_stats.total_memories_retrieved:>15}")
    print(f"  {'Team Conventions Matched':<35} {result_without.memory_stats.team_conventions_matched:>15} {result_with.memory_stats.team_conventions_matched:>15}")
    print(f"  {'Recurring Issues Detected':<35} {result_without.memory_stats.recurring_issues_detected:>15} {result_with.memory_stats.recurring_issues_detected:>15}")
    print(f"  {'Architectural Decisions Applied':<35} {result_without.memory_stats.architectural_decisions_applied:>15} {result_with.memory_stats.architectural_decisions_applied:>15}")

    print("\n  🎯 KEY INSIGHT:")
    print("  WITHOUT MEMORY → Generic review based on general best practices")
    print("  WITH MEMORY    → Team-specific review citing learned conventions")
    print("  The difference demonstrates that Hindsight memory genuinely")
    print("  changes the quality and specificity of code reviews.\n")


if __name__ == "__main__":
    run_demo()
