from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from frtb_lab.ima.backtesting import threshold_status
from frtb_lab.ima.capital_routing import calculate_phase8_capital_routing
from frtb_lab.ima.desk_eligibility import calculate_phase7_desk_diagnostics
from frtb_lab.ima.es import calculate_phase5_ima_es
from frtb_lab.ima.imcc import calculate_phase8_imcc
from frtb_lab.ima.nmrf import calculate_phase8_ses
from frtb_lab.ima.rfet import calculate_phase6_rfet, reduced_set_rfet_audit
from frtb_lab.sa.standardised import calculate_selected_scope_standardised_approach

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ReleaseValidationSnapshot:
    selected_sbm: float
    drc: float
    rrao: float
    selected_sa: float
    es_f_c: float
    es_r_c: float
    es_r_s: float
    phase5_reduced_set_coverage: float
    rfet_results: dict[str, tuple[str, str, str]]
    reduced_set_audit_status: str
    pla_zones: dict[str, str]
    backtesting_statuses: dict[str, dict[float, str]]
    desk_diagnostics: dict[str, str]
    desk_routes: dict[str, str]
    imcc: float
    ses: float
    final_total_status: str
    us_proposal_status: str
    unresolved_findings_count: int


EXPECTED = {
    "selected_sbm": 601060.6801585773,
    "drc": 25200.0,
    "rrao": 250.0,
    "selected_sa": 626510.6801585772,
    "es_f_c": 135310.97891484312,
    "es_r_c": 136600.78255244752,
    "es_r_s": 377307.3028054556,
    "phase5_reduced_set_coverage": 1.0116454032543514,
    "imcc": 358979.94225370314,
    "ses": 26655.82413840059,
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _unresolved_findings_count() -> int:
    final_inventory = REPO_ROOT / "governance" / "final_findings_inventory.csv"
    if final_inventory.exists():
        counted_statuses = {"OPEN", "REMEDIATION_IMPLEMENTED_PENDING_VALIDATION"}
        return sum(
            row.get("current_status") in counted_statuses
            for row in _read_csv(final_inventory)
        )

    files = [
        REPO_ROOT / "governance" / "rfet_findings.csv",
        REPO_ROOT / "governance" / "pla_backtesting_findings.csv",
    ]
    count = 0
    for path in files:
        count += sum(row.get("status") == "OPEN" for row in _read_csv(path))
    return count


def _us_proposal_status() -> str:
    text = (REPO_ROOT / "regulatory" / "us_2026_status.md").read_text()
    required = ["PROPOSED", "NOT FINAL", "NOT CURRENT U.S. RULE"]
    if all(fragment in text for fragment in required):
        return "PROPOSED / CROSSWALK ONLY"
    return "REQUIRES_REVIEW"


def collect_release_snapshot() -> ReleaseValidationSnapshot:
    sa = calculate_selected_scope_standardised_approach(write_artifacts=False)
    phase5 = calculate_phase5_ima_es(write_artifacts=False)
    phase6 = calculate_phase6_rfet(write_artifacts=False)
    phase7 = calculate_phase7_desk_diagnostics(write_artifacts=False)
    imcc = calculate_phase8_imcc(write_artifacts=False)
    ses = calculate_phase8_ses(write_artifacts=False)
    routing = calculate_phase8_capital_routing(write_artifacts=False)

    rfet_results = {
        row.risk_factor_id: (
            row.rfet_mechanics_result,
            row.passing_route,
            row.model_treatment_candidate,
        )
        for row in phase6["results"]
    }
    pla_zones = {row.desk_id: row.pla_zone for row in phase7["diagnostics"]}
    desk_diagnostics = {
        row.desk_id: row.diagnostic_status for row in phase7["diagnostics"]
    }
    backtesting_statuses: dict[str, dict[float, str]] = {}
    for summary in phase7["backtesting"]["summaries"]:
        backtesting_statuses.setdefault(summary.desk_id, {})[
            summary.confidence_level
        ] = summary.threshold_status

    desk_routes = {
        row["desk_id"]: row["phase8_route"]
        for row in _read_csv(REPO_ROOT / "governance" / "phase8_desk_routing.csv")
    }

    return ReleaseValidationSnapshot(
        selected_sbm=sa["selected_sbm"],
        drc=sa["non_securitisation_drc"],
        rrao=sa["rrao"],
        selected_sa=sa["selected_scope_standardised_approach_capital"],
        es_f_c=phase5["stress_calibration"].es_f_c,
        es_r_c=phase5["stress_calibration"].es_r_c,
        es_r_s=phase5["stress_calibration"].es_r_s,
        phase5_reduced_set_coverage=(
            phase5["stress_calibration"].reduced_set_diagnostic.average_ratio
        ),
        rfet_results=rfet_results,
        reduced_set_audit_status=reduced_set_rfet_audit(phase6["results"])[
            "audit_status"
        ],
        pla_zones=pla_zones,
        backtesting_statuses=backtesting_statuses,
        desk_diagnostics=desk_diagnostics,
        desk_routes=desk_routes,
        imcc=imcc.simulated_selected_imcc,
        ses=ses.simulated_selected_ses,
        final_total_status=routing.final_total_status,
        us_proposal_status=_us_proposal_status(),
        unresolved_findings_count=_unresolved_findings_count(),
    )


def _close(actual: float, expected: float, tolerance: float = 1e-9) -> bool:
    return abs(actual - expected) <= tolerance * max(1.0, abs(expected))


def validate_release_snapshot(snapshot: ReleaseValidationSnapshot) -> dict[str, bool]:
    return {
        "SA regression": all(
            [
                _close(snapshot.selected_sbm, EXPECTED["selected_sbm"]),
                _close(snapshot.drc, EXPECTED["drc"]),
                _close(snapshot.rrao, EXPECTED["rrao"]),
                _close(snapshot.selected_sa, EXPECTED["selected_sa"]),
            ]
        ),
        "IMA ES regression": all(
            [
                _close(snapshot.es_f_c, EXPECTED["es_f_c"]),
                _close(snapshot.es_r_c, EXPECTED["es_r_c"]),
                _close(snapshot.es_r_s, EXPECTED["es_r_s"]),
                _close(
                    snapshot.phase5_reduced_set_coverage,
                    EXPECTED["phase5_reduced_set_coverage"],
                ),
            ]
        ),
        "RFET regression": snapshot.rfet_results
        == {
            "RF_GIRR_USD_5Y_RATE": (
                "PASS",
                "ROUTE_1",
                "ES_CANDIDATE_PENDING_REAL_DATA_VALIDATION",
            ),
            "RF_EQUITY_SPX_SPOT": (
                "PASS",
                "ROUTE_2",
                "ES_CANDIDATE_PENDING_REAL_DATA_VALIDATION",
            ),
            "RF_EQUITY_SPX_VOL_1Y": (
                "FAIL",
                "NONE",
                "NMRF_CANDIDATE",
            ),
            "RF_FX_EURUSD_SPOT": (
                "FAIL",
                "NONE",
                "NMRF_CANDIDATE",
            ),
            "RF_FX_EURUSD_VOL_1Y": (
                "PASS",
                "ROUTE_1",
                "ES_CANDIDATE_PENDING_REAL_DATA_VALIDATION",
            ),
        }
        and snapshot.reduced_set_audit_status == "REDUCED_SET_RFET_MECHANICS_FAIL",
        "PLA/backtesting regression": snapshot.pla_zones
        == {"TD-RATES": "GREEN", "TD-EQUITY": "GREEN", "TD-FX": "RED"}
        and all(
            statuses == {0.975: "PASS", 0.99: "PASS"}
            for statuses in snapshot.backtesting_statuses.values()
        )
        and snapshot.desk_diagnostics
        == {
            "TD-RATES": "SIMULATED_IMA_TEST_GATE_PASS",
            "TD-EQUITY": "SIMULATED_IMA_TEST_GATE_PASS",
            "TD-FX": "SIMULATED_SA_FALLBACK_REQUIRED",
        }
        and threshold_status(0.99, 12) == "PASS"
        and threshold_status(0.99, 13) == "BREACH"
        and threshold_status(0.975, 29) == "PASS"
        and threshold_status(0.975, 30) == "BREACH",
        "IMCC/SES regression": _close(snapshot.imcc, EXPECTED["imcc"])
        and _close(snapshot.ses, EXPECTED["ses"])
        and snapshot.desk_routes
        == {
            "TD-RATES": "SIMULATED_IMA_BRANCH",
            "TD-EQUITY": "SIMULATED_IMA_BRANCH",
            "TD-FX": "SIMULATED_SA_FALLBACK",
            "TD-CREDIT": "SELECTED_SA_ONLY",
        }
        and snapshot.final_total_status == "NOT_CALCULATED",
        "U.S. crosswalk status": snapshot.us_proposal_status
        == "PROPOSED / CROSSWALK ONLY",
        "Claim audit": snapshot.final_total_status == "NOT_CALCULATED"
        and snapshot.unresolved_findings_count >= 6,
    }


def format_release_summary(
    snapshot: ReleaseValidationSnapshot, checks: dict[str, bool]
) -> str:
    lines = [
        "FRTB V2 RELEASE VALIDATION",
        "",
        f"SA regression: {'PASS' if checks['SA regression'] else 'FAIL'}",
        f"IMA ES regression: {'PASS' if checks['IMA ES regression'] else 'FAIL'}",
        f"RFET regression: {'PASS' if checks['RFET regression'] else 'FAIL'}",
        "PLA/backtesting regression: "
        f"{'PASS' if checks['PLA/backtesting regression'] else 'FAIL'}",
        f"IMCC/SES regression: {'PASS' if checks['IMCC/SES regression'] else 'FAIL'}",
        f"U.S. crosswalk status: {snapshot.us_proposal_status}",
        f"Claim audit: {'PASS' if checks['Claim audit'] else 'FAIL'}",
        "",
        f"Selected-scope SA: {snapshot.selected_sa:.10f}",
        f"IMCC mechanics: {snapshot.imcc:.10f}",
        f"SES mechanics: {snapshot.ses:.10f}",
        f"Final bank-wide aggregate: {snapshot.final_total_status}",
        f"Open findings: {snapshot.unresolved_findings_count}",
        "",
        f"Overall: {'PASS' if all(checks.values()) else 'FAIL'}",
    ]
    return "\n".join(lines)


def main() -> int:
    snapshot = collect_release_snapshot()
    checks = validate_release_snapshot(snapshot)
    print(format_release_summary(snapshot, checks))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
