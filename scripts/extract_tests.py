# -*- coding: utf-8 -*-
"""
Extracts automated test cases from a Sto-Sim checkout and writes them to
data/test-cases.json for the dashboard (index.html) to load.

Usage:
    python scripts/extract_tests.py [path-to-sto-sim-checkout]

If no path is given, it defaults to ../../StoSim/Sto-Sim relative to this
script (adjust DEFAULT_ROOT below if your checkout lives elsewhere).
"""
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_ROOT = os.path.normpath(os.path.join(REPO_DIR, "..", "StoSim", "Sto-Sim"))
OUT_PATH = os.path.join(REPO_DIR, "data", "test-cases.json")

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

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    total_tests = sum(len(f["tests"]) for f in result)
    print(f"Wrote {OUT_PATH}")
    print(f"{len(result)} files, {total_tests} test cases")


if __name__ == "__main__":
    main()
