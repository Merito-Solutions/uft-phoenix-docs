# Usage Guide

UFT Phoenix converts OpenText UFT One (formerly Micro Focus UFT / QTP)
VBScript GUI tests to UFT Python. There are exactly **two conversion
paths**, with nothing in between:

- **Local filesystem** — convert UFT test directories stored on disk (local
  folders or UNC shares).
- **Whole ALM project** — convert an entire ALM domain/project, all or
  nothing. There is no folder- or count-scoped ALM *mode*; the scope is reduced
  only by explicitly parking tests out of it — by id (`--alm-exclude-test-id`)
  or by glob against their ALM folder path, name or id (`--include` /
  `--exclude`).

ALM conversion is whole-project because a UFT test that calls another test's
shareable ("reusable") action forms a call chain that must run under **one**
script engine: a callee action executes inside the *caller's* engine, so a
mixed VBScript/Python chain fails at runtime. Converting only part of a
project would both leave mixed-engine chains behind and miss inbound
references from tests outside the subset. Converting the whole project keeps
every chain uniform Python. Cross-test shareable actions are preserved by
**native reference reconstruction** (see below), not by copying.

Most users drive Phoenix through the Migration Console (`uft-migrate-gui`,
documented field-by-field in [gui_field_guide.md](gui_field_guide.md)); this
guide covers the `uft-migrate` command line the console builds on.

`scan`/`analyze`, `convert`, `run`, `validate` and `summarize` print the project
root at start (`PROJECT_ROOT:` — the folder the command was launched from) and
write their artifacts to `out\<run id>` under it. `--output-root` does **not**
move the run folder: on `convert`/`run` it relocates the converted output
(default `out\<run id>\converted`), and on the other commands a scratch folder
(default `out\<run id>\artifacts`). Launch from a folder you can write to —
never `C:\Windows\System32`, and never the install folder, which an upgrade or
an uninstall clears.

With `--run-id` omitted, a filesystem run gets a UTC timestamp id
(`YYYYMMDD_HHMMSS`), while an ALM run is keyed on `<Domain>-<Project>` from the
`--domain`/`--project` you passed — so repeat ALM runs re-enter the same folder,
with the resume and anti-clobber machinery that implies, unless `--run-id` is
given. The name is normalised: a domain written in capitals (letters, digits and
underscores only) is title-cased, and any character other than a letter, digit,
`-`, `_` or `.` becomes an underscore, so the domain `MY_DOMAIN` and project
`MY_PROJECT` run in `out\My_Domain-MY_PROJECT`. `doctor`, `restore` and
`diagnostics` sit outside this entirely: all three are dispatched before the
banner and the run-folder creation, so none of them prints `PROJECT_ROOT:` or
creates a run folder.

`summarize` is the exception among those: it consumes an existing run's
reports and links them with relative paths, so with no `--run-id` it writes the
executive summary **into the most recent run folder** rather than creating one
of its own (only when there is no previous run does it fall back to a new
timestamped folder). One guard governs that default: when the most recent run
folder already holds an `executive_summary.json`, `.html` or `.md`, bare
`summarize` writes nothing — it prints `"status": "refused"` and exits 2 rather
than overwrite an approval document the run itself wrote from evidence
`summarize` cannot rebuild. Only `run` (filesystem and `--alm`) writes an
executive summary, so bare `summarize` after any `run` is refused; the default
above is what applies to `scan`, `convert` and ALM-analysis folders. Passing
`--run-id` bypasses the guard: `summarize --run-id <that run>` overwrites the
approval document the run wrote with one rebuilt from the report JSON alone. To
keep the original, pass a **new** `--run-id` together with
`--scan-json`/`--convert-json`/`--validation-json` pointing at the run's
reports — the rebuilt summary's detail-report links are relative and will not
open from the new folder, so read the details in the original run folder.

## Commands

