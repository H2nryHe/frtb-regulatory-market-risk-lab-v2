from __future__ import annotations

import csv
import datetime as dt
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REGISTER = REPO_ROOT / "regulatory" / "source_register.yaml"
PARAMETER_CROSSWALK = REPO_ROOT / "regulatory" / "parameter_crosswalk.csv"

BIS_SOURCE_IDS = {
    "BIS_MAR20",
    "BIS_MAR21",
    "BIS_MAR22",
    "BIS_MAR23",
    "BIS_MAR30",
    "BIS_MAR31",
    "BIS_MAR32",
    "BIS_MAR33",
}
US_SOURCE_IDS = {"FED_2026_PRESS_RELEASE", "FED_2026_PROPOSAL_DETAILS"}

PARAMETER_COLUMNS = [
    "parameter_id",
    "component",
    "parameter_name",
    "value",
    "unit",
    "source_id",
    "source_paragraph_or_table",
    "effective_date",
    "implementation_status",
    "notes",
]


def load_register() -> dict:
    with SOURCE_REGISTER.open() as handle:
        return yaml.safe_load(handle)


def git_lines(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def public_files() -> list[Path]:
    paths = git_lines("ls-files", "--cached", "--others", "--exclude-standard")
    return [REPO_ROOT / path for path in paths]


def source_by_id(register: dict) -> dict[str, dict]:
    return {source["source_id"]: source for source in register["sources"]}


def test_source_register_exists() -> None:
    assert SOURCE_REGISTER.is_file()


def test_required_official_sources_exist() -> None:
    sources = source_by_id(load_register())
    assert BIS_SOURCE_IDS <= sources.keys()
    assert US_SOURCE_IDS <= sources.keys()


def test_source_domains_are_official() -> None:
    sources = source_by_id(load_register())
    for source_id in BIS_SOURCE_IDS:
        assert urlparse(sources[source_id]["url"]).netloc == "www.bis.org"
    for source_id in US_SOURCE_IDS:
        assert urlparse(sources[source_id]["url"]).netloc == "www.federalreserve.gov"


def test_retrieval_dates_are_iso_dates() -> None:
    for source in load_register()["sources"]:
        assert dt.date.fromisoformat(source["retrieved_date"])


def test_basel_sources_identify_project_role() -> None:
    sources = source_by_id(load_register())
    for source_id in BIS_SOURCE_IDS:
        assert sources[source_id]["project_role"].strip()
        assert sources[source_id]["relevant_sections"]


def test_us_source_status_is_explicitly_proposal_based() -> None:
    sources = source_by_id(load_register())
    statuses = " ".join(sources[source_id]["status"] for source_id in US_SOURCE_IDS).lower()
    notes = " ".join(sources[source_id]["notes"] for source_id in US_SOURCE_IDS).lower()
    assert "proposal" in statuses
    assert "proposal" in notes


def test_project_claim_note_disclaims_production_use() -> None:
    note = load_register()["project"]["claim_note"].lower()
    assert "educational" in note
    assert "not a production" in note
    assert "not" in note and "compliance claim" in note


def test_parameter_crosswalk_has_required_columns() -> None:
    with PARAMETER_CROSSWALK.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == PARAMETER_COLUMNS


def test_no_phase0_parameter_marked_implemented() -> None:
    with PARAMETER_CROSSWALK.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    phase0_rows = [row for row in rows if row["component"].lower().startswith("phase0")]
    assert all(row["implementation_status"] != "IMPLEMENTED" for row in phase0_rows)


def test_private_control_files_are_ignored() -> None:
    ignored = git_lines(
        "check-ignore",
        "-v",
        "PROJECT_FRTB_V2_SPEC.md",
        "FRTB_V2_STATUS.md",
        "local_frtb_v2_baseline/",
    )
    assert len(ignored) == 3


def test_private_control_files_are_not_tracked() -> None:
    tracked = git_lines("ls-files", "PROJECT_FRTB_V2_SPEC.md", "FRTB_V2_STATUS.md")
    assert tracked == []


def test_local_baseline_directory_is_not_public() -> None:
    public = [path.relative_to(REPO_ROOT).as_posix() for path in public_files()]
    assert not any(path.startswith("local_frtb_v2_baseline/") for path in public)


def test_no_local_absolute_path_in_public_files() -> None:
    leaked_path = "/Users/" + "linruihe/"
    for path in public_files():
        if path.is_file():
            assert leaked_path not in path.read_text(errors="ignore"), path


def test_no_public_file_overclaims_status() -> None:
    fragments = [
        "regulatory " + "compliant",
        "basel " + "compliant",
        "frtb " + "compliant",
        "fed " + "compliant",
        "federal reserve " + "compliant",
        "occ " + "compliant",
        "fdic " + "compliant",
        "approved " + "by",
        "regulator " + "approved",
        "production " + "bank",
        "production " + "capital engine",
        "supervisory " + "approval",
    ]
    for path in public_files():
        if path.is_file():
            text = " ".join(path.read_text(errors="ignore").lower().split())
            denial = "not a regulatory-compliance or production " + "capital engine"
            text = text.replace(denial, "")
            phase8_denial = (
                "it is not an institutional modellability determination, "
                "supervisory "
                "approval, or a complete regulatory capital calculation"
            )
            text = text.replace(phase8_denial, "")
            assert not any(fragment in text for fragment in fragments), path
