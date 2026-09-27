"""LLM prompt templates for the code review agent."""

SYSTEM_PROMPT = """You are a senior software engineer performing a thorough code review. 
You are detail-oriented, constructive, and deeply familiar with Python best practices.

Your reviews are structured, actionable, and specific to the code being reviewed.
You cite exact lines, explain WHY something is an issue, and suggest concrete fixes.

When team-specific memory context is provided, you MUST incorporate it into your review.
If the code violates a known team convention or repeats a previously identified issue,
you must explicitly call that out and reference the team's established practice."""

REVIEW_PROMPT_TEMPLATE = """## Code Review Request

### Pull Request Information
- **Title**: {pr_title}
- **Author**: {pr_author}
- **Repository**: {pr_repo}
- **Description**: {pr_description}

### Changed Files and Diffs
{diff_content}

{ruff_section}

{memory_section}

### Your Task

Analyze this pull request and provide a thorough code review. 

**CRITICAL FORMAT REQUIREMENT:** You MUST output findings as a JSON ARRAY in a ```json code block. No wrapper object, no extra fields.

```json
[
  {{
    "severity": "critical|high|medium|low",
    "file": "filename.py",
    "line": "line number or range or null",
    "issue": "Short issue title",
    "explanation": "Detailed explanation of why this is a problem",
    "suggestion": "Concrete fix or improvement",
    "source": "general_reasoning|team_convention|historical_memory",
    "memory_reference": "Reference to team memory if applicable, or null"
  }}
]
```

⚠️ DO NOT output a wrapper object with "findings" key. Output the ARRAY directly.
⚠️ Use ONLY these fields: severity, file, line, issue, explanation, suggestion, source, memory_reference
⚠️ Use ONLY these source values: general_reasoning, team_convention, historical_memory, static_analysis

IMPORTANT RULES:
1. If team memory context is provided, PRIORITIZE checking for violations of team conventions.
2. For each finding sourced from team memory, set source to "team_convention" or "historical_memory" and fill memory_reference.
3. Look for: bugs, security issues, maintainability problems, naming issues, missing error handling, architectural concerns.
4. Be specific — cite exact code from the diff.
5. Start your response with a brief 2-3 sentence summary assessment, then provide the JSON findings block.
6. LIMIT: Output at most 5 findings total. Focus on the most critical issues.

Provide your review now."""

RUFF_SECTION_TEMPLATE = """### Static Analysis Results (Ruff)
The following issues were detected by Ruff static analysis:
{ruff_findings}

Consider these findings in your review. You don't need to repeat them verbatim,
but validate whether they represent real issues and include significant ones."""

MEMORY_SECTION_TEMPLATE = """### Team History & Conventions (from Hindsight Memory)
The following team-specific knowledge was retrieved from previous code reviews.
You MUST incorporate this context into your review. If the current PR violates
any of these established conventions, flag it explicitly and reference the convention.

{memory_context}

CRITICAL: When a finding is based on team memory, you MUST:
- Set "source" to "team_convention" or "historical_memory"  
- Set "memory_reference" to describe which team convention applies
- Explain that this feedback is based on the team's established practices"""

NO_MEMORY_SECTION = """### Note
No team history is available. This is a first-time review without historical context.
Provide your best general-purpose code review based on Python best practices."""

KNOWLEDGE_EXTRACTION_PROMPT = """You just completed a code review for a pull request. 
Extract the most important engineering learnings that should be remembered for future reviews.

### PR Information
- **Repository**: {pr_repo}
- **PR**: {pr_ref}
- **Title**: {pr_title}

### Review Findings
{review_text}

### Your Task
Extract 2-5 key learnings from this review. Each learning should be a reusable team convention,
architectural decision, or recurring issue pattern that would help with future reviews.

Output EXACTLY as a JSON array:
```json
[
  {{
    "type": "team_convention|architectural_decision|recurring_issue|review_feedback",
    "content": "The specific rule, decision, or pattern",
    "context": "Why this matters and when it applies"
  }}
]
```

Only extract genuinely useful, generalizable learnings. Skip trivial style issues.
Focus on patterns that would change how future code is reviewed."""


def build_review_prompt(
    pr_title: str,
    pr_author: str,
    pr_repo: str,
    pr_description: str,
    diff_content: str,
    ruff_findings: str | None = None,
    memory_context: str | None = None,
) -> str:
    """Build the complete review prompt for the LLM."""
    ruff_section = ""
    if ruff_findings:
        ruff_section = RUFF_SECTION_TEMPLATE.format(ruff_findings=ruff_findings)

    if memory_context:
        memory_section = MEMORY_SECTION_TEMPLATE.format(memory_context=memory_context)
    else:
        memory_section = NO_MEMORY_SECTION

    return REVIEW_PROMPT_TEMPLATE.format(
        pr_title=pr_title,
        pr_author=pr_author,
        pr_repo=pr_repo,
        pr_description=pr_description or "No description provided.",
        diff_content=diff_content,
        ruff_section=ruff_section,
        memory_section=memory_section,
    )


def build_extraction_prompt(
    pr_repo: str,
    pr_ref: str,
    pr_title: str,
    review_text: str,
) -> str:
    """Build the knowledge extraction prompt."""
    return KNOWLEDGE_EXTRACTION_PROMPT.format(
        pr_repo=pr_repo,
        pr_ref=pr_ref,
        pr_title=pr_title,
        review_text=review_text,
    )