| Command | Purpose |
| --- | --- |
| `doctor` | Preflight the environment: Python, pywin32, UFT install, IronPython runtime completeness, ALM client, output write access, optional live ALM login. Run this first on every new machine. |
| `scan` / `analyze` | Discover tests, inventory blockers/warnings per file, build the dependency graph, produce readiness reports. No changes are made. |
| `convert` | Convert tests (filesystem or ALM). ALM mode: download → convert → AOM build → optional upload/verify → optional Test Lab run. |
| `run` | Closed loop in one pass. Filesystem: scan → convert → validate → summarize. With `--alm`: the same whole-project ALM conversion `convert --alm` performs, plus the executive summary (`ready_for_approval`, `alm_status`). This is the command the Migration Console's **Run Conversion** button issues. |
| `validate` | Post-conversion checks (Python syntax, UFT method-call rules) on a converted tree. |
| `summarize` | Build the executive summary from existing report JSONs. |
| `diagnostics` | `diagnostics collect` writes a support bundle for Merito support under `out\_support\`: the per-process logs, the environment and an allow-list of the run's files, with secrets removed. Nothing is sent anywhere. `diagnostics triage` reads a bundle, or a run folder, and prints a first-look report. See *Collecting diagnostics* below. |
| `restore` | Restore ALM tests to their original pre-conversion payloads from a prior run's frozen snapshots (`out\<RUN_ID>\alm_aom_work\alm_rollback\test_<id>_source`). `out\<RUN_ID>\alm_aom_work\test_<id>_source` is read only as a legacy fallback — it is the live staging tree, which convert re-downloads on every attempt, so after a second run it holds the *converted* payload. A snapshot that already contains Python (`Script.pts` with no `Script.mts`) is refused rather than restored, and so is an incomplete one — it must hold one `.usr`, a `Test.tsp` and every local action script that `.usr` names, because a restore deletes the server's scripts first. Snapshots are frozen by any run that converts a downloaded test for real — real conversions, and also **deep** ALM analysis (`--analysis-depth deep`), which AOM-builds every test. A *standard* analysis and an `--upload --dry-run` gate rehearsal freeze nothing, so those run folders leave nothing for `--from-run` to use. `--wave <wave>` restores instead from the copy that conversion wave froze before it changed the test (`alm_rollback\waves\<wave>\test_<id>\payload`) and records the restore in the run's journal; a test a wave may have left half-written is refused without it, and the refusal prints the `--wave` command for each such test, callers first. `--wave` naming a finished wave is refused for a test that a later wave has written since — that copy is older than what ALM holds — and the refusal prints the command for the later wave's copy instead. `--accept-current-state` and `--abandon-wave` make no ALM change and need no ALM arguments — see [troubleshooting.md](troubleshooting.md) § *Native crashes and interrupted ALM conversions*. `restore` is refused while another Phoenix process works in that run folder. |

## Common options (scan, analyze, convert, run, validate, summarize)

`--config` (config file: JSON; YAML only in a source install) ·
`--source-root` (repeatable) ·
`--output-root` · `--uft-object-model` · `--custom-uft-method` (repeatable) ·
`--include` / `--exclude` (glob patterns, repeatable) ·
`--exclude-test-path` (filesystem conversion-scope exclusion, repeatable) ·
`--strictness strict|standard|permissive` (`--strict` is shorthand) ·
`--report-format json|md|html|both` · `--verbose` · `--max-errors` ·
`--threads` · `--emit-dependency-graph` ·
`--run-id` · `--resume` · `--failed-only`

`--report-format both` emits JSON, Markdown, and HTML artifacts.
`--max-errors` is inert: it is accepted for compatibility and stops nothing.

If `--config` is not given, Phoenix loads `uft-migrate.json` (or
`uft-migrate.yaml` / `uft-migrate.yml`) from the folder the command was launched
from, when one exists, and the run does not say which file it loaded. The
installed product reads JSON only: a `.yaml`/`.yml` file stops the run with
"YAML config requested but PyYAML is not installed", because the offline
package does not include PyYAML. The Migration Console's current directory is
the folder it was launched from — for the Start Menu shortcut, your user
profile folder. Rename or remove a stray file there to get the defaults.

`--resume` continues an **interrupted** run with the same run id and otherwise
the same command line. It is accepted only while that run's checkpoint is still
`running`; after a run that failed or was aborted it is refused with exit 2, and
the fix is to re-run with the same run id rather than to add the flag. The
Migration Console has no `--resume` control of its own. When the previous run in
that folder is still interrupted it offers a Resume Previous Run dialog, and
passes the flag for you only if you answer Yes.

`--resume` does not control a whole-project ALM conversion either. Every upload
conversion journals each asset to `resume\alm_test_results.ndjson` in the run
folder, and belongs to a *conversion wave* that lasts until the conversion
finishes or is rolled back. A launch with the same command line — `--run-id`,
`--resume`, `--failed-only` and the value of `--password` aside — continues an
unfinished wave, with or without `--resume`, even after the run's checkpoint
stopped saying `running`. A launch with a different command line closes an
unfinished wave that has not written any test and starts a new one; once the
open wave has written a test, it is refused, naming the options that differ
and the `restore --abandon-wave` command that closes the wave. A conversion
that was cancelled, that stopped, or that a crash ended before recovery could
finish leaves its wave open unless the wave was rolled back; see
[troubleshooting.md](troubleshooting.md) § *Native crashes and interrupted ALM
conversions*. A later conversion in the same run
folder skips an asset when the journal records it uploaded and verified,
nothing recorded after that touched it again, **and** the server still holds
its complete Python payload; the asset is reported `ok`, flagged `resumed`, and
listed under **Carried Forward**. Its record in the reports is the one its
conversion made — findings, structure check, duration and notes, and, when an
earlier attempt of the same conversion wave converted it (a crash relaunch, a
resume), the shared libraries it replaced — kept in `resume\alm_asset_details\`
beside the journal; a journal an earlier Phoenix wrote has none, and the
reports say how many assets that leaves out. No flag turns this on. Because ALM runs
default to the `<Domain>-<Project>` folder, a repeat conversion of the same
project resumes unless you pass a new `--run-id` and run the analysis under
that id first. ALM analysis never resumes and never skips an asset.

A carried-forward test still serves as a callee: its journal record holds the
converted action layout that its callers are retargeted against, so a test that
calls it is converted as usual in the same run. The one exception is a run
folder whose journal an earlier version of Phoenix wrote, before that layout was
recorded. A caller of a test carried forward from such a journal is refused with
"that callee has no conversion record in this run"; see
[troubleshooting.md](troubleshooting.md) for the fix.

`--failed-only` re-processes only the assets that failed previously and
merges the result into the previous run's, so the report still covers the
whole scope. It applies to analysis (`scan`, `analyze`, and the ALM analysis
`convert --alm --dry-run`); whole-project ALM conversion is all-or-nothing
and rejects it.

`doctor`, `restore` and `diagnostics` do not share these options — each defines
its own flag set (see the `doctor` examples below, `restore --help` and
*Collecting diagnostics* below). The only overlap is `--output-root`, which each
declares separately; everything else above, including `--config`,
`--report-format`, `--verbose` and `--run-id`, is rejected by argparse on those
three commands.

## Reading the result (verdict vs. exit code)

Every migration command (`scan`, `analyze`, `convert`, `run`, `validate`,
`summarize`, `restore`) prints a JSON payload on stdout. Three different signals
live in it, they answer different questions, and **only `run` and `summarize`
publish all three**:

| Field | Question it answers | Where it appears |
| --- | --- | --- |
| `go_no_go` | **Is this scope fit to convert?** `no-go` whenever there are scan blockers, unresolved dependency edges or dependency cycles, whenever nothing was assessed (`nothing_assessed: true` — no tests or libraries were discovered), and, on the ALM path, whenever any in-scope asset did not come back `ok`. Identical to the verdict in `scan_report.json` / `scan_report.html` and to the badge the Migration Console shows. | Published by `scan`, `analyze`, `convert` and `run`, including the ALM analysis (`convert --alm --dry-run`) and ALM conversion, and by `summarize` whenever the reports it read carry a verdict (absent when they do not — treat a missing verdict as `no-go`). Not published by `validate`, which assesses an already-converted tree rather than a scope. |
| `status` / `summary.overall_status` | **Did the run clear the selected strictness gate?** Drives the exit code (`0` ok, `2` failed). | Every migration command. |
| `ready_for_approval` | **Can a human sign this conversion off?** The same boolean behind the executive summary's "Ready to approve conversion program" / "Approval pending remediation" badge. It is a strictly **wider** hold than the exit code: it also goes `false` for waived converter blockers and for a scan-only run folder with nothing converted. | `run` and `summarize` (both `--alm` and filesystem run folders) — the two commands that write the executive summary. Equivalent to `approval.ready_for_approval` in `executive_summary.json`. |

On the ALM path `--strictness` is ignored — the ALM converter always runs
strict. `convert --alm`, the `--dry-run` analysis included, prints the ALM
pipeline's own status word — `ok`, `completed-with-errors` or `no-tests`, and,
on any run that is not the read-only analysis (the `--upload --dry-run` gate
rehearsal and the real upload), `preflight-failed` — and exits 2 unless
**every** discovered asset result is `ok`. Out-of-scope assets are not failures
for the verdict but they are non-`ok` results, so an analysis whose only
non-`ok` asset is a skipped API test exits 2 with `go_no_go: "go"` — where
`run --alm` over the same scope exits 0. Gate on `go_no_go`.

`go_no_go`, `status` and `ready_for_approval` are **not** the same thing, and
they diverge in **both** directions:

- **`"status": "ok"`, exit 0, verdict `no-go`.** `--strictness standard` (the
  default) deliberately tolerates scan blockers, and no strictness level folds
  in dependency-graph health. A scan carrying 3 blockers exits 0 while its own
  `scan_report.html` renders the red "Hold conversion approval" badge.
- **Exit 2, verdict `go`.** Under `--strictness strict` a review-required
  finding fails the gate even when nothing blocks conversion — an estate whose
  only findings are `GoTo` lines exits 2 with `go_no_go: "go"` and
  `summary.gate_failures: ["3 scan review-required finding(s) remain."]`.
- **`"status": "ok"`, exit 0, verdict `go`, `ready_for_approval: false`.**
  `standard` (the default) waives converter blockers: the flagged construct is
  **dropped from the published Python** and the run continues. That is a
  strictness decision, so it does not fail the gate and does not move the scan
  verdict — but it is not something a human should sign off unread. It is
  counted in `summary.conversion_waived_blockers`.
- **`summarize`: exit 2 on an ALM run folder, exit 0 on a filesystem one, same
  `no-go`.** An ALM analysis summary folds its verdict into `overall_status`
  (any non-`go` verdict holds approval at every strictness), while a filesystem
  summary's `status` stays the pure strictness gate — so `summarize` over a
  filesystem run whose scan said `no-go` still prints `"status": "ok"` and
  exits 0. Gate on `go_no_go` / `ready_for_approval`, never on `summarize`'s
  exit code.

A test that came back "no actions" / "no convertible actions" is **not** one of
these tolerated cases. It is a real UFT test that produced no converted output
and is still VBScript, so it fails the gate at every strictness: `status`
`failed`, exit 2. On the filesystem path the gate failure reads "N test(s) were
skipped without producing converted output." and the count is
`summary.conversion_unconverted_skips`; on the ALM path the asset carries a
non-`ok` status and appears in the conversion status breakdown.

So **exit 0 does not mean `go`, exit 2 does not mean `no-go`, and neither one
means approvable.** Gate conversion approval on `go_no_go`, treat the exit code
as the strictness gate it is, and gate the human sign-off of a `run` on
`ready_for_approval`. Read the verdicts from the run's report files rather than
piping stdout to `jq` — stdout starts with a `PROJECT_ROOT:` banner line, and
with `--verbose` an ALM run (`convert --alm --dry-run` included) also prints
each migration-log event as its own JSON line before the final payload:

```
uft-migrate scan --source-root C:\UFT\Suite --run-id SUITE_SCAN --report-format both
jq -e '.go_no_go == "go"' out/SUITE_SCAN/scan_report.json

