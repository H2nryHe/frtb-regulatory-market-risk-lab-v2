from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path


def public_candidate_files(repo_root: Path, excluded_globs: tuple[str, ...] = ()) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=True,
    )
    paths: list[Path] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        if any(fnmatch.fnmatch(line, pattern) for pattern in excluded_globs):
            continue
        path = repo_root / line
        if path.is_file():
            paths.append(path)
    return paths


def scan_public_text(
    repo_root: Path,
    needle: str,
    *,
    case_sensitive: bool = True,
    excluded_globs: tuple[str, ...] = (),
) -> list[tuple[Path, int, str]]:
    expected = needle if case_sensitive else needle.lower()
    matches: list[tuple[Path, int, str]] = []
    for path in public_candidate_files(repo_root, excluded_globs):
        for line_number, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
            haystack = line if case_sensitive else line.lower()
            if expected in haystack:
                matches.append((path, line_number, line))
    return matches


def format_matches(matches: list[tuple[Path, int, str]], repo_root: Path) -> str:
    return "\n".join(
        f"{path.relative_to(repo_root).as_posix()}:{line_number}:{line}"
        for path, line_number, line in matches
    )
