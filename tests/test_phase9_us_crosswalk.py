from __future__ import annotations

import csv
import subprocess
from pathlib import Path

import pytest
import yaml

from frtb_lab.ima.backtesting import threshold_status
from frtb_lab.ima.capital_routing import calculate_phase8_capital_routing
from frtb_lab.ima.desk_eligibility import calculate_phase7_desk_diagnostics
from frtb_lab.ima.es import calculate_phase5_ima_es
from frtb_lab.ima.imcc import calculate_phase8_imcc
from frtb_lab.ima.nmrf import calculate_phase8_ses
from frtb_lab.ima.rfet import calculate_phase6_rfet
from frtb_lab.sa.standardised import calculate_selected_scope_standardised_approach

REPO_ROOT = Path(__file__).resolve().parents[1]
REGULATORY = REPO_ROOT / "regulatory"
REPORT = REPO_ROOT / "reports" / "sections" / "us_2026_proposed_market_risk_crosswalk.md"
US_SOURCE_IDS = {
    "US_R1887_FED",
    "US_R1887_FEDERAL_REGISTER",
    "US_R1887_OCC",
    "US_R1887_FDIC",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _source_rows() -> dict[str, dict[str, object]]:
    with (REGULATORY / "source_register.yaml").open() as handle:
        register = yaml.safe_load(handle)
    return {row["source_id"]: row for row in register["sources"]}


def _public_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [REPO_ROOT / line for line in result.stdout.splitlines() if line.strip()]


def test_us_source_records_and_status_are_current_phase9_freeze() -> None:
    sources = _source_rows()
    assert US_SOURCE_IDS <= sources.keys()

    fed = sources["US_R1887_FED"]
    fr = sources["US_R1887_FEDERAL_REGISTER"]
    occ = sources["US_R1887_OCC"]
    fdic = sources["US_R1887_FDIC"]

    assert fed["status"] == "Rulemaking Proposal"
    assert fr["status"] == "Proposed Rule / Notice of proposed rulemaking"
    assert fr["federal_register_citation"] == "91 FR 14952"
    assert fr["document_number"] == "2026-05959"
    assert fr["docket"] == "Docket No. R-1887; Docket ID OCC-2026-0265"
    assert "7100-AH20" in fr["rin"]
    assert fed["retrieved_date"] == "2026-08-16"
    assert fr["retrieved_date"] == "2026-08-16"
    assert occ["publication_date"] == "2026-03-19"
    assert fdic["publication_date"] == "2026-03-19"
    assert fed["effective_date"] is None
    assert fr["effective_date"] is None


def test_us_status_artifact_records_proposed_boundary_without_effective_date() -> None:
    text = (REGULATORY / "us_2026_status.md").read_text()
    assert "PROPOSED" in text
    assert "NOT FINAL" in text
    assert "NOT CURRENT U.S. RULE" in text
    assert "91 FR 14952" in text
    assert "2026-05959" in text
    assert "2026-06-18" in text
    assert "No effective date is recorded because the source is a proposal." in text
    assert "No official R-1887 final rule" in text


def test_us_parameter_register_is_separate_crosswalk_only_and_official() -> None:
    rows = _read_csv(REGULATORY / "us_2026_proposed_parameters.csv")
    assert rows
    assert {row["implementation_status"] for row in rows} == {"CROSSWALK_ONLY"}
    assert {row["proposal_status"] for row in rows} == {"PROPOSED"}
    assert all(row["US_source"].startswith("US_R1887_") for row in rows)
    assert all(
        "US_R1887_FEDERAL_REGISTER" in row["US_source"] or row["US_source"] in US_SOURCE_IDS
        for row in rows
    )

    by_id = {row["parameter_id"]: row for row in rows}
    assert by_id["US_APPLICABILITY_TATL_PERCENT"]["proposed_value"] == "10"
    assert by_id["US_APPLICABILITY_TATL_DOLLAR"]["proposed_value"] == "5000000000"
    assert by_id["US_STANDARDIZED_NDCR_COMPONENTS"]["proposed_value"] == "SBM+RRAO"
    assert by_id["US_NMRF_TYPE_B_RHO"]["proposed_value"] == "0.36"
    assert by_id["US_NMRF_TYPE_B_RHO"]["same_as_Basel"] == "NO"
    assert by_id["US_FALLBACK_FAIR_VALUE"]["proposed_value"] == "sum_absolute_fair_value"


def test_us_parameters_do_not_contaminate_basel_configs_or_parameter_register() -> None:
    basel_rows = _read_csv(REGULATORY / "parameter_crosswalk.csv")
    assert not any(row["parameter_id"].startswith("US_") for row in basel_rows)

    config_paths = list((REPO_ROOT / "configs").rglob("*.yaml"))
    assert config_paths
    for path in config_paths:
        text = path.read_text()
        assert "us_2026_proposed_parameters" not in text
        assert "US_R1887" not in text
        assert "TYPE_A" not in text
        assert "TYPE_B" not in text
        assert "0.36" not in text


def test_main_crosswalk_covers_required_topics_and_sources() -> None:
    text = (REGULATORY / "us_2026_proposal_crosswalk.md").read_text()
    required_topics = [
        "A. Market-risk scope / applicability",
        "D. Standardised / standardized non-default capital",
        "J. Residual risk add-on",
        "K. Default risk capital",
        "L. Models-based non-default capital",
        "S. NMRF treatment",
        "T. PLA",
        "U. Desk-level backtesting",
        "W. SA fallback mechanics",
        "Z. Reporting / disclosure",
        "SYN_EQ_BARRIER",
        "SA_all_desks - SA_G,A",
        "Fallback capital requirement",
    ]
    for topic in required_topics:
        assert topic in text

    table_lines = [line for line in text.splitlines() if line.startswith("| ")]
    data_lines = [line for line in table_lines if " | " in line and "topic |" not in line]
    data_lines = [
        line for line in data_lines if not set(line.replace("|", "").strip()) <= {"-", " "}
    ]
    assert len([line for line in data_lines if "US_R1887_" in line]) >= 26
    assert "same as Basel" not in text


def test_nmrf_type_a_type_b_crosswalk_and_aggregation_gap() -> None:
    rows = _read_csv(REGULATORY / "us_nmrf_crosswalk.csv")
    concepts = {row["concept"]: row for row in rows}
    assert "Type A NMRF treatment" in concepts
    assert "Type B NMRF treatment" in concepts
    assert "SES" in concepts["Type A NMRF treatment"]["US_proposed_treatment"]
    assert "rb = 0.36" in concepts["Type B NMRF treatment"]["US_proposed_treatment"]
    assert "not present" in concepts["NMRF category taxonomy"]["material_difference"]
    assert all(row["US_source"].startswith("US_R1887_FEDERAL_REGISTER") for row in rows)


def test_source_interpretation_notes_flag_ambiguity_without_changing_basel() -> None:
    text = (REGULATORY / "us_source_interpretation_notes.md").read_text()
    assert "SOURCE_TEXT_REQUIRES_LEGAL_INTERPRETATION" in text
    assert "Question 152" in text
    assert "§__.214(b)(3)(iii)(A)" in text
    assert "does not alter the Basel Phase 6 RFET engine" in text
    assert threshold_status(0.99, 12) == "PASS"
    assert threshold_status(0.99, 13) == "BREACH"
    assert threshold_status(0.975, 29) == "PASS"
    assert threshold_status(0.975, 30) == "BREACH"


def test_gap_matrix_has_required_high_priority_gaps() -> None:
    rows = _read_csv(REGULATORY / "us_project_gap_matrix.csv")
    high = {row["gap_id"]: row for row in rows if row["severity"] == "HIGH"}
    assert {
        "US-GAP-001",
        "US-GAP-002",
        "US-GAP-003",
        "US-GAP-004",
        "US-GAP-005",
        "US-GAP-006",
        "US-GAP-007",
    } <= high.keys()
    assert high["US-GAP-001"]["status"] == "DIFFERENT_METHODOLOGY"
    assert high["US-GAP-005"]["status"] == "NOT_IMPLEMENTED"
    assert all(row["would_require_code_change"] == "true" for row in high.values())


def test_phase9_report_contains_required_sections_and_claim_boundaries() -> None:
    text = REPORT.read_text()
    normalized = " ".join(text.split())
    required_sections = [
        "## Current Rulemaking Status",
        "## U.S. Proposed Applicability",
        "## Proposed Market-Risk Architecture",
        "## Standardized Non-Default Capital",
        "## Residual Risk Add-On",
        "## Models-Based Non-Default Capital",
        "## NMRF: Basel vs U.S. Type A / Type B",
        "## Desk-Level Backtesting",
        "## Fallback Capital Requirement",
        "## Why No U.S. Capital Number Is Produced",
        "## Key U.S. Proposal Differences to Explain in an Interview",
    ]
    for section in required_sections:
        assert section in text
    assert "not as a final U.S. capital rule" in text
    assert "does not calculate a U.S. portfolio capital number" in normalized
    assert "Phase 8 is conceptually related but not numerically equivalent" in normalized


def test_readme_contains_minimal_phase9_disclaimer() -> None:
    text = (REPO_ROOT / "README.md").read_text()
    assert "Phase 9" in text
    assert "Regulatory Crosswalk" in text
    assert "U.S. 2026 proposed market-risk framework" in text
    assert "does not claim U.S. regulatory compliance" in text
    assert "does not treat R-1887 as final" in text
    assert "does not produce a U.S. proposal capital number" in text


def test_basel_regression_values_are_unchanged_after_phase9() -> None:
    sa = calculate_selected_scope_standardised_approach(write_artifacts=False)
    phase5 = calculate_phase5_ima_es(write_artifacts=False)
    phase6 = calculate_phase6_rfet(write_artifacts=False)
    phase7 = calculate_phase7_desk_diagnostics(write_artifacts=False)
    imcc = calculate_phase8_imcc(write_artifacts=False)
    ses = calculate_phase8_ses(write_artifacts=False)
    routing = calculate_phase8_capital_routing(write_artifacts=False)

    assert sa["selected_scope_standardised_approach_capital"] == pytest.approx(
        626510.6801585772
    )
    assert phase5["stress_calibration"].es_f_c == pytest.approx(135310.97891484312)
    assert phase5["stress_calibration"].es_r_c == pytest.approx(136600.78255244752)
    assert phase5["stress_calibration"].es_r_s == pytest.approx(377307.3028054556)

    rfet = {row.risk_factor_id: row.rfet_mechanics_result for row in phase6["results"]}
    assert rfet == {
        "RF_GIRR_USD_5Y_RATE": "PASS",
        "RF_EQUITY_SPX_SPOT": "PASS",
        "RF_EQUITY_SPX_VOL_1Y": "FAIL",
        "RF_FX_EURUSD_SPOT": "FAIL",
        "RF_FX_EURUSD_VOL_1Y": "PASS",
    }
    pla = {row.desk_id: row.pla_zone for row in phase7["diagnostics"]}
    assert pla == {"TD-RATES": "GREEN", "TD-EQUITY": "GREEN", "TD-FX": "RED"}
    assert imcc.simulated_selected_imcc == pytest.approx(358979.94225370314)
    assert ses.simulated_selected_ses == pytest.approx(26655.82413840059)
    assert routing.final_total_status == "NOT_CALCULATED"


def test_no_us_portfolio_result_or_final_rule_claim_artifacts_exist() -> None:
    forbidden_paths = [
        REPO_ROOT / "src" / "frtb_lab" / "us_capital.py",
        REPO_ROOT / "src" / "frtb_lab" / "us_2026_capital.py",
        REPO_ROOT / "src" / "frtb_lab" / "ima" / "us_ndcr.py",
        REPO_ROOT / "configs" / "ima" / "us_2026_proposed_parameters.yaml",
        REPO_ROOT / "configs" / "sa" / "us_2026_proposed_parameters.yaml",
        REPO_ROOT / "data" / "artifacts" / "us_2026_portfolio_capital.csv",
    ]
    assert not any(path.exists() for path in forbidden_paths)

    public_text = "\n".join(
        path.read_text(errors="ignore") for path in _public_files() if path.is_file()
    )
    forbidden_claims = [
        "U.S. FRTB " + "compliant",
        "US FRTB " + "compliant",
        "Federal Reserve " + "compliant",
        "Fed " + "compliant",
        "OCC " + "compliant",
        "FDIC " + "compliant",
        "current U.S. " + "FRTB",
        "implemented U.S. " + "regulation",
        "final U.S. " + "rule",
        "effective U.S. " + "FRTB",
        "regulator " + "approved",
        "supervisory " + "approved",
    ]
    assert not any(claim in public_text for claim in forbidden_claims)


def test_privacy_git_and_network_independence_boundaries() -> None:
    ignored = subprocess.run(
        ["git", "check-ignore", "-v", "PROJECT_FRTB_V2_SPEC.md", "FRTB_V2_STATUS.md"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert len([line for line in ignored.stdout.splitlines() if line.strip()]) == 2
    for path in _public_files():
        if path.is_file():
            assert "/Users/" + "linruihe/" not in path.read_text(errors="ignore")

    test_text = Path(__file__).read_text()
    assert "requests" + "." not in test_text
    assert "urllib" + ".request" not in test_text