uft-migrate run --source-root C:\UFT\Suite --run-id SUITE_RUN --report-format both
jq -e '.approval.ready_for_approval == true' out/SUITE_RUN/executive_summary.json
```

An ALM run that aborts at the pre-flight gate writes no report set and
therefore prints no `go_no_go` at all (its analysis report set is preserved
untouched). Treat a **missing** verdict as `no-go`; `jq -e '.go_no_go == "go"'`
already fails closed on it. `run --alm` additionally publishes `alm_status`,
the ALM pipeline's own status word — `preflight-failed` for exactly this abort
(the gate refused and **no ALM writes were performed**) — because the
top-level `status` is the readiness rollup and only ever says `failed`.

A real upload that **stopped and stays open** prints no verdict either: its
`status` (and `alm_status`) is `wave-stopped`, or `journal-unwritable`, it
writes no report set, and it exits 2 (see
[troubleshooting.md](troubleshooting.md) § *Native crashes and interrupted ALM
conversions*). When the crash supervisor ends an upload itself — after a
crash it could not recover from, when the conversion process ended without
recording its result, or when it refuses to start one — it prints its own
result: `status` `failed`, an `alm_status` such as `process-crashed`,
`exited-without-result` or `refused`, and a `crash_recovery` block whose
`operator_message` says what happened and what to do next. An upload exits 0
only when the conversion recorded a result whose exit code is 0.

Use `--strictness strict` if you also want the exit code to fail on scan
blockers. `summary.unresolved_edges`, `summary.dependency_cycles` and
`nothing_assessed` explain a filesystem `no-go` that has no blockers behind it,
`metrics.assets_failed` explains an ALM one, and `summary.scan_review_required`
explains a strict exit 2 that has no `no-go` behind it.

## Environment check

```
uft-migrate doctor
uft-migrate doctor --alm-url http://alm:8099/qcbin --username svc.migration
```

Add `--json` for machine-readable output. The ALM password for the live
login check comes from the `UFT_MIGRATE_ALM_PASSWORD` environment variable
(`--password` is accepted too, but a command line is visible to other processes
on the machine). `doctor` also reads `UFT_MIGRATE_ALM_URL` and
`UFT_MIGRATE_ALM_USERNAME` in place of the two flags, and takes no `--domain`
or `--project`: the live check is a login, not a project operation.

`doctor` is the exception to everything in the previous section. It is a
read-only preflight dispatched before the run-folder machinery, so it writes no
run artifacts, prints no `PROJECT_ROOT:` banner, and prints a human-readable
check report unless you pass `--json`. Its `status` values are `ok|warn|fail`
(not `ok|failed`), and it exits **1** when any check fails — 0 otherwise,
warnings included. The checks themselves never exit 2; exit 2 from `doctor`
means argparse rejected the command line, for example an unsupported option
such as `--config`.

## Collecting diagnostics

When Merito support asks for diagnostics, `diagnostics collect` writes a support
bundle; the Migration Console's **Collect Diagnostics…** button, and the Yes of
its *Conversion Failed* dialog, run the same collector, and so does the Start
Menu shortcut *Merito UFT Phoenix Collect Diagnostics*, as `pythonw.exe -m
uft_migrate.diagnostics collect --show-result` started in the launching user's
profile folder. Nothing is sent anywhere: the collector opens no network
connection, creates no COM object, logs in to nothing and writes nothing into a
run folder. You send the zip yourself. What a bundle holds, and what it never
holds, is in [troubleshooting.md](troubleshooting.md) § *Collect diagnostics
for Merito support*.

Run it as `uft-migrate diagnostics …`, or, when `uft-migrate` itself cannot
start, as `python -m uft_migrate.diagnostics …` with the same options:

```
diagnostics collect [--run RUN_ID | --run-dir PATH | --no-run] [--output-root DIR] [--dest DIR]
                    [--days N] [--include-dumps] [--include-failed-tests] [--include-test ID ...]
                    [--keep-names] [--max-mb N] [--list | --show-result] [--json]
