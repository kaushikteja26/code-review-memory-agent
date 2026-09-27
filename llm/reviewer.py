"""LLM reviewer supporting Groq and Google Gemini for code review generation."""

import json
import re
from config import settings
from core.models import (
    ReviewFinding,
    Severity,
    FindingSource,
    MemoryEntry,
    MemoryType,
    PRInfo,
    FileDiff,
)
from core.prompts import (
    SYSTEM_PROMPT,
    build_review_prompt,
    build_extraction_prompt,
)


class LLMReviewer:
    """Generates code reviews using Groq or Google Gemini LLM with memory-augmented prompts."""

    def __init__(self):
        if not settings.has_llm:
            raise RuntimeError(
                "No LLM provider configured. Set GROQ_API_KEY or GOOGLE_API_KEY in .env"
            )
        
        self._provider = settings.LLM_PROVIDER.lower()
        
        if self._provider == "groq":
            if not settings.has_groq:
                raise RuntimeError("GROQ_API_KEY not configured but LLM_PROVIDER=groq")
            from groq import Groq
            self._client = Groq(api_key=settings.GROQ_API_KEY)
            self._model = settings.GROQ_MODEL
        elif self._provider == "google":
            if not settings.has_google:
                raise RuntimeError("GOOGLE_API_KEY not configured but LLM_PROVIDER=google")
            import google.generativeai as genai
            genai.configure(api_key=settings.GOOGLE_API_KEY)
            self._client = genai.GenerativeModel(settings.GOOGLE_MODEL)
            self._model = settings.GOOGLE_MODEL
        else:
            raise RuntimeError(f"Unknown LLM_PROVIDER: {settings.LLM_PROVIDER}. Use 'groq' or 'google'")

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Make a call to the LLM."""
        try:
            if self._provider == "groq":
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.3,
                    max_tokens=4096,
                )
                return response.choices[0].message.content or ""
            
            elif self._provider == "google":
                # Combine system + user prompt for Gemini
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = self._client.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 8192,
                    },
                )
                return response.text or ""
        except Exception as e:
            print(f"LLM call failed: {e}")
            return ""

    def review(
        self,
        pr_info: PRInfo,
        files: list[FileDiff],
        ruff_findings: list[ReviewFinding] | None = None,
        memory_context: str | None = None,
    ) -> tuple[str, list[ReviewFinding]]:
        """Generate a code review using the LLM.

        Returns (summary_text, list_of_findings).
        """
        # Build diff content
        diff_content = self._format_diffs(files)

        # Format ruff findings if any
        ruff_text = None
        if ruff_findings:
            ruff_text = "\n".join(
                f"- [{f.severity.value}] {f.file}:{f.line} — {f.issue}"
                for f in ruff_findings
            )

        # Build the full prompt
        prompt = build_review_prompt(
            pr_title=pr_info.title,
            pr_author=pr_info.author,
            pr_repo=f"{pr_info.owner}/{pr_info.repo}",
            pr_description=pr_info.description,
            diff_content=diff_content,
            ruff_findings=ruff_text,
            memory_context=memory_context,
        )

        # Call LLM
        raw_response = self._call_llm(SYSTEM_PROMPT, prompt)
        if not raw_response:
            return "Review generation failed.", []

        # Parse response
        summary, findings = self._parse_response(raw_response)
        return summary, findings

    def extract_knowledge(
        self, pr_info: PRInfo, review_findings: list[ReviewFinding]
    ) -> list[MemoryEntry]:
        """Extract learnable knowledge from a completed review."""
        review_text = "\n".join(
            f"- [{f.severity.value}] {f.file}: {f.issue} — {f.explanation}"
            for f in review_findings
        )

        prompt = build_extraction_prompt(
            pr_repo=f"{pr_info.owner}/{pr_info.repo}",
            pr_ref=f"PR #{pr_info.number}",
            pr_title=pr_info.title,
            review_text=review_text,
        )

        raw = self._call_llm(
            "You are a senior engineering knowledge curator. Extract reusable learnings from code reviews.",
            prompt,
        )

        return self._parse_knowledge(raw, pr_info)

    def _format_diffs(self, files: list[FileDiff]) -> str:
        """Format file diffs for the LLM prompt."""
        parts = []
        for f in files:
            if not f.patch:
                continue
            parts.append(f"#### File: {f.filename} ({f.status})")
            parts.append(f"+{f.additions} -{f.deletions}")
            parts.append("```diff")
            # Truncate very large patches
            patch = f.patch
            if len(patch) > 3000:
                patch = patch[:3000] + "\n... (truncated)"
            parts.append(patch)
            parts.append("```")
            parts.append("")
        return "\n".join(parts) if parts else "No file diffs available."

    def _parse_response(self, raw: str) -> tuple[str, list[ReviewFinding]]:
        """Parse the LLM response into summary and structured findings."""
        # Extract summary (everything before the JSON block)
        json_match = re.search(r"```json\s*\n(.*?)\n\s*```", raw, re.DOTALL)

        summary = raw
        findings = []

        if json_match:
            summary = raw[: json_match.start()].strip()
            json_str = json_match.group(1).strip()
            try:
                items = json.loads(json_str)
                # Handle both direct array and wrapped object with "findings" key
                if isinstance(items, dict) and "findings" in items:
                    items = items["findings"]
                if isinstance(items, list):
                    for item in items:
                        findings.append(self._item_to_finding(item))
            except json.JSONDecodeError:
                # Try to find individual JSON objects
                for obj_match in re.finditer(r"\{[^{}]+\}", json_str):
                    try:
                        item = json.loads(obj_match.group())
                        findings.append(self._item_to_finding(item))
                    except json.JSONDecodeError:
                        continue

        if not summary:
            summary = "Code review completed."

        return summary, findings

    def _item_to_finding(self, item: dict) -> ReviewFinding:
        """Convert a parsed JSON item into a ReviewFinding."""
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        source_map = {
            "general_reasoning": FindingSource.GENERAL_REASONING,
            "team_convention": FindingSource.TEAM_CONVENTION,
            "historical_memory": FindingSource.HISTORICAL_MEMORY,
            "static_analysis": FindingSource.STATIC_ANALYSIS,
        }

        return ReviewFinding(
            severity=severity_map.get(
                item.get("severity", "medium"), Severity.MEDIUM
            ),
            file=item.get("file", "unknown"),
            line=item.get("line"),
            issue=item.get("issue", ""),
            explanation=item.get("explanation", ""),
            suggestion=item.get("suggestion", ""),
            source=source_map.get(
                item.get("source", "general_reasoning"),
                FindingSource.GENERAL_REASONING,
            ),
            memory_reference=item.get("memory_reference"),
        )

    def _parse_knowledge(
        self, raw: str, pr_info: PRInfo
    ) -> list[MemoryEntry]:
        """Parse extracted knowledge into MemoryEntry objects."""
        entries = []
        json_match = re.search(r"```json\s*\n(.*?)\n\s*```", raw, re.DOTALL)
        if not json_match:
            return entries

        try:
            items = json.loads(json_match.group(1).strip())
            if not isinstance(items, list):
                return entries

            type_map = {
                "team_convention": MemoryType.TEAM_CONVENTION,
                "architectural_decision": MemoryType.ARCHITECTURAL_DECISION,
                "recurring_issue": MemoryType.RECURRING_ISSUE,
                "review_feedback": MemoryType.REVIEW_FEEDBACK,
            }

            for item in items:
                mem_type = type_map.get(
                    item.get("type", "review_feedback"),
                    MemoryType.REVIEW_FEEDBACK,
                )
                entries.append(
                    MemoryEntry(
                        type=mem_type,
                        content=item.get("content", ""),
                        source_pr=f"PR #{pr_info.number} ({pr_info.owner}/{pr_info.repo})",
                        context=item.get("context", ""),
                    )
                )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to parse knowledge extraction: {e}")

        return entries