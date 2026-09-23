# Enterprise Migration Playbook

The engagement sequence for migrating a UFT VBScript estate to UFT Python
with Phoenix. Phases 0–5 name their exit criteria — do not advance without
them. Companion documents: [alm_safety.md](alm_safety.md) (write-safety
model), [gui_field_guide.md](gui_field_guide.md) (console reference),
[remediation.md](remediation.md) (blocker fixes).

## 0. Environment readiness

- Run `uft-migrate doctor` on the migration workstation **and every
  execution host**; resolve every FAIL (pywin32, UFT install, IronPython
  runtime completeness) **and** every WARN that applies to the host's role.
  Two of those warnings are blocking in practice even though doctor grades
  them WARN, not FAIL: a missing ALM client (`alm-client`) on the migration
  workstation for any ALM work, and a missing `IronPython.dll`
  (`uft-ironpython`) on any host that runs converted tests.
- Confirm the migration account can read the Test Plan scope and (later)
  write to it, **and** can create folders and function-library resources in
  the Test Resources module and relate them to tests — conversion adds a
  `.pfl` function library for each converted `.qfl`, plus one shared helper
  runtime library in a `UFT Phoenix` folder it creates under Resources. On a
  version-controlled project the account also needs the ALM "Manage
  checkouts"-equivalent permission (Phase 4). Permission to run OTA SQL
  commands is optional: with it, conversion clears stale entity locks
  itself; without it a locked asset still converts, but the lock stays.
- *Exit:* no FAIL, and no role-relevant WARN, on any host; live ALM login
  check passes (`doctor --alm-url … --username …`).

## 1. Baseline discovery

- Run analysis across each candidate portfolio: on a **filesystem** estate
  `uft-migrate scan` (or its alias `analyze`), on an **ALM project**
  `uft-migrate convert --alm --dry-run` — the read-only pass that makes zero
  ALM writes and needs no `--confirm-alm-backup`. Each is what GUI Step 5
  runs for its workflow. There is no `analyze --alm`: that flag combination
  is refused before any ALM connection is opened.
- Aggregate blocker categories and risk distribution from the scan reports;
  enable the dependency graph to map shared libraries and reusable actions.
- Identify copy/paste-derived tests early (they surface as `shared-assets`)
  and decide: re-create each so it owns its assets, or retire it (converting
  the owning test does not clear the refusal).
- Run the manual sweep for the constructs the reports do not reliably name
  (`GoTo`, `On Error GoTo <label>`, VBScript classes, and `Eval` *inside an
  expression*) — see [limitations.md](limitations.md) § *Not detected before
  conversion*. Which of them a report catches — and which pass in silence —
  depends on the path. On the **filesystem** `scan`/`analyze`, the first three
  raise nothing but a generic warning, while `x = Eval("…")` does raise a
  `dynamic-code` blocker. On the **ALM** `convert --alm --dry-run` it is the
  reverse: the first three convert to Python that will not parse, so the
  syntax gate fails the asset with a generic *"converted output is not valid
  Python"* blocker, while `x = Eval("…")` passes silently and raises
  `NameError` only when UFT runs the test. On either path a clean report is
  not evidence that all four are absent.
- *Exit:* blocker inventory triaged into fix-at-source and out-of-scope
  buckets (a custom mapping rule cannot clear a blocker), **and** the
  undetected-construct sweep run and its hits triaged.

## 2. Pilot

- Pilot on a small, representative test set — a **filesystem** copy of
  low/medium-risk tests, or a **dedicated pilot ALM project** seeded with
  copies (ALM conversion is whole-project, so you cannot upload against a
  subset of the production project). Seed it so that **each test owns its
  assets**: save each test into the pilot project from UFT (Save As), or
  paste with the option that creates copies of related entities. A copy that
  still points at the source test's assets is refused as `shared-assets`
  with no override. Copy the resources those tests link (function libraries,
  shared object repositories) and every callee of a cross-test caller,
  keeping the Test Plan and Resources paths the same so the references
  resolve.
- Include at least one test exercising each estate trait: function
  libraries, action parameters, DataTables, object repositories, and a
  cross-test reusable-action caller.
- If the production project is version-controlled, the pilot project must be
  version-enabled too. The basic path — check out, convert, verify, check in
  as a new version — has run against a live version-enabled project, for
  tests without linked function libraries. Undoing another user's checkout,
  the missing-permission `vc-blocked` failure, abandon-on-failure, and
  check-out/check-in of `.pfl` resources have unit coverage only
  ([limitations.md](limitations.md) § *Version-controlled ALM projects*), so
  run acceptance cases TC-21 and TC-22
  ([acceptance_test_plan.md](acceptance_test_plan.md) § I) on that pilot
  before the production window.
