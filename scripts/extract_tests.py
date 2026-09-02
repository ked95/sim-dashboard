# -*- coding: utf-8 -*-
"""
Extracts automated test cases from a Sto-Sim checkout and writes them to
data/test-cases.json for the dashboard (index.html) to load.

Usage:
    python scripts/extract_tests.py [path-to-sto-sim-checkout]

If no path is given, it defaults to ../../StoSim/Sto-Sim relative to this
script (adjust DEFAULT_ROOT below if your checkout lives elsewhere).
"""
import datetime
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_ROOT = os.path.normpath(os.path.join(REPO_DIR, "..", "StoSim", "Sto-Sim"))
OUT_PATH = os.path.join(REPO_DIR, "data", "test-cases.json")
HISTORY_PATH = os.path.join(REPO_DIR, "data", "history.json")

ROOT = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT

DIRS = [
    "apps/api/test",
    "apps/web/e2e",
    "apps/web/e2e-oidc",
    "apps/web/src",
    "packages/core/test",
    "scripts",
]

TEST_RE = re.compile(
    r"\b(?:test|it)(?:\.(only|skip|todo|fixme|fail|slow))?\s*\(\s*(['\"`])((?:\\.|(?!\2).)*)\2"
)


def kind_of(rel):
    if "/e2e/" in rel or "/e2e-oidc/" in rel:
        return "e2e (Playwright)"
    if rel.startswith("apps/api/"):
        return "unit (Vitest, API)"
    if rel.startswith("packages/core/"):
        return "unit (Vitest, Core)"
    if rel.startswith("apps/web/src/"):
        return "unit (Vitest, Web)"
    return "unit (Vitest)"


def categorize(rel):
    if "/e2e/" in rel or "/e2e-oidc/" in rel:
        return "E2E Tests (Playwright)"
    if rel.startswith("apps/api/"):
        return "API Integration Tests (Vitest + Supertest)"
    if rel.startswith("packages/core/"):
        return "Core Unit Tests (Vitest)"
    if rel.startswith("apps/web/src/"):
        return "Web Unit Tests (Vitest)"
    return "Repo Tooling Tests (Vitest)"


# Client-requested addition: surface all four .github/workflows files alongside the test
# files — including in the dashboard's stat tiles, donut chart, kind-bar and Excel export,
# not just the searchable list. Curated by hand rather than parsed from the YAML: most
# steps in these workflows are infra (checkout, setup-node, npm ci, prisma generate)
# rather than checks worth showing to a client — those are skipped, only the named,
# meaningful steps are listed.
WORKFLOW_CHECKS = [
    {
        "file": ".github/workflows/ci.yml",
        "category": "Git Workflows",
        "kind": "CI check (GitHub Actions)",
        "tests": [
            {"name": "adr:check", "modifier": None},
            {"name": "typecheck", "modifier": None},
            {"name": "build", "modifier": None},
            {"name": "npm test (unit + API)", "modifier": None},
        ],
    },
    {
        "file": ".github/workflows/e2e-nightly.yml",
        "category": "Git Workflows",
        "kind": "CI check (GitHub Actions)",
        "tests": [
            {"name": "E2E suite (Playwright, nightly)", "modifier": None},
            {"name": "API integration tests (nightly)", "modifier": None},
        ],
    },
    {
        "file": ".github/workflows/deploy-dev.yml",
        "category": "Git Workflows",
        "kind": "CI check (GitHub Actions)",
        "tests": [
            {"name": "Azure Login (OIDC)", "modifier": None},
            {"name": "Build image in ACR", "modifier": None},
            {"name": "Apply DB schema (optional)", "modifier": None},
            {"name": "Update Container App", "modifier": None},
        ],
    },
    {
        "file": ".github/workflows/version-bump.yml",
        "category": "Git Workflows",
        "kind": "CI check (GitHub Actions)",
        "tests": [
            {"name": "Version bump (patch increment)", "modifier": None},
        ],
    },
]


# Client-requested "last updated" + change summary on the dashboard itself. The page is
# static and has no git access, so it needs its own tiny append-only log to diff against.
def load_history():
    if os.path.isfile(HISTORY_PATH):
        with open(HISTORY_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def update_history(files, tests):
    today = datetime.date.today().isoformat()
    history = load_history()
    # Re-running the same day updates today's entry in place instead of piling up duplicates;
    # the diff baseline is still the last *different* day's entry.
    if history and history[-1]["date"] == today:
        previous = history[-2] if len(history) >= 2 else None
        history[-1] = {"date": today, "files": files, "tests": tests}
    else:
        previous = history[-1] if history else None
        history.append({"date": today, "files": files, "tests": tests})
    with open(HISTORY_PATH, "w", encoding="utf-8") as fh:
        json.dump(history, fh, ensure_ascii=False, indent=2)
    return previous


def find_test_files(root):
    files = []
    for d in DIRS:
        full = os.path.join(root, d.replace("/", os.sep))
        if not os.path.isdir(full):
            continue
        for dirpath, dirnames, filenames in os.walk(full):
            dirnames[:] = [dn for dn in dirnames if dn != "node_modules"]
            for fn in filenames:
                if re.search(r"\.(test|spec)\.(ts|tsx|mjs)$", fn):
                    rel = os.path.relpath(os.path.join(dirpath, fn), root).replace("\\", "/")
                    files.append(rel)
    return files


def main():
    if not os.path.isdir(ROOT):
        print(f"Sto-Sim checkout not found at: {ROOT}")
        print("Pass the path explicitly: python scripts/extract_tests.py <path>")
        sys.exit(1)

    result = []
    for rel in find_test_files(ROOT):
        full = os.path.join(ROOT, rel.replace("/", os.sep))
        with open(full, encoding="utf-8") as fh:
            content = fh.read()
        names = [{"name": m.group(3), "modifier": m.group(1)} for m in TEST_RE.finditer(content)]
        if not names:
            continue
        result.append({
            "file": rel,
            "category": categorize(rel),
            "kind": kind_of(rel),
            "tests": names,
        })

    for entry in WORKFLOW_CHECKS:
        if not os.path.isfile(os.path.join(ROOT, entry["file"].replace("/", os.sep))):
            print(f"Warning: {entry['file']} not found — WORKFLOW_CHECKS may be stale")
            continue
        result.append(entry)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    total_tests = sum(len(f["tests"]) for f in result)
    print(f"Wrote {OUT_PATH}")
    print(f"{len(result)} files, {total_tests} test cases")

    previous = update_history(len(result), total_tests)
    print(f"Wrote {HISTORY_PATH}")
    if previous:
        print(
            f"Since {previous['date']}: "
            f"{len(result) - previous['files']:+d} files, "
            f"{total_tests - previous['tests']:+d} test cases"
        )


if __name__ == "__main__":
    main()