diagnostics triage PATH [--json] [--repo DIR] [--compare OLDER_PATH] [--check-secret]
```

For example:

```
uft-migrate diagnostics collect
uft-migrate diagnostics collect --run "Default-Retail_Regression_2026" --days 30
uft-migrate diagnostics collect --no-run --list
uft-migrate diagnostics collect --include-test 12 34 --json
uft-migrate diagnostics triage "C:\support\UFTPhoenix-diagnostics-1.2.0-20261006T101500Z.zip"
uft-migrate diagnostics triage "C:\out\Default-Retail_Regression_2026" --json
```

| Option | Meaning |
| --- | --- |
| `--run`, `--run-dir`, `--no-run` | The run folder to include: a run id under `--output-root`, or a path. Without either, the run the newest run-bound process log names, else the newest folder under `--output-root` that holds a run; `--no-run` collects logs and the environment only. |
| `--output-root` | The folder that holds the run folders (default `out` under the current folder), as for `restore`. |
| `--dest` | Where the bundle is written (default `<output-root>\_support\`, else `%LOCALAPPDATA%\Merito\UFT Phoenix\support\`). |
| `--days` | Days of process logs and Windows crash evidence to include, 1 to 90 (default 30, every process log Phoenix keeps: the Migration Console and the Start Menu shortcut pass no `--days`, so they reach as far back). Collecting deletes no log, but every Migration Console and command start deletes process logs older than 30 days, so past 30 days only Windows' crash evidence is usually left to reach. |
| `--include-dumps` | Also save the crash dumps matched to this run's crashes (at most 3) to the separate `…-EXTRAS-SENSITIVE.zip`. A dump can contain the ALM password. |
| `--include-failed-tests`, `--include-test ID ...` | Also save the scripts of the 5 newest failed tests, or of these ALM test ids (at most 5), to the separate file. |
| `--keep-names` | Keep ALM host, domain, project, user, test, folder and library names instead of replacing them with tokens. |
| `--max-mb` | The largest bundle zip, 5 to 200 MB (default 25); the oldest and least useful files are trimmed first, and each trim is listed in `MANIFEST.json`. |
| `--list` | Print what would be collected, and the extras that exist, and write no bundle (the collector still writes its own process log). |
| `--show-result` | Show the collect in windows, for a start with no console — what the Start Menu shortcut runs: when crash dumps or failed tests' scripts exist for the run, the Migration Console's question about saving them to the separate file (the kinds you already asked for with `--include-dumps` or `--include-failed-tests` are not asked about); a small progress window while it works; then the console's *Diagnostics Saved*, after which the bundle's folder opens, or *Diagnostics Not Collected* with the reason. The JSON document is printed as without it. Not with `--list`. |
| `--json` | Print the result as one JSON document. |

With `--json`, `collect` prints one document at column 0, with no `event` key:
`command` (`diagnostics`), `action` (`collect`), `status` (`ok` or `failed`, or
`cancelled` when the `--show-result` question was answered **Cancel**),
`bundle` (the zip), `folder` (the same files, unzipped, for review), `bytes`,
`files`, `excluded_files`, `dropped_after_scan`, `extras` (the separate file, or
null), `names_map` (the token map, which stays on this PC), `headline` and
`error`. It exits **0** when a bundle was written and **2** when the collector
refused or failed, or nothing was collected because the question was
cancelled — the error names the rule that stopped it, never a value. The exit
codes are the same with `--show-result`.

`diagnostics triage` is the reader Merito support uses; it reads a bundle zip, a
bundle folder, or a run folder of an earlier release, never changes it, and
prints `TRIAGE.md`, the first look a bundle already carries: build and
environment risks, the process tree, the verdict and the failure that caused
it, fault groups, native crashes, discovery, and next steps. `--json` prints the
report as one document; `--compare OLDER_PATH` lists the faults that went away
or appeared since an older bundle; `--repo DIR` shows the code at the bundle's
commit beside each failing frame (it runs `git` in DIR). Triage exits 0 with its
report; when PATH or `OLDER_PATH` cannot be read it prints one JSON document
with `"status": "failed"` and the reason in `error`, and exits 2.

`--check-secret` asks for a value without showing it and names every file of a
bundle zip or bundle folder that holds it, in any letter case and in any of the
forms the redaction masks (raw, JSON-escaped, URL-encoded, XML-escaped, UTF-8 or
UTF-16). That is how a security team can check a bundle for a password or a
server name before it is sent. The value itself is never printed. The answer
does not change the exit code: read the closing *appears in* / *appears
nowhere* line, or, with `--json`, `check_secret.found`, the list of files that
hold the value.

## Filesystem workflows

```
# Analyze a suite
uft-migrate scan --source-root C:\UFT\Suite --report-format both --emit-dependency-graph

# Convert to a new output tree, reusing the prior scan's verdict
uft-migrate convert --source-root C:\UFT\Suite ^
    --scan-report C:\work\out\SUITE_SCAN\scan_report.json --strictness strict

# Full closed loop in one command
uft-migrate run --source-root C:\UFT\Suite --report-format both

# In-place conversion (version-controlled sources only)
uft-migrate convert --source-root C:\UFT\Suite --in-place --overwrite-policy backup

# Validate a converted tree
uft-migrate validate --target-root C:\work\out\SUITE_RUN\converted
```

`--scan-report` does not choose what is converted. It only reuses the earlier
scan's verdict and inventory in the reports; the tests themselves are
rediscovered from `--source-root` (the current directory when you omit it), so
pass the same `--source-root` and the same `--include`/`--exclude`/
`--exclude-test-path` values the scan used.

`--vbs-preservation-mode python-only|comment-block|interleave` controls how
much original VBScript rides along in converted files (`interleave` is ideal
for review phases).

### Taking tests out of scope, and where the drops are reported

`--exclude-test-path <name|path|glob>` (repeatable) marks a filesystem test
**out of scope for this wave**. The files are left untouched on disk; the test
is simply not converted. Matching is anchored, never a substring: a pattern
with no `/`, `*` or `?` matches a **whole path segment**, so
`--exclude-test-path Login` excludes a test named `Login` and every test under
a folder named `Login`, but not `Admin_Login`.

An excluded test produces no row in `convert_report.json` — it was never part
of the wave — so the run headline still reads as a complete conversion. The
conversion narrative is written to **stderr**, one line per dropped or blocked
asset, and that is the only place an over-broad pattern shows up:

```
out of scope: C:\UFT\Suite\Login\Smoke (matched exclusion pattern 'Login')
excluded 4 out-of-scope test(s) from this wave; files left untouched
ignored as a Phoenix artifact, NOT converted: C:\UFT\Suite\Smoke.bak (Phoenix backup of 'Smoke' (folder 'Smoke.bak'))
[Checkout] BLOCKED: 2 blocker(s); no test built
```

Redirect it (`2> convert_drops.log`) on any run where scope matters. The
Migration Console already captures it to `out\<run id>\run_cli_stderr.log`
(`analysis_cli_stderr.log` for the analysis step). Before signing off, check
that the number of excluded tests is the number you intended.

`--exclude-test-path` is applied by **conversion only**. `scan`/`analyze`, and
the scan phase of `run`, still discover and measure an excluded test, so its
blockers stay in `scan_report` and in `go_no_go`. Unlike `--alm-exclude-test-id`
it does not change the analysis verdict; judge the wave's scope from the stderr
narrative above.

The ALM counterpart is `--alm-exclude-test-id` (see "ALM flags on `convert`").

## ALM workflows

`--alm-url`, `--username`, `--domain` and `--project` are **required on every
command that connects to a whole ALM project** — `convert --alm`, `run --alm`
and `restore`. On `convert` and `run` a missing value stops the command with
"Missing required ALM configuration values"; `restore` stops with a `failed`
result naming the missing flags (exit 2) before it connects. Only
`restore --accept-current-state` and `restore --abandon-wave`, which write
nothing to ALM, need none of them. On those commands only the password has an
environment-variable source, `UFT_MIGRATE_ALM_PASSWORD`, and that is the
preferred way to supply it — `--password` works but a command line is visible
to other processes on the machine. The Migration Console collects every connection value field-by-field
and passes the password through the environment variable, never on a command
line ([gui_field_guide.md](gui_field_guide.md)).

### ALM flags on `convert`

ALM conversion is always **whole-project** — the entire domain/project is
converted as one unit. There is no folder- or count-scoped ALM conversion.

It is also always **in-place**: the converted Python is written back into the
existing ALM tests, preserving their ids, links and history. There is no "new
tests" ALM mode — `--convert-mode` and `--confirm-in-place` are accepted on the
command line but ignored once `--alm` is set (the ALM options hard-code in-place
and the in-place confirmation), so the backup you assert with
`--confirm-alm-backup` is the real safety net. `--convert-mode` is live only on
the filesystem path, where `--convert-mode in-place` is the same selector as the
`--in-place` flag shown above.

Connection and target:
`--alm` · `--alm-url` · `--username` · `--password` ·
`--domain` · `--project` · `--alm-test-plan-module-id`

Scope:
`--alm-exclude-test-id` (repeatable) marks an ALM test **out of scope for this
wave**, on the conversion path as well as analysis. The test is left untouched
in ALM, and it does not count against the run's scope-coverage check. Park whole
call chains: if a parked test is called by a test that is still in scope, the
caller cannot rebuild its reference and the pre-flight gate refuses the wave —
park the caller too, or remediate instead. It is the ALM analog of
`--exclude-test-path`, and the Migration Console surfaces it as Step 5's
"Out-of-scope test IDs" parking field.

`--alm-test-plan-module-id` is optional and only affects the report's `td://`
test links: without it each test is named in plain text, with no link. It is
ALM's internal Test Plan module id, stored per project, so look it up for the
project you are converting; find it via the ALM client's **Copy URL** on any
test (the digits in `TestPlanModule-<id>`), or with
`SELECT DISTINCT CSET_CATEGORY FROM COMMON_SETTINGS WHERE CSET_CATEGORY LIKE 'TestPlanModule-%'`
in Site Administration → Database. See [gui_field_guide.md](gui_field_guide.md).

