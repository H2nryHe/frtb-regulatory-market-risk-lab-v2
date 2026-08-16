from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from frtb_lab.release_validation import (
    collect_release_snapshot,
    format_release_summary,
    validate_release_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _public_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line]


@pytest.fixture(scope="module")
def release_snapshot():
    return collect_release_snapshot()


def test_release_validation_snapshot_is_centrally_reproducible(release_snapshot) -> None:
    checks = validate_release_snapshot(release_snapshot)
    assert checks == {
        "SA regression": True,
        "IMA ES regression": True,
        "RFET regression": True,
        "PLA/backtesting regression": True,
        "IMCC/SES regression": True,
        "U.S. crosswalk status": True,
        "Claim audit": True,
    }

    summary = format_release_summary(release_snapshot, checks)
    assert "Overall: PASS" in summary
    assert release_snapshot.selected_sa == pytest.approx(626510.6801585772)
    assert release_snapshot.imcc == pytest.approx(358979.94225370314)
    assert release_snapshot.ses == pytest.approx(26655.82413840059)
    assert release_snapshot.final_total_status == "NOT_CALCULATED"
    assert release_snapshot.us_proposal_status == "PROPOSED / CROSSWALK ONLY"
    assert release_snapshot.unresolved_findings_count == 7


def test_release_validation_cli_runs_without_pythonpath() -> None:
    result = subprocess.run(
        ["python", "-m", "frtb_lab.release_validation"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Overall: PASS" in result.stdout
    assert "Final bank-wide aggregate: NOT_CALCULATED" in result.stdout
    assert "Open findings: 7" in result.stdout


def test_final_report_and_recruiter_package_have_required_sections() -> None:
    report = (REPO_ROOT / "reports" / "FRTB_V2_FINAL_VALIDATION_REPORT.md").read_text()
    required_report_sections = [
        "## 1. Executive Summary",
        "## 2. Scope",
        "## 3. What Was Built",
        "## 4. What Was Not Built",
        "## 5. Data and Assumptions",
        "## 6. Regulatory Sources",
        "## 7. Source Retrieval Dates",
        "## 8. Standardised Approach Results",
        "## 9. IMA Expected Shortfall Results",
        "## 10. RFET Results",
        "## 11. PLA and Backtesting Results",
        "## 12. IMCC and SES Results",
        "## 13. Capital Routing Results",
        "## 14. U.S. 2026 Proposal Crosswalk",
        "## 15. Findings Inventory",
        "## 16. Tests and Validation",
        "## 17. CI and Reproducibility",
        "## 18. Privacy and Release Packaging",
        "## 19. Key Interview Talking Points",
        "## 20. Known Limitations",
        "## 21. Final Decision",
        "## 22. Release Checklist",
        "## 23. Appendix: One-Command Validation",
    ]
    for section in required_report_sections:
        assert section in report
    assert "RELEASE_READY_FOR_EDUCATIONAL_PORTFOLIO_USE" in report

    readme = (REPO_ROOT / "README.md").read_text()
    assert "selected-scope" in readme
    assert "U.S. 2026 Proposal Crosswalk" in readme
    assert "python -m frtb_lab.release_validation" in readme
    assert "not a like-for-like comparison" in readme

    recruiter = (REPO_ROOT / "reports" / "RECRUITER_AND_INTERVIEW_SUMMARY.md").read_text()
    resume = (REPO_ROOT / "reports" / "RESUME_BULLETS.md").read_text()
    assert "30-second summary" in recruiter
    assert "Resume Bullets" in resume
    assert "$626.5k" in recruiter
    assert "$359.0k" in resume


def test_final_scope_and_findings_inventories_are_complete() -> None:
    findings = _read_csv(REPO_ROOT / "governance" / "final_findings_inventory.csv")
    finding_ids = {row["finding_id"] for row in findings}
    assert {
        "RFET-FIND-001",
        "RFET-FIND-002",
        "RFET-FIND-003",
        "RFET-FIND-004",
        "PLA-BT-FIND-001",
        "PLA-BT-FIND-002",
        "US-SOURCE-001",
    } <= finding_ids
    assert sum(row["current_status"] == "OPEN" for row in findings) == 6
    assert any(
        row["current_status"] == "REMEDIATION_IMPLEMENTED_PENDING_VALIDATION"
        for row in findings
    )

    scope = _read_csv(REPO_ROOT / "governance" / "final_scope_matrix.csv")
    by_subcomponent = {row["subcomponent"]: row for row in scope}
    assert by_subcomponent["Final MAR33 aggregate"]["status"] == "OUT_OF_SCOPE"
    assert by_subcomponent["Securitisation DRC"]["status"] == "OUT_OF_SCOPE"
    assert by_subcomponent["Full U.S. proposal engine"]["status"] == "OUT_OF_SCOPE"
    assert by_subcomponent["IMCC"]["status"] == "IMPLEMENTED"


def test_retrieval_dates_and_public_inventory_are_release_ready() -> None:
    register = yaml.safe_load((REPO_ROOT / "regulatory" / "source_register.yaml").read_text())
    assert register["project"]["retrieval_date_basis"] == "UTC"
    assert all(source["retrieved_date"] for source in register["sources"])
    assert {
        source["retrieved_date"]
        for source in register["sources"]
        if str(source["source_id"]).startswith("US_R1887")
    } == {"2026-08-16"}

    inventory = (REPO_ROOT / "reports" / "PUBLIC_RELEASE_FILE_INVENTORY.md").read_text()
    assert "Include in public repository" in inventory
    assert "Keep local / ignored" in inventory
    assert "PROJECT_FRTB_V2_SPEC.md" in inventory
    assert "FRTB_V2_STATUS.md" in inventory
    assert "local_frtb_v2_baseline/" in inventory


def test_ci_workflow_runs_required_release_commands() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "python -m pip install -e \".[dev]\"" in workflow
    assert "python -m pytest -q" in workflow
    assert "python -m ruff check ." in workflow
    assert "python -m frtb_lab.release_validation" in workflow
    assert all(version in workflow for version in ["3.10", "3.11", "3.12"])


def test_tests_do_not_shell_out_to_undeclared_ripgrep_binary() -> None:
    ripgrep_literal = '"' + chr(114) + chr(103) + '"'
    for path in (REPO_ROOT / "tests").glob("test_*.py"):
        text = path.read_text()
        assert ripgrep_literal not in text, path


def test_public_release_has_no_local_paths_or_obvious_credential_material() -> None:
    local_path = "/Users/" + "linruihe/"
    sensitive_patterns = [
        "api" + r"[_-]?key",
        "sec" + "ret",
        "tok" + "en",
        "pass" + "word",
        "aws" + r"[_-]access[_-]key[_-]id",
        "aws" + r"[_-]secret[_-]access[_-]key",
        "database" + r"[_-]?url",
        r"postgres://",
        "BEGIN RSA " + "PRIVATE KEY",
        "BEGIN OPENSSH " + "PRIVATE KEY",
    ]
    assignment_like = r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}"
    joined = "|".join(f"(?:{pattern}){assignment_like}" for pattern in sensitive_patterns)
    excluded = {
        REPO_ROOT / "tests" / "test_release_regression.py",
    }
    for path in _public_paths():
        if not path.is_file() or path in excluded:
            continue
        text = path.read_text(errors="ignore")
        assert local_path not in text, path
        assert re.search(joined, text, flags=re.IGNORECASE) is None, path
