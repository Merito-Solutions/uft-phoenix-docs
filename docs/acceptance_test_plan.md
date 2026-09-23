# Manual Acceptance Test Plan

A hands-on validation walkthrough of UFT Phoenix, ordered so each case builds
on the previous. Run it on a machine with UFT One 26.1, the ALM client, and an
ALM project you can snapshot/restore, hosted on OpenText Application Quality
Management (formerly Application Lifecycle Management) 24.1, 25.1 or 26.1 —
the supported server versions. Each case lists steps and pass criteria.
Artifacts referenced live under `out\<run id>\` in the directory the
Migration Console or CLI was launched from (`%USERPROFILE%\out\` when
started from the Start Menu shortcut). Output Root does not move them.

Launch: `uft-migrate-gui` (GUI) and `uft-migrate` (CLI).

---

## A. Environment

**TC-01 — Environment preflight**
1. Run `uft-migrate doctor`.
2. PASS: exit code 0 and no `[FAIL]` rows. Nine rows print, in order:
   `platform`, `python`, `pywin32`, `uft-installed`, `uft-ironpython`,
   `alm-client`, `output-root`, `offline-package`, `alm-connectivity`.
   This plan needs UFT's Python engine and the ALM client, so
   `uft-installed`, `uft-ironpython` and `alm-client` must be `[ OK ]`. A
   `[WARN]` on `alm-client` or `uft-ironpython` fails this case. If
   `uft-ironpython` shows `[ -- ]`, doctor could not locate the UFT install
   path; confirm the IronPython runtime by hand before continuing.
3. PASS: `[ -- ]` (skipped) on the other two rows is expected.
   `offline-package` checks a package build folder and matters only to
   whoever builds the offline package; on an installed machine it is
   skipped. `alm-connectivity` skips unless `--alm-url` (or
   `UFT_MIGRATE_ALM_URL`) is supplied, which is TC-02. Any `[FAIL]` names
   its fix; resolve it and re-run before continuing.

**TC-02 — Live ALM login check**
1. `uft-migrate doctor --alm-url <url> --username <user>` with
   `UFT_MIGRATE_ALM_PASSWORD` set in the shell.
2. PASS: `alm-connectivity` reports login OK and a visible domain count.

## B. Console basics

**TC-03 — GUI launch and state persistence**
1. Launch the GUI; on Step 2 choose **Upgrade ALM Project**; on Step 3 fill
   Output Root, ALM URL, Username and Password; close the GUI; relaunch it
   and choose **Upgrade ALM Project** again on Step 2 (the workflow choice
   is not restored, and the ALM fields stay hidden until it is made).
2. PASS: all fields restore, including the password.
3. Open `out\.uft-migrate-gui-cache.json` under the launch directory
   (`%USERPROFILE%\out\` for the Start Menu shortcut) in a text editor.
4. PASS: the `alm_password` value starts with `dpapi:` — never plaintext.

**TC-04 — ALM Connect (threaded, friendly failures)**
1. Step 2: choose **Upgrade ALM Project**. Step 3: enter a deliberately
   wrong ALM URL (bad host) → Connect.
2. PASS: the UI stays responsive (no freeze, no stack trace), the Connect
   button comes back, and one of two dialogs appears. **ALM Connection
   Timed Out** appears after about 45 s with URL/firewall guidance,
   typically for an address that never answers. **ALM Connection Failed**
   appears sooner, naming the URL(s) tried and the client error, typically
   for a host name that does not resolve. The status line reads "ALM
   connection timed out." or "ALM server connection failed." respectively.
3. Enter the correct URL → Connect.
4. PASS: domain/project dropdowns populate.

## C. Analysis

**TC-05 — Project analysis end-to-end**
1. Step 2: choose **Upgrade ALM Project**.
2. Step 3: Connect, pick a domain/project (use a small pilot project with
   5–10 tests; ALM conversion is whole-project, so analysis covers the whole
   project), and tick *I confirm the ALM project database and repository
   backups are complete* — Step 3's validator refuses Next without it, so the
   wizard cannot reach Step 5 with the box clear (TC-08 part (a) exercises
   that gate deliberately).
3. Step 5: Run Analysis; watch per-asset progress.
4. PASS: analysis completes and the Step 5 status line carries a GO or
   NO-GO verdict. Open Scan HTML from Analysis Reports: it shows the
   approval recommendation, the Assets Passed / Assets Failed / Scan
   Blockers / Convertible Findings counts, and a Decision Drill-down with
   working links to the per-asset pages (Assets in Scope, Assets Passed,
   Assets Failed, Scan Blockers, Convertible Findings, Timing Metrics, and
   Out of Scope when any asset was excluded). The CLI Output pane holds the
   raw log. An ALM analysis report is organised by asset, not by file.

**TC-06 — Cancel and re-run**
1. Start an analysis on a larger source (a bigger filesystem tree or ALM
   project); click **Cancel** mid-run.
2. PASS: the analysis process stops immediately and the UI stays
   responsive. The status line briefly reads "Cancel requested — stopping
   analysis. …" and then "Analysis failed. …", and the progress line reads
   "Analysis did not complete." That is the expected end state for a
   cancelled run: the cancel kills the process, so the CLI exits without a
   result payload.
3. Re-run with the same Analysis Run ID and answer **Yes** to *Resume
   Previous Run*.
4. PASS — filesystem source: files already scanned before the cancel are
   not re-scanned. ALM project: analysis has no per-asset resume, so the
   re-run analyzes every asset again and must finish with a verdict.

## D. Conversion safety rails

**TC-07 — Step 4 policy surface and read-only analysis**
1. Step 4 (Conversion Strategy): review the page.
2. PASS (Upgrade ALM Project workflow): only the **ALM Conversion** policy
   note and the **Script Preservation** frame (VBS Preservation Mode:
   comment-block | interleave | python-only) appear. There are no ALM
   option fields — no Upload, Dry Run, blocker-override, cache-purge, or
   Test Lab controls — and the Filesystem Conversion Options frame is
   hidden on this workflow. (UFT FileSystem workflow: Step 4 shows
   **Filesystem Conversion Options** — Convert Mode, Overwrite Policy
   [fail | backup | overwrite], Parallel Mode (no effect) — and Script
   Preservation, with no ALM Conversion note. The two frames are never
   shown together.)
3. Step 5: Run Analysis over the pilot project.
4. PASS: analysis behaves as a read-only dry run — the tests' *Modified*
   dates in ALM are unchanged. (The Step-3 backup confirmation was already
   required before Analysis could be reached: it gates wizard navigation,
   not the analysis run, which the GUI issues as `convert --alm --dry-run`
   with no ALM writes.)

**TC-08 — Backup confirmation gate**
The GUI gate and the CLI gate are different mechanisms at different points, so
check both.

*(a) GUI — navigation validator on Step 3.*
1. Step 2: choose Upgrade ALM Project. Step 3: fill ALM URL, username,
   password, click Connect, pick a domain and project, and make sure *I
   confirm the ALM project database and repository backups are complete* is
   **unchecked**. The tick is never restored from the settings cache — every
   launch of the console starts with it clear — but it is still ticked from
   TC-05 if the console has stayed open since, so clear it. Press Next.
2. PASS: a "Backup Confirmation Required" modal appears, the wizard stays on
   Step 3, and no conversion is launched. The checkbox lives on Step 3, next
   to the ALM connection fields — Step 6 cannot be reached with it clear.
   (The earlier Step 3 checks fire first: an unfilled URL/username, no
   Connect, or no domain/project produces "Missing ALM Inputs" or "ALM
   Connection Required" instead.)
3. Tick the box and press Next.
4. PASS: the wizard advances to Step 4.

*(b) CLI — refusal before any ALM write.*
1. Run `uft-migrate convert --alm --upload ...` without
   `--confirm-alm-backup`.
2. PASS: exit code 2 and a `status: failed` refusal naming
   `--confirm-alm-backup`, raised before the ALM login, so nothing is touched
   on the server. `--upload` is what arms the gate: adding `--dry-run` makes
   no ALM writes and does not require the flag. Neither analysis depth lists
   the files an upload would write or delete, and with `--upload --dry-run`
   the run rehearses the gate without building any payload. (ALM conversion
   from the GUI always uploads in place; there is no GUI dry-run toggle.)

**TC-09 — Fail-closed blockers**
Run this case as a **Deep** analysis: at the default Standard depth the
analysis never opens UFT, so it does not evaluate `Parameter()` definitions
at all — it records the note "N action(s) read Parameter(); their
definitions are harvested at conversion time (analysis does not open UFT)",
reports the asset `ok`, and the verdict stays GO. The blocker is raised only
by a Deep analysis or by a real conversion.
1. In the pilot project, prepare a test whose action body calls
   `Parameter("x")` where `x` is defined at NEITHER action level (Action
   Properties → Parameters) NOR test level (File → Settings → Parameters).
   Leave the *referencing* action with no action-level parameters of its own,
   and give the test some parameter definitions elsewhere — test-level
   definitions that do not include `x`, or action-level parameters on a
   different action. (An action that carries any action-level definitions of
   its own is skipped by the resolver, so `Parameter("x")` there raises no
   blocker and the asset reads `ok` — that is not a failure of this case,
   it is the wrong setup for it.)
2. Step 5: set Analysis Depth = **Deep** and Run Analysis. Deep analysis
   rebuilds each test in UFT locally and writes nothing to ALM.
3. PASS: that asset's status is `blocked` in `alm_aom_results.json` and on
   the Assets Failed page; the blocker names the action and the unresolved
   parameter name(s) — e.g. `Action1: Parameter() references ['x'] not found
   among the legacy test's action or test-level parameter definitions` (it
   does not cite a source line); no ALM write occurred; the verdict is NO-GO
   and Step 6's Convert Project refuses to run. If instead the test carries
   no parameter definitions at all, the blocker is the variant `Action1:
   Parameter() referenced but no parameter definitions (action or test-level)
   were found on the legacy test` — it names the action but not `x`, and is an
   equally valid PASS.
