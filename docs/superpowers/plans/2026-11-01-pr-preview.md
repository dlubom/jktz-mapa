# PR Preview Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Provide complete PR ZIPs and a selected-PR GitHub Pages preview.
**Architecture:** Read-only PR builds and a separate trusted Pages publisher in a preview repository.
**Tech Stack:** Python standard library, existing Node/GDAL build, GitHub Actions/Pages.
**Spec:** docs/superpowers/specs/2026-11-01-pr-preview-design.md

## Global Constraints

Production publishing and pages-state are unchanged. Source changes use PRs. Complete source catalogues and browser checks remain mandatory. ZIP retention is 15 days. The selected preview is limited to one open PR targeting main; deployment requires unchanged head/base/merge identity.

## Review Focus

- Stale/closed/conflicted PR must not replace the selected preview.
- Unsafe paths, symlinks and incomplete file inventories must fail before publication.
- Untrusted build code receives no publication credentials and cannot supply its own trusted identity.
- Relative URLs must work at /jktz-mapa-preview/ and locally.
- Production and its ledger must remain untouched by preview automation.

### Task 1: Complete portable bundle

Files: scripts/preview.py, scripts/preview-server.py, tests/test_preview.py, .github/workflows/ci.yml.
- [ ] Write failing tests for complete package, identity, checksums, unsafe assets and local HTTP.
- [ ] Run tests and observe missing implementation.
- [ ] Implement deterministic bundle, launcher, identity and validation; upload flat files and write Actions summary.
- [ ] Run Python and Node tests; build with existing generated data; commit.

### Task 2: Selected-PR Pages workflow

Files: .github/preview-repository/preview.yml, scripts/preview.py, tests/test_preview.py, tests/browser.mjs.
- [ ] Write failing tests for PR identity, stale/closed/conflicted candidates, and workflow privilege boundaries.
- [ ] Implement trusted resolve/verify stages and isolated build/deploy jobs; allow browser acceptance under the preview prefix.
- [ ] Verify workflows, tests and three-browser acceptance; commit.

### Task 3: Configure and verify delivery

Files: README.md, AGENTS.md, docs/PR_PREVIEW.md.
- [ ] Document download/run/select-PR workflow and main exceptions.
- [ ] Review changes independently; resolve findings and open source PR.
- [ ] Initialize preview repository with reviewed workflow/helper; configure Pages and protect main.
- [ ] Run source PR CI and selected-PR publication; verify downloaded bundle, public manifest, map, source main protection and production identity.
