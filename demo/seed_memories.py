"""Seed historical team knowledge into Hindsight for the demo."""

from core.models import MemoryEntry, MemoryType
from memory.hindsight_manager import HindsightMemoryManager


SEED_MEMORIES = [
    MemoryEntry(
        type=MemoryType.TEAM_CONVENTION,
        content="All database access must go through repository/service layer classes. Never place raw database queries or direct DB connections inside API route handlers. Use the repository pattern (e.g., UserRepository, OrderRepository) to encapsulate data access.",
        source_pr="PR #12 (kaushikteja26/code_review_agent)",
        context="A junior developer placed sqlite3.connect() directly in an API route. Senior reviewer rejected it and required moving all DB logic to a dedicated repository class.",
    ),
    MemoryEntry(
        type=MemoryType.TEAM_CONVENTION,
        content="Do not use raw SQL string formatting or f-strings for database queries. Always use parameterized queries or the ORM query builder to prevent SQL injection vulnerabilities.",
        source_pr="PR #15 (kaushikteja26/code_review_agent)",
        context="A developer used f-string interpolation in SQL queries which is a critical SQL injection risk. The team mandates parameterized queries at all times.",
    ),
    MemoryEntry(
        type=MemoryType.TEAM_CONVENTION,
        content="All external API calls and network I/O operations must use async functions (async/await). Do not use synchronous requests library for external HTTP calls. Use httpx.AsyncClient or aiohttp instead.",
        source_pr="PR #18 (kaushikteja26/code_review_agent)",
        context="Synchronous requests.post() was blocking the event loop in a FastAPI async context. Team standardized on httpx.AsyncClient for all external calls.",
    ),
    MemoryEntry(
        type=MemoryType.TEAM_CONVENTION,
        content="All API error responses must use the project's standard error wrapper class AppError. Do not return raw dicts with 'error' keys or raise generic HTTPException without proper error codes. Use AppError(code=..., message=..., details=...) for consistency.",
        source_pr="PR #21 (kaushikteja26/code_review_agent)",
        context="Multiple endpoints were returning inconsistent error formats. Team adopted AppError wrapper for all error responses to ensure uniform error handling across the API.",
    ),
    MemoryEntry(
        type=MemoryType.ARCHITECTURAL_DECISION,
        content="Do not introduce new third-party dependencies when an existing internal utility module already provides the needed functionality. Check app/utils/ before adding a new pip package. The team maintains shared utilities for validation, formatting, and common operations.",
        source_pr="PR #24 (kaushikteja26/code_review_agent)",
        context="A developer added a new validation library when app/utils/validators.py already had the needed functions. Team decided to consolidate utilities internally.",
    ),
    MemoryEntry(
        type=MemoryType.TEAM_CONVENTION,
        content="All API endpoint handler functions must have type-annotated parameters using Pydantic models for request validation. Do not accept raw dict or untyped parameters. Define request/response schemas as Pydantic BaseModel classes.",
        source_pr="PR #27 (kaushikteja26/code_review_agent)",
        context="Endpoints accepting raw dict parameters bypass FastAPI's automatic validation. Team requires Pydantic models for all request bodies.",
    ),
    MemoryEntry(
        type=MemoryType.RECURRING_ISSUE,
        content="Developers frequently forget to add proper type hints on new functions and method parameters. All new code must include type annotations for function parameters and return types.",
        source_pr="Multiple PRs (kaushikteja26/code_review_agent)",
        context="This has been flagged in 6 out of the last 10 reviews. It's a recurring issue that the team is actively working to fix.",
    ),
    MemoryEntry(
        type=MemoryType.ARCHITECTURAL_DECISION,
        content="Database connection strings and credentials must never be hardcoded in source code. All connection details must come from environment variables or the project's configuration module (config.py). Hardcoded passwords are a critical security violation.",
        source_pr="PR #30 (kaushikteja26/code_review_agent)",
        context="A developer hardcoded database credentials in a route handler. This was caught in review and the team established a strict rule against hardcoded secrets.",
    ),
    MemoryEntry(
        type=MemoryType.REVIEW_FEEDBACK,
        content="When modifying existing async endpoints, do not downgrade them to synchronous. The team has standardized on async handlers for all endpoints that perform I/O operations. Converting async to sync causes performance regression.",
        source_pr="PR #33 (kaushikteja26/code_review_agent)",
        context="A refactor accidentally removed async/await from an endpoint, causing performance issues under load.",
    ),
    MemoryEntry(
        type=MemoryType.TEAM_CONVENTION,
        content="Email validation must use the project's existing email validation utility in app/utils/. Do not write custom naive email checks (like checking for '@' symbol). Use the validate_email function from the shared utilities.",
        source_pr="PR #35 (kaushikteja26/code_review_agent)",
        context="A developer wrote a simplistic email validation that just checks for '@'. The team has a proper validator with RFC compliance.",
    ),
]


def seed_demo_memories() -> int:
    """Seed all demo memories into Hindsight. Returns count of stored memories."""
    manager = HindsightMemoryManager()
    stored = 0

    print("\n🌱 Seeding team knowledge into Hindsight...")
    print(f"   {len(SEED_MEMORIES)} memories to store\n")

    for i, entry in enumerate(SEED_MEMORIES, 1):
        success = manager.store_memory(entry)
        if success:
            stored += 1
            print(f"   ✅ [{i}/{len(SEED_MEMORIES)}] {entry.type.value}: {entry.content[:60]}...")
        else:
            print(f"   ❌ [{i}/{len(SEED_MEMORIES)}] Failed to store: {entry.content[:60]}...")

    print(f"\n🌱 Seeding complete: {stored}/{len(SEED_MEMORIES)} memories stored.\n")
    return stored


if __name__ == "__main__":
    seed_demo_memories()