Safety and writes:
`--upload` · `--dry-run` · `--allow-blockers` ·
`--allow-partial-conversion` · `--confirm-alm-backup` ·
`--purge-uft-cache/--no-purge-uft-cache`

`--purge-uft-cache` is the real cache control: it clears UFT's TD_80
test-extraction cache before every run, and again after any run that wrote to
ALM, on the machine Phoenix runs on. Every **other** execution host still needs
`%LOCALAPPDATA%\Temp\TD_80` cleared by hand after a conversion.
`--purge-alm-cache/--no-purge-alm-cache` is accepted for compatibility and does
nothing.

From the Migration Console these are fixed rather than exposed: ALM
**conversion** always uploads, the **Run Analysis** workflow is always the
read-only dry run, the cache purge is always on, and `--allow-blockers` is never
set — a blocked asset makes the pre-flight gate refuse the whole conversion,
with no ALM writes, until you remediate it or park it in Step 5's "Out-of-scope
test IDs" field and re-analyze. The flags above remain available on the CLI as
support/expert levers.

Analysis:
`--analysis-depth standard|deep` — `standard` screens every test in parallel
(`--threads` worker processes, default 10) without building it in UFT (fast
go/no-go filter); `deep` AOM-builds each test serially (single UFT COM
constraint — conversion is serial for the same reason), proving each passing
asset actually converts. **Deep analysis
reports additionally carry the Technical Conversion Breakdown** — counts
measured by the same converter the real conversion runs, per asset and
overall: source/Python line counts, lines needing parentheses added for
Python call syntax, VBScript intrinsic replacements, and descriptive-
programming lines split static vs dynamic. This is the per-construct
evidence behind the go/no-go verdict. Filesystem analysis (`scan`) has no
depth concept and always includes the breakdown — its single mode fully
measures every script.

**What ALM analysis does not look for.** At either depth, an ALM analysis
reports what the converter and the Python syntax gate find. The
construct-review findings the filesystem `scan` raises — checkpoints and
`OutputValue`, the `GetROProperty`/`GetTOProperty`/`SetTOProperty` family,
`.Object`, `Scripting.Dictionary`, `RegExp`, `Environment`, `OptionalStep`,
recovery scenarios — are not raised on the ALM path, so an ALM project full of
them can still report `go`. Search your own source for those constructs if you
need them inventoried before a wave.

Execution verification (CLI-only support levers — not exposed in the console):
`--run-via-alm` (ALM Test Lab) · `--alm-test-lab-folder` ·
`--alm-test-set-name` · `--alm-host` · `--uft-timeout`

**There is no local-execution lever.** `--run-uft` was removed when the AOM
conversion path became canonical. It is still accepted so that it can be
refused *by name* instead of silently doing nothing — passing it fails the
command with exit 2 and a `status: failed` payload, on both the ALM and the
filesystem path. Nothing is converted, uploaded, or run.

**How to actually verify a converted test runs.** Conversion never proves
execution, and neither does any flag on this page; the pipeline's own
post-upload verification proves the *bytes* on the server are correct, not
that the test passes. Do one of:

1. Open the converted test in UFT One and run it. This is the check that
   applies to both paths and the only one available for filesystem
   conversions.
2. Run it from ALM Test Lab — either from your existing test sets in the ALM
   client (the normal path, and the only one available to a Migration Console
   operator, since the console has no execution control at
   all), or via `--run-via-alm` when a support engineer needs the run
   captured in the Phoenix report. Test Lab execution needs an **active,
   unlocked interactive desktop** on the execution host.

### The safety model (read before your first upload)

