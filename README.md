# Sto-Sim Test Dashboard

An interactive, shareable overview of Sto-Sim's automated test suite (Playwright E2E +
Vitest unit tests): a donut chart of test cases by category, with a searchable,
drill-down list of every test case.

Live version (once GitHub Pages is enabled on this repo): `https://<user>.github.io/<repo>/`

## How it's structured

```
index.html              the dashboard — loads data/test-cases.json + data/history.json at runtime
data/test-cases.json    the test-case data. This is the file you replace to update the dashboard.
data/history.json       append-only log of {date, files, tests} per update, for the
                        "Last updated" line and its change summary. Maintained by extract_tests.py.
scripts/extract_tests.py  regenerates data/test-cases.json + data/history.json from a local Sto-Sim checkout
```

The dashboard never has data baked into it — it always reads `data/test-cases.json`
over HTTP when the page loads. That means **updating the dashboard is just replacing
one file**, no build step, no coding required.

## Updating the test data

**Option A — regenerate from a Sto-Sim checkout (recommended):**

```bash
python scripts/extract_tests.py /path/to/your/Sto-Sim/checkout
```

This re-scans the repo's test files (`apps/api/test`, `apps/web/e2e`,
`apps/web/e2e-oidc`, `apps/web/src`, `packages/core/test`, `scripts`), extracts every
`test(...)` / `it(...)` name, categorizes each file, and overwrites
`data/test-cases.json`. Commit and push the updated file (or push straight to GitHub
via the web UI — see below).

**Option B — replace the file directly on GitHub (no local setup needed):**

1. Open `data/test-cases.json` in this repo on github.com
2. Click the pencil (edit) icon, or drag a new file onto the file list to replace it
3. Commit directly to `main`

GitHub Pages serves the new file immediately — no rebuild step. Reload the page to
see the update.

## Data format

`data/test-cases.json` is a plain array, one entry per test file:

```json
[
  {
    "file": "apps/web/e2e/kopieren.spec.ts",
    "category": "UI & Bedienung",
    "kind": "e2e (Playwright)",
    "tests": [
      { "name": "Kopie behält das Planbild — auch nachdem das Original gelöscht wurde", "modifier": null }
    ]
  }
]
```

- `file` — path shown in the dashboard, purely for display (doesn't need to resolve to a real path).
- `category` — any string. The dashboard derives the donut chart, legend, colors and
  percentages from whatever categories appear here — no separate config to keep in sync.
- `kind` — free text, used for the type filter and the E2E/Unit split at the top.
- `tests[].name` — the test case description.
- `tests[].modifier` — `"skip"`, `"only"`, `"todo"`, etc., or `null`. Shown as a small tag.

Categorization rules for `extract_tests.py` (which pattern maps to which category) live
in the `categorize()`/`kind_of()` functions in that script — this project's own
categories, not meant to generalize to other repos.

An entry may also carry `"dashboardExempt": true` — used for the `.github/workflows`
CI checks the client asked to have listed. These stay out of the stat tiles, donut
chart, kind-bar and Excel export, but remain searchable in the "Test case list" panel
(see the hand-curated `WORKFLOW_CHECKS` list in `extract_tests.py`).

`data/history.json` is a plain array, oldest first:

```json
[{ "date": "2026-08-26", "files": 133, "tests": 1385 }]
```

Counts here are dashboard-only (`dashboardExempt` entries excluded), so they match the
stat tiles. `extract_tests.py` updates it on every run — re-running the same day edits
that day's entry in place rather than adding a duplicate.

## Viewing it locally

Because the dashboard fetches `data/test-cases.json`, opening `index.html` directly
(`file://`) will fail (browsers block `fetch` for local files). Serve the folder over
HTTP instead, e.g.:

```bash
python -m http.server 8000
```

then open `http://localhost:8000`.

## Publishing on GitHub Pages

Settings → Pages → Source: **Deploy from a branch** → Branch: `main`, folder `/ (root)`.
Save, wait ~1 minute, then the URL shown there is live.

## Status

This is a **static snapshot** of what test cases exist in the source code — not a live
test-run result (pass/fail). That's a separate, larger project (would need CI run data,
e.g. from GitHub Actions).