4. PASS (what a real conversion would do, for the approver's record): in a
   whole-project upload conversion this status is fatal. The run aborts at
   that asset, every asset already uploaded in the run is restored from its
   pre-conversion snapshot and recorded `rolled-back`, and the remaining
   assets are recorded `not-attempted`. Any asset recorded `rollback-failed`
   is still converted on the server and must be restored with
   `uft-migrate restore` from the frozen snapshot before the project is
   used. `restore` puts back each test's own scripts and actions only — the
   resource relations the conversion changed are not reverted, so a restored
   VBScript test stays related to the converted `.pfl` and to
   PhoenixVBRuntime.pfl rather than to its original `.qfl`. Do not leave this
   test in the project — see the clean-up step before section E.

**TC-09a — Test-level parameters are carried, not blocked**
1. Using the same Deep analysis run, pick a test whose main flow or actions
   read `Parameter()` names defined only at TEST level (File → Settings →
   Parameters), where the reading action has no action-level parameter
   definitions of its own.
2. PASS: status `ok`; notes show `Harvested TEST-level parameter
   definitions: [...]`, `<Action>: Parameter() references satisfied by
   TEST-level definitions (...)`, and `Carrying parameter definitions:
   main-flow=[...]`. After TC-11's conversion, the converted test's UFT
   Settings → Parameters lists the definitions with their legacy defaults.
   Default values carry, but test-set runtime overrides do not propagate
   through the AOM main-flow indirection. (The `satisfied by TEST-level
   definitions` note is emitted on the ALM path; the local filesystem path
   logs only `Harvested TEST-level parameters: [...]`.)

**TC-10 — Shared-assets refusal**
1. In ALM, copy/paste an existing GUI test in the pilot project's Test Plan,
   then re-run Analysis (Step 5). A pasted copy cannot be converted on its
   own — ALM conversion is whole-project — so the analysis is where its
   status appears.
2. PASS: the pasted copy shows status `shared-assets` in
   `analysis_assets_failed.html`, marked "do not park" and left out of the
   "Park the Failed Assets" list; the message names the owning test id and
   the re-creation options (paste with "create copies of related entities",
   or save-as a new test in UFT); Step 6's Convert Project refuses with
   "Conversion Blocked — Unresolved Assets"; no ALM write occurred; no
   override exists.

**Clean-up before section E**
ALM conversion is all-or-nothing, so the assets TC-09 and TC-10 put into the
pilot project will refuse the conversion run. Before continuing:
1. Delete the pasted copy from TC-10. It must **not** be parked: a
   `shared-assets` asset is withheld from the park list on purpose, because
   parking it leaves the owning test converted and the copy pointing at it.
2. Remediate the TC-09 test (define the missing parameter at action or test
   level in UFT, or replace the read with a DataTable/Environment lookup),
   or park it on Step 5 under *Out-of-scope test IDs*. Parking leaves it
   untouched in ALM and still VBScript after the migration.
3. Alternatively, restore the pilot project from its snapshot.
4. Re-run Analysis until the verdict is GO. A Standard analysis will not
   flag the TC-09 test, but its blocker would still abort and roll back the
   conversion, so remove or remediate it either way.

## E. Conversion and upload

**TC-11 — Real conversion with verification**
1. Step 6: **Convert Project** on the pilot project, with the GO analysis
   from the clean-up step above. ALM conversion is whole-project and always
   uploads in place.
2. PASS: the run completes with no failed asset — every converted asset
   ends `ok`. (API tests and non-GUI test types are recorded out of scope
   rather than converted; they are not failures.) Pick one clean VBScript
   GUI test and read its record in `alm_aom_results.json`: `upload_verified`
   is `ok`, and its notes show stale-file deletions from a server listing,
   the VBScript sidecar purge, and the ARI ownership sync.
3. PASS (helper runtime), where converted actions use VBScript
   compatibility helpers: the asset's `runtime_helper_blocks` in
   `alm_aom_results.json` is non-empty; in ALM, Test Resources →
   `Resources\UFT Phoenix\PhoenixVBRuntime.pfl` exists and is related to the
   test. The run notes show `helper runtime '…PhoenixVBRuntime.pfl'
   (created)` (or `(helper entries added; …)`) on the asset that wrote it,
   and `helper runtime related: …` where the relation was newly made. No
   asset shows `helper runtime RELATION ERROR`. If an asset notes
   "PhoenixVBRuntime.pfl is not available to this test; its VBScript
   compatibility helpers stay pasted", record why — that test keeps its
   pasted helpers and still runs.

**TC-11a — Conversion resume and Carried Forward**
A conversion re-run into the same run folder skips assets its journal
records as uploaded and verified, provided the server still holds their
Python payload. This is what makes a long run survive an interruption.
1. With TC-11's conversion complete, click **Convert Project** again with
   the same run ID. (The analysis that authorised TC-11 is frozen in the
   run folder, so the pre-flight gate still passes.)
2. PASS: every asset TC-11 converted is skipped with the note "Already
   converted: uploaded and verified by an earlier run of this scope…",
   counts toward progress, and ends `ok`. `executive_summary.html` for this
   run shows a **Carried Forward** card with that count and a matching Next
   Steps note, so the document does not claim this run did the work.
3. Press Back to Step 5. PASS: Step 5 reads "Analysis verdict before the
   conversion: GO … its reports are on Step 6" and does not demand a
   re-analysis. (After the GUI is closed and reopened, Step 5 asks for
   Analysis to be re-run before another conversion; that is expected.)
4. Optional — interrupted run. **Cancel is a hard stop, not a pause**: it
   kills the process tree, so nothing is rolled back, any checkout the run
   took is not abandoned, the end-of-run UFT cache purge never runs (purge
   `%LOCALAPPDATA%\Temp\TD_80` by hand before opening a converted test, or
   UFT serves the pre-conversion build), UFT.exe may keep running, and the
   asset that was mid-upload can be left in either state. Before re-running,
   check that asset in ALM and, if it is damaged, restore it with
   `uft-migrate restore` from its snapshot under
   `out\<run id>\alm_aom_work\alm_rollback\`. On a disposable pilot project:
   start Convert Project, click **Cancel** once at least one asset has
   uploaded and confirm (a "Conversion Failed" dialog is expected), then
   click **Convert Project** again with the same run ID and answer the
   *Resume Previous Run* dialog either way — the per-asset journal is kept
   in both cases and is what drives the skipping. PASS: the completed
   assets are carried forward as in step 2 and the rest convert normally.
5. If the cancel in step 4 fell after a test that owns a shareable action
   and before a test that calls it, PASS also requires the caller to be
   converted in the resumed run rather than refused with "that callee has no
   conversion record in this run": a carried-forward test still serves as a
   callee, because its journal record holds the converted action layout its
   callers need. The one exception is a run folder whose journal an earlier
   version of Phoenix wrote, before that layout was recorded; for that folder,
   run the analysis again under a new run ID and convert there.

**TC-12 — Asset carry-over**
1. In the same conversion, pick a test with action parameters AND a linked
   `.qfl` Test Resource.
2. PASS: notes show `Harvested action parameter definitions`, `Carrying
   parameter definitions`, and that the linked `.qfl` was converted to a
   shared Python Function Library (`.pfl`) and linked to the test; confirm the
   `.pfl` resource exists in the source library's Resources folder in ALM, the
   converted test's UFT Settings → Resources → Libraries lists it, and the
   library functions are present as Python `def`s in the built `.pfl` (not
   copied into any `Action*/Script.pts`). For a test that uses VBScript
   compatibility helpers, Libraries lists `PhoenixVBRuntime.pfl` first and
   the converted `.pfl` after it; that ordering is deliberate, because the
   converted library installs its helpers from the runtime as UFT loads it.

**TC-13 — Converted test opens as Python in UFT**
1. Open the converted test from ALM in UFT One.
2. PASS: the test opens as a Python test; the action script is the
   converted Python (not VBScript, not a placeholder); action parameters
   appear in Action Properties with their legacy defaults. An action that
   uses VBScript compatibility helpers carries a `# _phoenix_vb_runtime v1`
   loader block instead of pasted helper definitions; it is the first thing
   in the action unless the test links a function library, in which case
   the `# _phoenix_library_binding` prelude comes first and the loader
   follows it.

## F. Execution verification

**TC-14 — Test Lab execution (CLI-only, optional)**
Test Lab execution is not available from the GUI; it survives only as the CLI
support lever `--run-via-alm` and its companion flags. The routine
verification path is the pipeline's own post-upload verify (TC-11), plus
opening a converted test in UFT One and running it, plus running converted
tests from their existing Test Lab sets in ALM. Run this case only when
CLI-driven execution evidence is required.
1. Use a **new** run ID. Re-using the earlier one makes the run read that
   run's journal and skip every asset already uploaded and still Python on
   the server — the skip happens before the Test Lab step, so no test would
   be executed. A new run ID needs its own analysis, or the pre-flight gate
   refuses the run.
2. Analyze into the new run folder:
   `uft-migrate convert --alm --dry-run --run-id <new id> --alm-url <url>
   --username <user> --domain <domain> --project <project>`
3. Convert and execute, with the desktop session active (do not lock or
   disconnect):
   `uft-migrate convert --alm --upload --confirm-alm-backup --run-via-alm
   --run-id <new id> --alm-url <url> --username <user> --domain <domain>
   --project <project>`
   Conversion is whole-project, so every in-scope test gets a Test Lab run.
4. PASS: a test set is created/reused, the runs execute, and
   `run_results.xml` under `out\<new id>\alm_aom_work\test_<id>_runresults\`
   shows real steps — input parameters appear with values; any failure is a
   genuine test/environment step, never `line 1 ... previously saved ...
   could not be found`.

**TC-14a — `--run-uft` refuses instead of silently running nothing**
Local UFT execution was removed; the flag is kept only so it can be refused
by name on both paths.
1. Run `uft-migrate convert --run-uft` (no `--alm`) in any project folder.
2. PASS: exit code 2 and a single-line JSON `{"status": "failed", "error":
   "--run-uft is no longer supported: ..."}` naming what to do instead. No
   run folder is created under `out\`.
3. Run `uft-migrate convert --alm --run-uft`.
4. PASS: exit code 2 and the equivalent `status: failed` refusal, this time
   naming `--run-via-alm`. No ALM connection is attempted.
5. FAIL if either command exits 0, or converts, or completes while ignoring
   the flag.

**TC-15 — Stale-cache protection (on by default)**
1. Read the run notes from TC-11's conversion (and TC-14's Test Lab run, if
   executed).
2. PASS: every asset's notes include "UFT test extraction cache purged
   (before conversion): …" (or "…was not present or could not be purged
   (before conversion)…", which is also a pass — the purge is best-effort
   and always reports its outcome). Each asset written to ALM also carries
   the "(after ALM write)" note. If TC-14 was run, its assets also show
   "Purged UFT test cache before Test Lab run: …".
3. PASS: from the GUI this purge cannot be turned off — Step 4 exposes no
   cache-purge checkbox. From the CLI it is on by default and only
   `--no-purge-uft-cache` disables it; do not pass it for this case.
   `--purge-alm-cache` / `--no-purge-alm-cache` are accepted but have no
   effect; there is no ALM client-cache purge to verify.
4. Note for multi-host estates: the automatic purge only covers the machine
   and user running Phoenix. Every other execution host needs
   `%LOCALAPPDATA%\Temp\TD_80` purged by hand before it runs a converted
   test.

## G. Console power features

**TC-16 — Command review is secret-free**
1. Step 6: Review Command with a non-blank ALM password configured.
2. PASS: the command contains no password; a note says it travels via the
   `UFT_MIGRATE_ALM_PASSWORD` environment variable; Copy Command works.

**TC-17 — Diff viewer**
1. Step 6: *Compare Converted Output…*; pick a converted `Script.pts`. For
   an ALM run it is under
   `out\<run id>\alm_aom_work\test_<id>_build\<Test name>\ActionN\`.
2. PASS: for a filesystem run the original VBScript usually pairs
   automatically. For an ALM run it does not, so browse to the original
   `Script.mts` under
   `out\<run id>\alm_aom_work\alm_rollback\test_<id>_source\` — the frozen
   pre-conversion copy. Use the asset note "Action directories renumbered by
   the rebuild", if present, to pick the matching action folder: `Action2`
   in the build is not necessarily `Action2` in the source.
3. PASS: changed lines are shaded, and the generated text at the top has no
   left-side counterpart by design: the `# _phoenix_library_binding`
   prelude when the test links a function library, then the
   `# _phoenix_vb_runtime` loader when `PhoenixVBRuntime.pfl` is related to
   the test, otherwise the pasted compatibility helpers.

**TC-18 — Custom mapping rules**
Custom mapping rules run against the line the converter has already turned
into Python, not against the VBScript source. Write the pattern against the
Python.
1. Step 3: *Edit Custom Mapping Rules…*; enter pattern
   `\bWaitSeconds\((\d+)\)` and replacement `Wait(\1)`, click **Add /
   Update Rule** so the pair appears in the list, then click **Save to
   <config file name>** (it reads `phoenix_config.json` when no config file
   has been selected yet).
2. PASS: an invalid regex is rejected with the parse error on Add / Update
   Rule; the valid rule saves into the config file and the wizard now points
   at that file.
3. Re-run a **Deep** analysis (or the conversion) over a test whose
   VBScript contains `WaitSeconds 5`. A Standard analysis writes no
   converted script, so there is nothing to inspect after it.
4. PASS: the built script contains `Wait(5)`. For an ALM run, read
   `out\<run id>\alm_aom_work\test_<id>_build\<Test name>\<Action>\Script.pts`.
   (A pattern written against the VBScript form, such as
   `\bWaitSeconds\s+(\d+)`, never fires: by the time rules run the line is
   already `WaitSeconds(5)`.)

**TC-19 — Failed-only re-run**
Re-create TC-09's condition on one disposable test and run a fresh Deep
analysis for it. (If you are running the plan out of order, you can instead
use TC-09's own Deep analysis, before the clean-up step ahead of section E
removes that test.)
1. Confirm the Deep analysis recorded that test as failed. Depth matters: a
   Standard analysis does not evaluate `Parameter()` definitions, so the
   test would read `ok` and this case would prove nothing.
2. Remediate the blocked test (add the missing parameter definition at
   action or test level in UFT, or replace the read with a
   DataTable/Environment lookup).
3. Keep Analysis Depth = **Deep** on Step 5 and click *Re-analyze Failed
   Assets (N)*. CLI equivalent: `convert --alm --dry-run --failed-only
   --analysis-depth deep --run-id <same id>` plus the usual connection
   arguments.
4. PASS: only the previously-failed assets are re-analyzed, every other
   asset's result is carried forward from the previous analysis, and the
   remediated test now analyzes `ok`. (`--failed-only` applies to ALM
   analysis only; ALM conversion is whole-project and cannot run a subset.)

## H. Reporting

**TC-20 — Executive summary rollup**
1. Open `executive_summary.html` from a completed conversion run (Step 6 →
   Run Outputs → Executive Summary HTML). Analysis-only runs on Step 5 do
   not write one.
2. PASS: it carries the approval badge ("Ready to approve conversion
   program" or "Approval pending remediation") and a Readiness card
   (ready/hold), and the Next Steps list matches the actual failure counts.
3. PASS: the Detail Reports links work. On an ALM run they are the scan
   report, the analysis asset pages (Failed assets, All assets, Out of
   scope) and, when the run wrote one, the pre-flight gate report. On a
   filesystem run they are the scan, conversion and validation reports; the
   ALM path does not produce convert or validation reports.

## I. Version control and locks

Run these two cases against a **version-controlled** ALM project.

**TC-21 — Foreign checkout converts from latest checked-in version**
1. Have a second user check out one test and leave uncommitted edits, then
   stay connected or not (the checkout itself is what matters). Run a real
   conversion (as TC-11) with an account holding the ALM "Manage
   checkouts"-equivalent permission.
2. PASS: the pre-existing checkout is undone (the server reverts to the
   latest checked-in version — the uncommitted edits are not converted);
   the asset is freshly checked out, converted, uploaded, verified, and
   checked in only after verification passes. The test ends **checked in**
   as a new version, with prior versions intact in ALM version history (the
   rollback path). Linked `.pfl` function-library resources go through the
   same check-out/check-in cycle. At the pre-flight gate the foreign
   checkout is recorded only as a warning; it does not stop the run.
3. Repeat with an account lacking that permission.
4. PASS: the conversion stops at that asset with status `vc-blocked`
   ("Version control blocked"). ALM conversion is all-or-nothing, so the run
   aborts: assets already uploaded in this run are restored from their
   pre-conversion snapshots (status `rolled-back`), the remaining assets are
   recorded `not-attempted`, and the run reports failed. Confirm that no
   asset shows `rollback-failed`; any that does is still converted on the
   server and must be restored with `uft-migrate restore` from the frozen
   snapshot before the project is used — and, as TC-09 step 4 notes,
   `restore` does not revert the resource relations the conversion changed.

**TC-22 — Locked asset is converted and overwritten, holder named in the audit**
A lock never fails a conversion. This case verifies that contract, so run it
only against disposable assets: it deliberately overwrites the work of the
session holding the lock.
1. Have another ALM session hold a lock on one test (e.g. open it from a
   second ALM login and leave it open); run a real conversion (as TC-11).
2. PASS: the pipeline allows a 10-second grace period, attempts to release
   the lock, and then converts the asset either way — it uploads and passes
   post-upload verification like any other test, and ends `ok`. The run does
   not fail, and no asset carries a `locked` status (there is no longer one).
   Other assets are unaffected.
3. Read that asset's notes in `alm_aom_results.json` and the run log.
4. PASS: the run recorded either `entity-lock-force-revoked` — the lock's
   row was deleted from the project's `LOCKS` table through the OTA
   `Command` object — or `entity-lock-not-cleared-proceeding`, where that
   object is unavailable (ALM disables it by default, so this is the
   expected outcome at most sites). How much the note can say depends on
   which path ran: the machine, ALM session id, lock time and last-active
   time come from the `LOCKS` table, so they appear only when that table was
   readable — normally the force-revoked path. On the not-cleared path the
   note names only the holding user, taken from the entity's own lock owner,
   or reads "holder unknown" when ALM does not expose one. The two paths word
   the outcome differently: on the not-cleared path the note adds that the
   asset was converted and overwritten anyway because the file upload is not
   lock-gated, and that ALM refused only entity metadata writes; on the
   force-revoked path it records that the lock was revoked so the asset could
   be converted. Either way the asset ends `ok` and the overwrite stands.
5. Back in the holding ALM session, close and reopen the test.
6. PASS: the test is the converted Python version — the holder's
   in-progress edit was overwritten, and their client was holding a stale
   copy until reopened. This is why conversions run in an agreed window
   with the project empty.

---

## Suggested sign-off matrix

| Area | Cases | Sign-off |
| --- | --- | --- |
| Environment | TC-01–02 | |
| Console basics | TC-03–04 | |
| Analysis | TC-05–06 | |
| Safety rails | TC-07–10 | |
| Conversion | TC-11, TC-11a, TC-12–13 | |
| Execution | TC-14 (CLI-only, optional), TC-14a, TC-15 | |
| Power features | TC-16–19 | |
| Reporting | TC-20 | |
| Version control & locks | TC-21–22 | |