- Remediate its blockers ([remediation.md](remediation.md)); re-analyze
  failed assets until clean, and confirm no asset still reports
  `shared-assets` before converting.
- **ALM pilot:** run a **Deep** analysis (Step 5, Analysis Depth = Deep).
  Both depths are read-only, but Deep is the only one that builds the
  converted tests on disk — under
  `out/<run id>/alm_aom_work/test_<id>_build/<TestName>/`, the Action
  folders sitting inside that test-name directory — so a Standard analysis
  leaves nothing to compare. Review the report, then on **Step 6** open
  *Compare Converted Output…*, pick an `Action<N>/Script.pts` from that
  build folder, then browse to the original `Action<N>/Script.mts` under
  `test_<id>_source/` — an ALM build does not pair automatically. Then
  convert with backup confirmed. ALM conversion from the console always
  uploads in place; the console has no upload/dry-run toggle (on the CLI the
  read-only pass is `--dry-run`, and the upload needs
  `--upload --confirm-alm-backup`).
- **Filesystem pilot:** analysis produces no converted output, so convert
  with Convert Mode `new` — the output lands under the Output Root and the
  source tree is left untouched — then review the diff before distributing.
- Verification is two-fold: the pipeline's own post-upload verify
  (`upload_verified=ok` per test), then running the converted tests from their
  **existing Test Lab test sets** in ALM — your own run path — with the
  execution host's desktop session active, and with that host's
  `%LOCALAPPDATA%\Temp\TD_80` cache purged first (Phase 7). The conversion
  flow itself creates no test set, and the GUI never runs Test Lab; the CLI
  `--run-via-alm` lever remains for support scenarios, and it *does*
  find-or-create a test set of its own — by default `AOM Verification
  <YYYYMMDD_HHMMSS>` under `Root\UFT Phoenix`, overridable with
  `--alm-test-lab-folder` / `--alm-test-set-name`.
- Screen the VBScript baseline for false passes before you compare failure
  points. A baseline run whose duration sits at or just above your object
  sync timeout, and whose step list ends in a `Replay Warning` on a step
  that is **not** an `OptionalStep`, with no checkpoint or verification
  step, was graded Passed without doing the work; the same test can fail
  after conversion with nothing wrong in the conversion
  ([limitations.md](limitations.md) § *Conversion can surface
  object-identification failures your baseline hid*). A `Replay Warning`
  from a skipped optional step is intended behaviour and still passes after
  conversion. Fix the descriptors of a genuine false pass and re-baseline,
  or record it as a known baseline defect. When you compare durations,
  allow for a source helper that scans every process: it runs seconds
  slower after conversion without failing ([limitations.md](limitations.md)
  § *A source helper that scans every process runs slower after
  conversion*).
- Then compare failure points against that baseline: the pilot standard is
  *parity or better* (converted tests fail only where the VBS also fails, or
  later).
- *Exit:* pilot tests uploaded `upload_verified=ok` and behavior in their
  existing Test Lab sets at parity with baseline; on a version-controlled
  project, TC-21 and TC-22 passed on the version-enabled pilot.

## 3. Rule hardening

- Encode framework wrappers into `custom_uft_methods` and mechanical idioms
  into custom mapping rules; keep both in the shared config file under
  version control.
- Re-run analyze/convert on the pilot and confirm determinism: identical
  inputs must produce identical outputs across repeated runs. Reset the
  pilot first, or the second pass is not a comparison. On an **ALM** pilot,
  return the project to VBScript — from a server snapshot, or with
  `uft-migrate restore --from-run <pilot run id> --alm-test-id <id>
  --alm-url … --username … --domain … --project … --confirm-alm-backup` —
  then purge `%LOCALAPPDATA%\Temp\TD_80` and run analysis and conversion
  under a **new** run id, which gives the second pass its own report set to
  compare against the first. (Without the restore, a conversion under the
  earlier run id would skip every asset that run already converted, and
  re-converting a project that is already Python does not repeat the
  VBScript-to-Python translation. `restore` puts the scripts back; it does
  not undo the resource relations the conversion added.) On a **filesystem**
  pilot, leave the VBScript source untouched (Convert Mode `new`), set the
  first output aside, and convert again to the **same** Output Root — a
  different root changes the absolute library and action paths embedded in
  the output, so the two trees would not match.
