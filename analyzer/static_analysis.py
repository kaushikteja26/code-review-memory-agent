"""Ruff static analysis integration."""

import json
import subprocess
import tempfile
from pathlib import Path
from core.models import ReviewFinding, Severity, FindingSource, FileDiff


RUFF_SEVERITY_MAP = {
    "S": Severity.HIGH,       # Security (bandit)
    "E": Severity.HIGH,       # Error
    "F": Severity.HIGH,       # Pyflakes
    "B": Severity.MEDIUM,     # Bugbear
    "W": Severity.MEDIUM,     # Warning
    "A": Severity.MEDIUM,     # Builtins
    "C": Severity.LOW,        # Convention
    "I": Severity.LOW,        # Import
    "N": Severity.LOW,        # Naming
    "D": Severity.LOW,        # Docstring
    "UP": Severity.LOW,       # pyupgrade
}


def _get_severity(code: str) -> Severity:
    """Map a Ruff rule code to a severity level."""
    for prefix, severity in RUFF_SEVERITY_MAP.items():
        if code.startswith(prefix):
            return severity
    return Severity.MEDIUM


def run_ruff_on_files(files: list[FileDiff]) -> list[ReviewFinding]:
    """Run Ruff static analysis on changed Python files."""
    findings = []
    python_files = [f for f in files if f.filename.endswith(".py") and f.patch]

    if not python_files:
        return findings

    with tempfile.TemporaryDirectory() as tmpdir:
        file_map = {}

        for diff_file in python_files:
            content = _extract_content_from_patch(diff_file.patch)
            if not content.strip():
                continue

            temp_path = Path(tmpdir) / diff_file.filename
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_text(content)
            file_map[str(temp_path)] = diff_file.filename

        if not file_map:
            return findings

        try:
            result = subprocess.run(
                ["ruff", "check", "--output-format=json", tmpdir],
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout.strip()
            if output:
                ruff_results = json.loads(output)
                for item in ruff_results:
                    temp_path = item.get("filename", "")
                    original_file = file_map.get(
                        temp_path, Path(temp_path).name
                    )

                    code = item.get("code", "") or ""
                    message = item.get("message", "")
                    location = item.get("location", {})
                    line = location.get("row") if location else None

                    fix_msg = ""
                    if item.get("fix"):
                        fix_msg = item["fix"].get("message", "")

                    findings.append(
                        ReviewFinding(
                            severity=_get_severity(code),
                            file=original_file,
                            line=str(line) if line else None,
                            issue=f"[{code}] {message}",
                            explanation=f"Ruff static analysis: {message}",
                            suggestion=fix_msg,
                            source=FindingSource.STATIC_ANALYSIS,
                        )
                    )
        except FileNotFoundError:
            print("Warning: Ruff not installed. Skipping static analysis.")
        except subprocess.TimeoutExpired:
            print("Warning: Ruff timed out.")
        except json.JSONDecodeError:
            print("Warning: Failed to parse Ruff output.")
        except Exception as e:
            print(f"Warning: Ruff analysis failed: {e}")

    return findings


def _extract_content_from_patch(patch: str) -> str:
    """Extract the resulting file content from a unified diff patch."""
    lines = []
    for line in patch.split("\n"):
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("@@"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
        elif line.startswith("-"):
            continue
        else:
            lines.append(line)
    return "\n".join(lines)