1. **Nothing writes to ALM without `--upload`.**
2. **`--dry-run` first — but know which dry run you asked for.**
   `convert --alm --dry-run` **without** `--upload` is the analysis path: it
   downloads each test, converts the bodies, and reports go/no-go — blockers,
   external references, missing or unresolvable resources, checkout/lock state
   — with zero ALM writes and no backup confirmation required. Its depth
   matters: `--analysis-depth standard` (the default, and what the Migration
   Console's **Run Analysis** button uses unless Analysis Depth is set to Deep)
   is that AOM-free assessment, while `--analysis-depth deep`
   really does launch UFT and AOM-build every test, proving each passing asset
   converts — still with no upload.

   Adding `--upload` to a dry run makes it do **less**, not more: dry-run
   conversion stops before any UFT/AOM operation, so `--upload --dry-run`
   rehearses the gate, not the payload. It produces no AOM build and no
   per-file upload or stale-file preview.
3. **Real uploads require `--confirm-alm-backup`** — your assertion that the
   ALM project database and repository are backed up (or snapshot-protected).
4. **Blockers fail closed.** A test whose conversion produced blockers is
   refused (`status=blocked`) before any ALM write; `--allow-blockers` is
   the recorded expert override. See [remediation.md](remediation.md).
   The all-or-nothing pre-flight gate has its own recorded override,
   `--allow-partial-conversion`: it converts the eligible assets when others
   are disqualified, knowingly leaving the project half Python and half
   VBScript. The gate still runs, every disqualified asset stays named in
   `alm_preflight.json`, and those assets are re-injected as in-scope
   `preflight-disqualified` failures — so a run that used the override can
   never report a clean whole-project conversion.
5. **Copy/paste-derived tests are refused** (`status=shared-assets`) — their
   assets belong to the source test and conversion cannot work. See
   [advanced_troubleshooting.md](advanced_troubleshooting.md) §1a.
6. **Every upload is verified**: stale server files are removed from a real
   server listing, asset ownership is repaired so UFT runs the Python, and
   the test is re-downloaded and byte-compared (`upload_verified` in the
   results). A `mismatch`, or a verification download that itself `failed`,
   fails the test as `upload-verify-failed`, and that aborts the run as item
   9 describes: the test comes back as `rolled-back` (or `rollback-failed`),
   with the verification failure kept in `error` and the run journal.
7. **Version-controlled projects check in only after verification.** In a
   VC-enabled ALM project each converted asset is checked in only once
   post-upload verification passes; any failure after check-out abandons the
   checkout, so the server keeps its last checked-in version.
8. **A conversion is judged against the analysis in its own run folder.** Run
   the analysis, any `--upload --dry-run` rehearsal and the real upload into the
   **same** folder: pass the same `--run-id` to all of them, or omit `--run-id`
   everywhere and pass the same `--domain`/`--project` (folder
   `<Domain>-<Project>`). A conversion in a folder with no analysis is refused —
   every asset is `not-analyzed` and the run ends `preflight-failed` with no ALM
   writes. The Migration Console does this for you: it converts into the run
   folder its analysis wrote. A rehearsal writes no report set and no executive
   summary of its own, so the analysis reports in that folder — and the frozen
   `alm_analysis_results.json` the gate judges against — are left as they are.
   It republishes that folder's verdict rather than computing a new one, and
   prints a `report_set` line explaining why it wrote no reports of its own —
   unless the rehearsal itself failed an in-scope asset, in which case it
   publishes no verdict at all; treat that absence, like any other missing
   verdict, as `no-go`.
9. **A real upload stops at the first failure it cannot recover.** A failure
   that happens *before* the asset's upload starts — a UFT build fault, an
   error, or a test the Test Plan walk did not find — is retried up to twice,
   and a dropped ALM session is reconnected first. Any other failure aborts the
   run. Every asset the conversion wave already wrote — including any an
   earlier attempt of the same wave converted — is then restored from the copy
   the wave froze before changing it, callers first, and reported
   `rolled-back` (VBScript again); the assets after it are reported
   `not-attempted`. `rollback-failed` means the restore did not complete or
   there was no copy: that asset may still be Python on the server, so inspect
   it in ALM and recover it with `restore --wave` (when a copy exists), ALM
   version history, or your backup. Neither the rollback nor `restore` undoes
   the resource **relation** changes: a restored VBScript test stays related to
   the converted `.pfl` and to `PhoenixVBRuntime.pfl` rather than to its
   original `.qfl`, and the runtime library and its Resources folder stay in
   the project. Re-point those relations in the ALM client before running a
   restored test. [alm_safety.md](alm_safety.md) has the full list of what a
   conversion writes.
10. **A native crash of the conversion process is recovered, within a
    budget.** A real upload runs under a crash supervisor. When Windows ends
    the conversion process, the supervisor records the crash, keeps the
    evidence under `crash_recovery\<wave>\` in the run folder and starts the
    conversion again; the new attempt checks any test the crash may have left
    half-written against the wave's copy, and restores it from that copy if it
    differs, before it converts anything. The third crash while the same test
    is in flight, the sixth in the wave, or the second in a row outside any
    test aborts the wave and rolls it back as item 9 describes. See
    [advanced_troubleshooting.md](advanced_troubleshooting.md) §9.

### What conversion carries automatically (ALM mode)

- **Action parameters** — definitions (name, type, direction, default) are
  harvested from the legacy test and authored onto the converted test.
- **Linked function libraries (`.qfl` → `.pfl`)** — a library attached as an
  ALM Test Resource is downloaded and converted **once** to a Python Function
  Library (`.pfl`, the Python analog of `.qfl`), uploaded as a shared ALM
  "Function library" resource in the same Resources folder as the source
  `.qfl` (convert-in-place), and **linked** to each converted test (UFT
  Settings → Resources → Libraries). Phoenix does not rely on that link alone:
  it also injects a short auto-generated **library-binding prelude** at the top
  of every **non-flow** action of a library-linked test, which loads the library
  unconditionally on action entry (`exec` into the action's globals), so the
  library's functions are callable directly — **no `import`** — and can use
  the UFT runtime objects (`Reporter`, `SystemUtil`, …). The main flow
  (Action0) gets no prelude, so a library function called directly from the
  converted main flow is not self-healed. The library is identified
  by its **ALM resource (asset) id**, not by file name: several same-named
  `.pfl` files can live under different Resources folders, and UFT's Python
  engine was measured binding a library the test is not linked to. Because UFT
  scopes libraries to the *calling* test, each test also publishes its library
  choice **before** the main flow body in Action0, so an action invoked from
  another test binds the caller's library. Both of those generated blocks are
  marker-delimited and are stripped and regenerated on re-conversion — do not
  hand-edit them. Libraries are still shared by reference, not copied or
  inlined into actions: the library is converted once and every referencing
  test links the same `.pfl`, exactly like native UFT `.qfl` behavior.
- **A third generated block, and why it shows up in the canvas.** Action0 of a
  test that links a function library or carries a cross-test reference can also
  end with a `# _phoenix_scope_binding` block: an `if False:` suite of
  `RunAction("<name>", oneIteration)` lines. It is never executed — it exists
  because UFT's Python engine only re-binds an action's linked libraries on
  iteration 2 and later when the main flow script names that action. UFT's
  Solution Explorer canvas and the engine's flow scan are the same static parse,
  so every line in the block is **drawn as a flow node** even though nothing
  runs it. The block lists only actions the main flow does not call itself —
  typically an action run from inside another action's body, or reached through
  an external reference — so a reviewer comparing the converted canvas against
  the VBScript original sees those nodes and no others. This applies to
  filesystem conversions as well as ALM ones. Like the other two blocks it is
  marker-delimited and regenerated on re-conversion; do not hand-edit it.
- **VBScript compatibility helpers** (upload conversions only) — kept in the
  shared function library `PhoenixVBRuntime.pfl`, in a Resources folder named
  `UFT Phoenix` that is created on first use and only ever **gains** entries, so
  a script keeps running the exact helper text it was converted with. The
  library is linked and related to each converted test whose scripts use it, and
  those scripts carry a generated `# _phoenix_vb_runtime` block — placed after
  any library-binding prelude — that installs the helpers they need;
  `alm_aom_results.json` lists them per test as `runtime_helper_blocks`. If the
  library cannot be written or related to a test, that test simply keeps its
  helpers pasted inline and runs as it always did. A test **fails** (`status
  error`) only when a library it links, or an action it calls, already depends
  on the runtime, because then there is no pasted copy to fall back to. Analysis
  never writes or uses the runtime. Do not hand-edit the block or the library.
  The filesystem path keeps its own copy at
  `FunctionLibraries\PhoenixVBRuntime.pfl` under the output root.
- **Object repositories and DataTables** — carried per action, byte-identical.
  One open limitation: a caller that owns a **shared** `.tsr` repository can
  lose that association. The build discloses it when it happens, and converting
  the test again does not repair it — re-attach the shared repository in UFT.
- **Cross-test shareable ("reusable") action references** — when a converted
  caller invokes an action that lives in another test (`RunAction "X
  [OtherTest]"`, `LoadAndRunAction`), those external references are rebuilt
  natively (via UFT's `AddExistingAction`) so the shareable action stays in
  its own test and is consumed **by reference**. The action body is never
  copied into the caller. Because the whole project is converted together,
  every test in a call chain is Python and the chain runs under one engine.
- UFT API/Service tests (C#-based) are detected and skipped as out of scope.

### Version-controlled ALM projects

Projects with ALM version control enabled are supported automatically — no
configuration. Versioning is detected per asset through OTA (a project
without version control is simply treated as unversioned).

Conversion flow per asset:

1. **Clear any entity lock** — best-effort, and never a failure (see below).
2. **Undo any pre-existing checkout** — a checkout left by another user, or
   a stale one of our own, is undone first. This reverts the server working
   copy to the **latest checked-in version**, and that reverted state is
   exactly what gets converted.
3. **Fresh check-out → convert → upload → post-upload verification.**
4. **Check-in only after verification passes**, with the comment
   `UFT Phoenix migration: AOM-canonical Python conversion (verified)`.

Any failure after the checkout **abandons the checkout** (UndoCheckout), so
the server keeps its last checked-in version — a failed conversion never
leaves a half-written working copy or a bad checked-in version. Python
function-library resources (`.pfl`, ALM "Function library" resources) are
checked out and checked in the same way, but not on the test's timetable:
each is checked in as soon as its content is uploaded — before the test's
own build and verification gates run — so a later failure of that test, or
an abort rollback, does not revert the library. Its previous version stays
in ALM version history, and the run notes name the saved copy of the prior
bytes.

Undoing **another user's** checkout requires the connected ALM user to hold
the ALM "Manage checkouts"-equivalent permission; without it the conversion
stops at that asset with report category **"Version control blocked"** (`status
vc-blocked`). ALM conversion is all-or-nothing, so the run aborts there: assets
this run already uploaded are rolled back to VBScript (`rolled-back`) and the
rest are recorded `not-attempted`. Grant the permission (or have the holder
release the checkout), then re-run the whole-project conversion into the same
run folder as the analysis — the rolled-back assets convert again, and anything
the journal recorded as finished is carried forward. There is no failed-asset-
only re-run of an ALM conversion, and `--resume` does not apply.

Every conversion in a version-controlled project creates a **new version**;
the pre-conversion version stays in ALM version history, which is a
first-class rollback path (alongside the `restore` command).

**Asset locks never fail a conversion.** A locked asset is converted and
**overwritten**; there is no `locked` failure status. Per asset the pipeline
allows a 10-second grace period for the lock to clear on its own, attempts
to release it, then converts either way. That is safe because an ALM lock
does not block `ExtendedStorage.Save` — the write that carries a test's
payload (`Script.pts`, `Test.tsp`, the `.usr`) — only entity *metadata*
writes (`SetField`/`Post`), which the upload path already treats as
optional. It is also necessary: a whole-project conversion is
all-or-nothing, and a run that dies partway leaves the project half Python
and half VBScript, breaking cross-test action chains. `UnLockObject()`
releases only your own lock; revoking a foreign one means deleting its
`LOCKS` row through the OTA `Command` object, which ALM disables by default
— where that is unavailable the conversion still completes and overwrites.
The run records `entity-lock-force-revoked` or
`entity-lock-not-cleared-proceeding`, and the asset carries a note naming the
holder. When the `LOCKS` table is readable that note also names the machine, ALM
session id, lock time and last-active time; when it is not, only the user name
is available. Because this overwrites anyone still editing a locked asset, run
conversions in an agreed window with the project empty.

**Analysis makes no version-control writes.** The ALM analysis
(`convert --alm --dry-run`) only snapshots per-asset checkout/lock state.
On a version-controlled project the analysis report includes a **"Version
Control & Locks"** section — counts plus who holds each checkout and lock —
the operator's chase list before a conversion window.

### Examples

Every command below needs the four connection flags, and the analysis and the
conversion must land in the **same run folder** — here `WAVE1`. Set the password
once for the session (Windows `cmd`):

```
set UFT_MIGRATE_ALM_PASSWORD=<password>
```

```
# 1. Analyze the project (read-only: zero ALM writes).
# This is what the Migration Console's Run Analysis button issues for an ALM
# project. There is no `analyze --alm`: that flag combination exits 2.
uft-migrate convert --alm --dry-run --run-id WAVE1 ^
    --alm-url http://alm.example.com:8080/qcbin --username svc.migration ^
    --domain MY_DOMAIN --project MY_PROJECT

# 2. Rehearse the gate for a whole-project upload (zero ALM writes; no AOM
# build, no per-file upload preview — see the safety model above).
# It writes no report set of its own, so step 1's analysis reports stay put;
# stdout carries that folder's verdict and a `report_set` line saying so.
uft-migrate convert --alm --upload --dry-run --run-id WAVE1 ^
    --alm-url http://alm.example.com:8080/qcbin --username svc.migration ^
    --domain MY_DOMAIN --project MY_PROJECT

# 3. Real whole-project upload, in place, with the executive summary.
# `run --alm` is the command the Migration Console's Run Conversion issues;
# `convert --alm` runs the same pipeline but writes no executive_summary.*.
uft-migrate run --alm --upload --confirm-alm-backup --run-id WAVE1 ^
    --alm-url http://alm.example.com:8080/qcbin --username svc.migration ^
    --domain MY_DOMAIN --project MY_PROJECT

# Same upload, plus an ALM Test Lab run of the converted tests
# (support lever; the Migration Console has no execution control).
uft-migrate run --alm --upload --confirm-alm-backup --run-id WAVE1 ^
    --alm-url http://alm.example.com:8080/qcbin --username svc.migration ^
    --domain MY_DOMAIN --project MY_PROJECT ^
    --run-via-alm --alm-test-set-name "Wave 1"
```

Drop `--run-id WAVE1` from all of them and the folder defaults to
`<Domain>-<Project>` instead (`out\My_Domain-MY_PROJECT` for the values above),
which is equally valid as long as every command passes the same
`--domain`/`--project`. What must not happen is a conversion in a folder that
holds no analysis: that run is refused at the pre-flight gate.

### Cross-test reusable actions (whole-chain rule)

A test that calls another test's reusable action executes the callee inside
the **caller's** engine, so a chain must be uniformly one engine. Phoenix
converts the whole ALM project together, then rebuilds each caller's external
"call to existing action" references natively with `AddExistingAction` — the
shareable action stays in its own test and is consumed by reference (no
copying, no inlining of the action body). Resolved references are recorded per
asset in `alm_aom_results.json` and `conversion_summary.json`
(`external_test_paths`, `action_renumber_map`), and the cross-test graph is in
`analysis_dependency_graph.json`.

### ALM run artifacts

In the run folder, after an ALM analysis or conversion:

- `scan_report.{json,md,html}` and the `analysis_*.html` drill-down pages — the
  verdict and the per-asset evidence behind it.
- `alm_aom_results.json` — per-test statuses, blockers, upload verification and
  Test Lab run ids. The authoritative per-asset payload.
- `alm_analysis_results.json` — the analysis payload frozen when the pre-flight
  gate passed, so the conversion cannot overwrite the evidence that authorised
  it.
- `alm_preflight.json` — the pre-flight gate's verdict and every disqualified
  asset by name.
- `conversion_summary.json` and `observability_metrics.json` — run-level
  rollups.
- `analysis_dependency_graph.json` — the cross-test shareable-action graph,
  written by the analysis pass.
- `dependency_graph.json` — the graph the report's **Dependency Graph JSON**
  link opens; on ALM runs it is built from `analysis_dependency_graph.json`.
- `migration_log.txt` — JSON-lines event log.
- `file_manifest.txt` — flat manifest of the analysed scope.
- `resume\alm_test_results.ndjson` — the per-asset conversion journal that
  drives Carried Forward and decides which conversion wave a launch continues.
  `resume\alm_asset_details\` beside it keeps what the reports show for each
  converted asset, for a later attempt that carries the asset forward.
- `resume_state.json` — the run checkpoint the Resume Previous Run dialog reads.
- `resume\alm_wave.json` and `resume\phoenix_run.lock` — a summary of the
  latest conversion wave, and the lock that keeps a second conversion,
  analysis or restore out of the run folder while one is running.
- `alm_aom_work\alm_rollback\` — the frozen pre-conversion snapshots. These are
  the true originals and what `restore` reads:
  `test_<id>_source` is each test's first-sight copy,
  `waves\<wave>\test_<id>\` the copy each conversion wave froze, which crash
  recovery, the wave's rollback and `restore --wave` use, and
  `resources\<wave>\<test id>\` the bytes of each `.pfl` library a wave
  replaced. Each write's "prior copy" holds the bytes THAT write replaced; the
  scan report's shared-library section also names, per library, the copy that
  holds it as it was before the wave first wrote it, when one can be tied to
  that first write (two libraries of the same file name share a test's first
  copy, so the folder alone never says which library a copy holds). A new
  wave deletes the copies of older finished waves except the newest one's that
  wrote to ALM (a
  wave that wrote nothing, such as a launch the pre-flight gate refused, does
  not count). *Wrote nothing* means wrote no test — no test upload, restore
  or rollback: a wave can still have written shared libraries before its
  first test upload began, because library writes are not journaled.
  `alm_aom_work\test_<id>_source` holds only the latest download.
- `crash_recovery\<wave>\` and `crash_breadcrumbs.log` — the crash supervisor's
  evidence for each attempt, and a line per ALM step of an upload, the last of
  which names the step a crashed conversion process died in
  ([advanced_troubleshooting.md](advanced_troubleshooting.md) §9). The
  supervisor deletes a wave's `crash_recovery\<wave>\` once two later
  conversion waves in the run folder that wrote to ALM have closed (a wave
  that wrote nothing, such as a launch the pre-flight gate refused, does not
  count; *wrote nothing* means wrote no test, as above). A memory dump is
  never copied into it (a dump may hold the ALM password); `crash.json` names
  where Windows wrote it.
- After a crash recovery the report set describes the whole conversion: its
  total time covers every attempt of the conversion wave, the crashed one
  included, but not the time between attempts (the timing note says how many
  there were and how long it left out), assets converted before the crash
  keep the duration measured then, and a **Crash Recovery Notes** section on
  `analysis_assets.html` and in `scan_report.md` lists each affected asset's
  `[crash recovery]` notes.
- `alm_wave_stop.json` — written, instead of a report set, when a conversion
  stopped and stays open to resume.
- `executive_summary.{json,md,html}` — written by `run --alm` (and by
  `summarize`), not by `convert --alm`.

Outside the run folder:

- `%LOCALAPPDATA%\Merito\UFT Phoenix\logs\` — one diagnostics log per Phoenix
  process (the Migration Console, each CLI, the crash supervisor and its
  workers; a build, analysis or discovery child only when it has a warning or
  an error), as JSON lines. They survive what the run folder does not: a
  re-analysis that clears `migration_log.txt`, the next run's overwrite of
  `alm_aom_results.json`. An error a message names by id, `E-<time>-<process
  id>-<number>`, is recorded in full there. The ALM password is masked before
  a record is written: by its value when it is 6 characters or longer, and
  wherever it follows a name such as `password` or `--password`. Phoenix
  deletes logs older than 30 days, and the oldest beyond 200 MB, itself, when
  the Migration Console or a command starts (never while it collects
  diagnostics); uninstalling leaves the folder in place.
- `out\_support\` — the support bundles `diagnostics collect` writes (see
  *Collecting diagnostics* above), or `%LOCALAPPDATA%\Merito\UFT Phoenix\support\`
  when there is no `out\` folder, where the Migration Console also keeps the
  collector's output. Nothing deletes them.

Forensic reading order:
[advanced_troubleshooting.md](advanced_troubleshooting.md) §5.

## Config file fields

- `search_folders`: ordered extra resource lookup roots for relative
  reference resolution. Config file only.
- `custom_rule_mappings`: regex → replacement rewrites applied to every
  converted line (editable from the Migration Console's mapping-rule editor).
  Config file only.
- `reporting.redaction`: redact path fields in generated artifacts. Config file
  only.
- `uft_object_model_path` (also `--uft-object-model`): a UFT object model JSON
  file. It **replaces** the shipped method registry rather than extending it,
  so use it only to supply a complete model; to add a handful of framework
  methods use `custom_uft_methods` instead.
- `custom_uft_methods` (also `--custom-uft-method`): methods always emitted with
  parentheses.
- `reporting.verbosity`: `quiet|normal|verbose` (`--verbose` selects `verbose`).
- `reporting.emit_dependency_graph` (also `--emit-dependency-graph`): toggle the
  dependency graph artifact.

There is no allow-list for dynamic descriptive programming, and nothing blocks
it: it is classified "dynamic (requires review)", carries a risk weight, and is
surfaced as the report row "Descriptive programming - dynamic (requires
review)". Do not confuse it with the separate `dynamic-code` (Execute/Eval)
blocker, which no config field waives either.

## Custom method onboarding flow

1. Run `scan` and review `unrecognized-object-member` warnings.
2. Add framework methods to `custom_uft_methods` (config file,
   `--custom-uft-method`, or the console's **Custom UFT Methods** box).
3. Re-run `scan`; convert once the warnings are triaged.

## Legacy ALM source roots (not recommended)

A filesystem `scan`/`convert` whose `--source-root` is an ALM reference
(`[ALM]...`, `td://`, `qc://`, `alm://`) needs an external bridge program, named
in the `UFT_ALM_BRIDGE_CMD` environment variable, with an optional
`UFT_ALM_CACHE_ROOT` for its local cache. Phoenix does not ship a bridge;
without one the scan reports the `unresolved-alm-source` blocker and nothing is
converted. Use the whole-ALM-project path described above instead.