- *Exit:* second pilot pass produces no new warnings and byte-identical
  output.

## 4. Migration window

- On a version-controlled project, do not open the window until the
  version-enabled pilot from Phase 2 has passed.
- Ahead of the conversion window, instruct **all users to check in their
  work and exit the project**. Leftover checkouts found during the window
  are treated as abandoned work-in-progress and force-undone — the server
  reverts to the latest checked-in version, which is what gets converted.
  Force-undoing another user's checkout requires the ALM "Manage
  checkouts"-equivalent permission; without it the first such asset fails
  as `vc-blocked` ("Version control blocked"), **and that aborts the whole
  conversion**: every later asset is left `not-attempted`, and everything
  the run had already uploaded is rolled back. Nothing catches this before
  the first write — neither analysis nor the pre-flight gate tests the
  permission, and a foreign checkout is only a gate warning — so confirm
  the permission on the migration account and clear the Checked Out list
  before the window opens.
- On a version-controlled project, run analysis and review the report's
  **Version Control & Locks** section — the per-asset checkout/lock snapshot
  naming holders — as the pre-window chase list. That section is rendered
  only when the project is version-controlled, and its Checked Out and
  Locked tables stop at the first 100 assets each; the complete lists are in
  `scan_report.json` under `version_control`. On a project without version
  control the section never appears, even when assets are locked — use your
  ALM client's own locked/checked-out view instead.
- Convert. Assets still locked by another ALM session do **not** fail: after
  a 10-second grace period and a release attempt, they are converted and
  **overwritten** (an ALM lock does not gate the payload write, only entity
  metadata). The run records `entity-lock-force-revoked` or
  `entity-lock-not-cleared-proceeding` and names the holder per asset. This
  is why the chase list matters — anyone still editing a locked asset loses
  that work and may hold a stale copy in their ALM client.
- *Exit:* chase list cleared (or holders disconnected) before the window; no
  `vc-blocked` assets outstanding.

## 5. Whole-project rollout

- ALM conversion is whole-project — the entire domain/project converts as
  one unit, which keeps every call chain uniform unless you break it
  yourself. Parking a caller whose callee still converts, or using
  `--allow-partial-conversion`, leaves a VBScript test calling a Python
  action; parking a *callee* is caught by the pre-flight gate, which
  disqualifies its callers. Park whole chains only. The dependency graph is
  still worth reading: it shows which tests call which reusable actions, and
  cross-test callers have their external "call to existing action"
  references reconstructed natively (via `AddExistingAction`) so shareable
  actions stay in their own tests and are consumed by reference.
- Sequence the run as: analysis (read-only dry run, Deep if you want the
  diffs) → review the report and diffs → convert (upload in place, verified
  per test) → spot-check the converted tests from their existing Test Lab
  sets in ALM → sign off. Analysis and conversion must share one run id
  (`--run-id`, or the console's **Analysis Run ID**): a conversion is judged
  against the analysis in its own run folder, and without a matching
  analysis every asset is recorded `not-analyzed` and the run is refused
  before any ALM write.
- An interrupted run is re-run under the **same run id**, and it picks up
  where it left off: an asset an earlier run of that run id converted,
  uploaded and verified — and whose copy on the server is still Python — is
  skipped, reported `ok` under **Carried Forward**, and the rest of the
  project converts. That needs no flag. A run you **cancelled** is different:
  the cancel kills the process outright, so nothing is rolled back, any
  checkout the run took stays open, the UFT cache is not purged and a UFT
  process may survive. Check the asset that was in flight — and its
  checkout — before you re-run. If it is half-written, restore it first
  with `uft-migrate restore` (Phase 3) from the snapshot at
  `alm_aom_work\alm_rollback\test_<id>_source` in the run folder: a re-run
  takes whatever the server now holds as its source.
  `--resume` is not required and is refused unless the previous checkpoint is
  still `running` and the command line matches. Conversely, to reconvert
  everything after a mapping-rule, library or configuration change, use a
  **new** run id: the same run id would skip the assets you want rebuilt.
- A carried-forward asset still serves as a callee: the journal record it is
  carried from holds the converted action layout its callers need, so a
  caller converted later in the re-run is retargeted as usual. The one
  exception is a journal written by an earlier version of Phoenix, before
  that layout was recorded — a caller of such an asset then blocks with
  *"that callee has no conversion record in this run"*, which aborts the
  run ([troubleshooting.md](troubleshooting.md) covers the message).
  Convert in a new run folder (a fresh run id, with the analysis run under
  it first) so caller and callee convert together, and keep the old run
  folder: its `alm_rollback` snapshots are the only pre-conversion
  originals of the tests the earlier run converted.
- `--failed-only` is the only real subset re-run and it applies to
  analysis — the filesystem `scan`/`analyze` and the ALM
  `convert --alm --dry-run`; whole-project ALM conversion rejects it outright
  as all-or-nothing.
- *Exit:* every in-scope asset `ok`, `upload_verified=ok` on every asset this
  run converted (Carried Forward assets were verified by the run that
  converted them), blockers zero, Test Lab spot-checks at parity. The GUI
  flow is fail-closed with no override. The CLI has two recorded expert
  overrides: `--allow-blockers`, which waives converter blockers but cannot
  bypass a blocker whose converted Python does not parse (see
  [remediation.md](remediation.md) § *The override, and when not to use
  it*), and `--allow-partial-conversion`, which lets the all-or-nothing
  pre-flight gate pass while the disqualified assets stay VBScript — those
  are reported as `preflight-disqualified` failures, so a run that used it
  cannot meet this exit. Park genuinely out-of-scope assets on Step 5
  instead.

## 6. Distribution (filesystem estates)

- Converted filesystem tests are **path-bound**. Their function-library
  links (including `FunctionLibraries\PhoenixVBRuntime.pfl`) and their
  cross-test action references are stored as absolute paths, so copying or
  moving the tree breaks them at run time, with no warning at build time.
  Either run the tests from the location they were converted to — a share
  every runner reaches by the same path works — or convert again with that
  final location as the Output Root (`--output-root`; under Convert Mode
  `in-place` the tests stay where the source was). The Portability Manifest
  in `convert_report.html` lists every absolute link: read it before
  distributing.
- Run `uft-migrate doctor` on every runner. It reports what is missing; it
  repairs nothing. If `uft-ironpython` comes back FAIL (missing
  `IronPython.Modules.dll`, `Microsoft.Scripting.Metadata.dll` or the `Lib\`
  standard library) or WARN (no `IronPython.dll` at all), repair the runtime
  by hand as described in
  [advanced_troubleshooting.md](advanced_troubleshooting.md) § *IronPython
  runtime completeness*, then re-run doctor — before first execution.

## 7. Governance

- Gate each wave's completion on the executive summary verdict, not raw
  counts; require structured remediation for every blocker. The GUI flow is
  fail-closed with no override. The CLI has two overrides, both disclosed in
  the run's own reports: `--allow-blockers`, which proceeds over converter
  blockers but cannot bypass unparseable converted Python, and
  `--allow-partial-conversion`, which lets the pre-flight gate pass and
  leaves the project part Python and part VBScript. Any run that used either
  needs explicit sign-off. Parking an asset out of scope is the sanctioned
  alternative, and the parking list is part of the sign-off.
- Keep the engagement config file (`custom_rule_mappings`,
  `custom_uft_methods` and, for filesystem estates, `exclude` /
  `exclude_test_paths`) in version control. For ALM, version-control the
  parked test-ID list separately: the Step 5 *Out-of-scope test IDs* /
  `--alm-exclude-test-id` values are not stored in the config file. A change
  to either re-opens the Phase 3 determinism checks.
- Retain the `out/<run id>/` folders as the audit trail — they hold the
  frozen pre-conversion snapshots under
  `alm_aom_work\alm_rollback\test_<id>_source` (the per-test rollback
  source; the staging copy at `alm_aom_work\test_<id>_source` beside it is
  only the latest download), the verification results, and the full event
  log. They are created in the folder Phoenix was launched from, so launch
  it from a writable working folder you keep — not from the install folder,
  which an upgrade or uninstall clears.
- Post-migration: Phoenix purges UFT's test cache
  (`%LOCALAPPDATA%\Temp\TD_80`) only on the machine that runs the
  conversion, and only for the account that runs it. Purge it by hand on
  **every execution host**: after each conversion, before the Test Lab
  checks in Phases 2 and 5, after any rollback to VBScript, and whenever
  tests are re-uploaded outside Phoenix. Until a host is purged it can keep
  running the build it extracted last. The command is in
  [advanced_troubleshooting.md](advanced_troubleshooting.md) § *Stale UFT
  test cache (TD_80)*.
