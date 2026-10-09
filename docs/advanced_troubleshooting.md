# Advanced Troubleshooting Guide

This guide is for support engineers and migration leads diagnosing failures
that survive the basics in [troubleshooting.md](troubleshooting.md). It
covers ALM storage internals, UFT runtime behavior, and the forensic use of
run artifacts. Field-by-field GUI reference:
[gui_field_guide.md](gui_field_guide.md).

---

## 1. The anatomy of a "converted test that won't run"

A converted test can be **verified perfect on the server and still not
execute** — because ALM stores a test as two loosely-coupled layers:

1. **ExtendedStorage** — the file tree (`Test.tsp`, `<name>.usr`,
   `Action*/Script.pts`, resources). This is what Phoenix uploads and what
   post-upload verification byte-compares.
2. **The asset model** — `USER_ASSETS` owner records and Asset Repository
   Item (ARI) rows that tell UFT *which files belong to which action*. This
   is what UFT's run-time extraction actually follows.

When the two disagree, UFT synthesizes a placeholder script:

> `'This script was created by UFT because the script that was previously
> saved with the test could not be found.`

and the run fails at "line 1" with `SyntaxError: unterminated string
literal` (the placeholder's own apostrophe). **Any run failing at line 1
with that text is a storage/asset-model problem, never a converter
problem.** Work through the causes below in order.

### 1a. Shared asset ownership (copy/pasted tests) — status `shared-assets`

ALM's clipboard copy/paste creates tests whose asset model still points at
the **source** test — the copy has its own ExtendedStorage but *shares* the
original's owners. Converting such a test can never work: uploads land in
the copy's storage while UFT runs the owner's scripts.

Phoenix detects this before converting (the download manifest's TEST owner
id doesn't match the test) and refuses with status **`shared-assets`**,
naming the owning test. This stop is deliberate and cannot be overridden.

Fix options:
- re-create the copy so it owns its assets: in ALM, paste it again with
  *create copies of related entities*, or in UFT open the source test and
  *Save As* a new ALM test — then re-run the analysis;
- if the copy is redundant, point its callers at the owning test and delete it
  before migrating.

Converting the owning test "instead" is not an available action: an ALM
conversion is whole-project, so the owner converts in the same run regardless,
and the copy is still disqualified at the pre-flight gate (§4), which refuses
the whole run. Parking the copy is not a fix either — the owner would still
convert, leaving a VBScript test whose actions are now Python. The failed-assets
page badges a `shared-assets` asset **do not park** and withholds it from the
one-click exclusion list for that reason.

Verification for the curious: the pre-upload staging download in
`out/<run>/alm_aom_work/test_<id>_source/Download.xml` lists the owners —
`<OwnerType>TEST</OwnerType>` with a different `<OwnerId>` is the smoking
gun.

### 1b. Shadow USER_ASSETS owners (stale `.mts` ARI rows)

On some ALM builds, uploading a `Script.pts` where the action historically
had `Script.mts` spawns a **second** (shadow) owner holding the `.pts` row,
while the original owner — the one UFT follows — keeps its stale `.mts`
row. The result is the placeholder above even though the storage is
correct.

Phoenix repairs this automatically during upload: it purges stale
`Action*/Script.mts` sidecars from the server and rewrites the ARI
`ARI_PATH` rows on **every** owner (resolved from the download manifest)
from `.mts` to `.pts`. The run notes show the outcome:

```
VBScript sidecar purge: status='purged' purged=2
ARI ownership sync (.mts -> .pts): status='updated' updated=2 owner_resolution='download-manifest'
Missing action-owner creation: status='created' created=['Action3 (desc=…, rows=4)'] errors=0
```

(`status='unchanged' created=[] errors=0` on the last line is equally normal —
it means every action already had an owner.)

- `status='skipped'` on the sidecar purge means the storage could not be
  probed (unreachable ServerPath, no Load) — the server state is *unknown*,
  not verified clean.
- `owner_resolution='asset-repository-items'` means `Download.xml` was missing
  or listed no action owners, so the fallback lookup supplied them.
- `status='skipped'` on the **ARI sync** means no action owner could be
  resolved at all. This is **not** benign. The asset-repair gate fails the
  asset (`asset-repair-failed`, see §1f), the whole conversion aborts, and
  every asset this run uploaded — including this one — is restored from its
  frozen snapshot. A test with no asset model at all therefore cannot be
  converted in place: re-create it by saving it from UFT into ALM, check that
  the connected user may modify test assets, then re-run the conversion.

### 1c. Stale UFT test cache (TD_80)

UFT extracts ALM tests into `%LOCALAPPDATA%\Temp\TD_80` to run them. After
a re-upload or a revert, a stale cache entry makes UFT run the **old**
build — symptoms include the placeholder above, or Python-era errors from a
test you reverted to VBScript (`Cannot use parentheses when calling a Sub`).

Phoenix clears TD_80 **on the machine running Phoenix, for the account running
it**: before a conversion, after any conversion that wrote to ALM, and before a
standard analysis reads the tests. The Migration Console has no option to
disable this; on the CLI, `--no-purge-uft-cache` switches off the conversion
purges. Phoenix cannot reach the cache on any other machine, which is why a
separate Test Lab execution host needs a manual purge.

Before running the command: close UFT One and confirm no test is running on
that host (an open handle makes the delete fail partway and leaves a partial
cache). Run it as the Windows account that executes the tests —
`%LOCALAPPDATA%` is per user. It removes only UFT's local extraction cache;
UFT re-extracts each test on its next run.

```powershell
$p = "$env:LOCALAPPDATA\Temp\TD_80"
if (Test-Path $p) { [System.IO.Directory]::Delete($p, $true) }
```

### 1d. `.usr` name mismatch

The `.usr` file (and the name recorded inside `Test.tsp`) must match the
test. Phoenix names its AOM build directory after the test to guarantee
this. If you hand-build or hand-copy test directories, a mismatched `.usr`
name reproduces the placeholder failure.

### 1e. Orphan owners left by an earlier conversion

An owner whose every ARI script row names a file the new payload does not
contain is a leftover from a previous conversion. UFT follows that row at run
time, finds nothing, and writes the placeholder. The run reports it but does not
fail the asset:

```
Orphan action owners detected: 2 - these WILL fail at run time with UFT's
"script could not be found" placeholder. Not deleted: removing a USER_ASSETS
owner is destructive and un-rollbackable.
```

A matching `converter_findings` entry in `alm_aom_results.json` names up to four
of the orphan owners — owner id, `UAS_NAME` and up to four of the rows that
point nowhere. The count in the note is the true total. **The asset still
reports `status: ok` and `upload_verified: "ok"` and still fails the moment it
runs.** Phoenix never deletes a `USER_ASSETS` owner — the deletion is
destructive and cannot be rolled back — so this one needs a decision: back the
project up, then escalate with the run folder.

### 1f. The asset model was not repaired — `asset-repair-failed`

The payload uploaded, but the owner/ARI repair described in §1b did not run or
did not succeed: the ARI sync or the owner creation reported `error` or
`skipped`, the ARI sync reported `failed` or returned errors, actions were left
with no ARI row and no owner created for them, or owner creation returned
errors. Phoenix fails the asset closed rather than ship a test that verifies
clean and executes nothing. The `error` text begins:

> The upload landed but the ALM asset model was not repaired, so the test would
> not execute its converted Python: …

On an upload run that failure aborts the conversion and rolls back every asset
this run uploaded, so the asset's *final* status in `alm_aom_results.json` reads
`rolled-back` or `rollback-failed`. The `asset-repair-failed` status itself
survives in `error`, in `resume/alm_test_results.ndjson` and in
migration_log.txt. Check that the connected user may modify test assets, then
re-run the conversion.

---

## 2. UFT's pre-execution validator (false "unterminated string literal")

**UFT 26.1 only.** UFT 26.3's script engine (`bin\ScriptExeEngine.dll`) no
longer contains the template below, and the 26.3 validation run showed none of
these failures. The workarounds Phoenix applies are harmless on 26.3, so the
same converted test runs on both versions.

UFT 26.1's Python engine pre-scans scripts and, for any line it believes
calls a "test object method without parentheses", synthesizes:

```
raise SyntaxError('Line %d: Test object method called without parentheses () - %s')
```

The synthesized `raise` does not compile, so **any** flagged line — with or
without quotes in it — kills the whole action before a single step runs. It is
reported as `unterminated string literal` at the *flagged* line (not line 1 —
that distinguishes it from the placeholder in §1).

The validator's name list includes common property/method names (`Read`,
`Write`, `Close`, `Value`, `Name`, `Activate`, …) and it flags them
textually, even in ordinary Python attribute access.

What Phoenix already does about it:
- routes FileSystemObject / TextStream calls and `.Value` assignments
  through `getattr`/`setattr` so the tokens never appear textually;
- hides `ExpandEnvironmentStrings` calls behind `getattr` — measured, this
  name kills the action whatever the receiver, the parentheses or the argument
  text, and passes untouched inside a string literal;
- rewrites bare `.Count` reads on collections to `_phoenix_prop(obj, "Count")`,
  which invokes the member only if the engine bound it as a method;
- rewrites member assignments on UFT's reserved objects (`Setting`,
  `DataTable`, `Environment`, `Reporter`, `SystemUtil`, …) to
  `setattr`/`_phoenix_setitem`, so no reserved member sits in assignment-target
  position;
- enforces parentheses on known UFT methods (extendable via **Custom UFT
  Methods** in the GUI);
- converts each linked library once, **in full**, to a shared Python Function
  Library (`.pfl`) and links it (`Settings.Resources.Libraries`) — never
  inlined, and never edited by function name.

No function defined in your own libraries is rewritten, renamed or deleted to
satisfy the validator; that is a standing prohibition in the converter.
Name-keyed rewrites are legitimate only for genuine VBScript/UFT object-model
members. The `.qfl` source is never written to either: the Test Resource
(function-library) upload path refuses outright any file name ending
`.qfl`/`.vbs`/`.mts`/`.tsp`/`.usr`/`.tsr` — conversion reads sources and writes
only converted products (`.pfl`). That refusal guards the *resource* upload
only; the test payload goes up a different path (`ExtendedStorage.Save` over the
AOM build directory), which is how the AOM-built `Test.tsp` and `<name>.usr`
reach the server on every conversion (§1, §5).

If you hit a new instance: note the flagged line from the run report, and
either add the method name to Custom UFT Methods (if it needs parentheses
enforced) or report it — the getattr-wrapping list is extendable. Do not
hand-edit the `.pts` on the server.

---

## 3. Test Lab execution environment failures (CLI-only support tooling)

Post-upload execution is no longer a GUI option: it is driven by the CLI
support lever `--run-via-alm` (with `--alm-test-lab-folder`,
`--alm-test-set-name`, `--alm-host`, `--uft-timeout`). This section applies
when a support engineer runs converted tests through that lever, or when your
team executes them from ALM Test Lab directly.

There is no local-execution lever: `--run-uft` was removed and now refuses
itself (exit 2) rather than running nothing quietly. If you want to verify a
single converted test without a Test Lab set, open it in UFT One and run it —
the symptoms below (locked desktop, unidentifiable AUT window, empty step
tree) apply to that manual run too.

| Symptom | Cause | Fix |
| --- | --- | --- |
| Run fails immediately: "computer is locked or logged off" | The execution host's desktop session is locked/disconnected — GUI automation needs an interactive desktop. | Keep the RDP session **active** during runs (or use a console session / auto-logon lab host). |
| `Cannot find the "X" object's parent "Y"` at the first GUI step | The AUT window isn't identifiable: app didn't launch, launched on a hidden/locked desktop, wrong resolution, or a stray previous instance holds state. | Verify the AUT launches manually in that session; kill stray AUT processes; check screen resolution matches the object repository's expectations; re-run. Compare against the VBScript baseline — if VBS fails at the same step, the environment (not conversion) is the cause. |
| Run "Passed" but no test steps in the report | Zero-script-steps execution (see §1). Phoenix flags this as `incomplete-execution` when expected actions are missing from the report. | Treat as §1; never accept a "Passed" with an empty step tree. |
| Every test times out | UFT license dialog or modal blocking on the host; or `--uft-timeout` is below real test duration. | RDP in and look at the screen; clear the dialog; raise the timeout. |
| `SystemUtil.Run` fails with `0x-7ffdfff7` | The launched path does not exist on the execution host. | Phoenix does not rewrite path literals: a surviving `HP\`, `HPE\` or `Micro Focus\Unified Functional Testing` prefix is the source test's own text and is intended behaviour, not a converter gap. Correct the path in the source test, install the application there, or supply a custom mapping rule (a regex substitution applied during conversion). |

---

## 4. Blockers, overrides, and what they actually mean

The ALM pipeline is **fail-closed**: a test whose conversion produced
blockers is refused (`status='blocked'`) before any ALM write. The result
JSON lists every blocker. Unsupported-construct blockers cite their source
line; the others name the action, the cross-test reference or the error
instead. Categories:

- `execute` / `eval` — dynamic code; no safe automatic translation exists.
- `executefile` — dynamic library loading from script. Blocked on the
  statement alone, whether or not the same library is *also* linked as an ALM
  Test Resource: the converter has no ALM context to check linkage with, and
  no safe automatic translation exists. (ALM uploads are forced to `strict`, so
  it always blocks there. Local `standard` records the blocker but does not
  refuse the test: it replaces the statement with a `# SKIPPED unsupported
  executefile:` comment, notes `OVERRIDE: proceeding despite N blocker(s)`, and
  builds and publishes anyway. Local `permissive` emits a run-time
  `NotImplementedError` stub instead.) Fix it in the source: make sure the
  library *is* linked to the test as a Test Resource — a linked `.qfl` is
  downloaded, converted once to a Python Function Library (`.pfl`), linked to
  the test, and loaded into every action's namespace, so its functions are
  callable with no `import` — then delete the `ExecuteFile` line and re-run.
- `exit_for` / `exit_do` — an `Exit For` or `Exit Do` whose innermost enclosing
  loop is of the other kind (an `Exit For` inside a `Do` nested in a `For`, or
  the reverse). Python's `break` would leave the wrong loop, so the statement is
  blocked rather than mistranslated. Restructure the loop in the source test.
- `Parameter() references [...] not found among the legacy test's action or
  test-level parameter definitions` / `Parameter() referenced but no parameter
  definitions (action or test-level) were found on the legacy test` — the
  script reads a parameter name that is defined **nowhere** on the legacy
  test. Both action-level parameters (Action Properties → Parameters) and
  test-level parameters (File → Settings → Parameters) are harvested via UFT
  and re-authored on the converted test; test-level definitions also satisfy
  `Parameter()` reads in the main flow (Action0), which has no parameter
  surface of its own. Add the missing definition in UFT at either level, or
  replace the read with a DataTable/Environment lookup, and re-run. Test-level
  default *values* are carried, but test-set runtime overrides do not
  propagate through the AOM main-flow indirection.
- `linked function libraries could not be resolved` — the resource link
  exists but the download failed (permissions, deleted resource). Fix the
  resource, re-run.

Searching the results JSON: the local filesystem path emits the same two
`Parameter()` conditions with slightly different wording (`... not found among
the local test's action or test-level parameter definitions`, and
`Parameter() referenced but no parameter definitions were found`). Both paths
emit a third, distinct blocker when the harvest itself fails — `Parameter()
referenced by [...] but harvesting definitions from the legacy/local test
failed: <error>` — which is a retryable tooling failure, not a remediation
item in your test.

`--allow-blockers` (CLI-only — the GUI checkbox was removed; the GUI flow is
fail-closed, with Step 5 parking for deferrals) uploads anyway and records the
override in the run notes. Legitimate uses are narrow: blocked lines you have
verified are unreachable (dead debug branches).

Never use it to "get the numbers green". ALM conversions always run at
`strict`, and at `strict` an overridden `Execute`, `Eval`, `ExecuteFile` or
mis-nested `Exit For`/`Exit Do` statement is uploaded as a comment
(`# BLOCKED: unsupported <kind> -> <source>`). It does nothing at run time, so
the test can **pass** while silently skipping that logic — or fail later with a
`NameError` for something the skipped code would have defined. A `Parameter()`
or unresolved-library blocker behaves differently: the line is written out
unchanged onto a test that has no matching definition (or no library), so it
fails at run time instead.

Three stops sit outside `--allow-blockers` entirely, because each is a
data-integrity stop rather than a quality gate — the override exists for
constructs an expert knowingly accepts, not for output that cannot execute:

- **`shared-assets`** (§1a) — not a blocker at all; a pre-conversion refusal
  with no override.
- **`converted output is not valid Python`** — the syntax gate. If any
  converted action fails to parse, the test is refused (`status='blocked'`)
  even with `--allow-blockers`, on both the conversion path and
  `convert --alm --dry-run` analysis. Such a test would upload clean, verify
  clean, and die at run time.
- **An un-retargetable cross-test reference** — a shareable-action reference
  that cannot be safely translated to the converted callee's renumbered
  layout, refused on the conversion path (analysis is exempt: nothing uploads,
  so the server keeps the callee's original layout). Building anyway would
  natively bind the caller to the **wrong** callee action.

`--allow-blockers` covers only the construct blockers listed above.

### The all-or-nothing pre-flight gate

Separately, every ALM conversion first re-reads the signed-off analysis in its
own run folder and judges the **whole** selection before the first ALM write. If
any in-scope asset is disqualified, the run is refused with status
`preflight-failed` and nothing is written. Disqualified means:

- an analysis status other than `ok` — for example `blocked` without
  `--allow-blockers`, `shared-assets`, or `error`;
- converter blockers on an otherwise-`ok` asset (`converter-blockers`) — the
  analysis was run with `--allow-blockers` and the conversion was not;
- no analysis record at all (`not-analyzed`), or a record the run's discovery
  did not return (`analyzed-but-not-selected`);
- a cross-test reference that cannot be retargeted: `unresolved-callee`,
  `ambiguous-callee`, `self-referencing-callee`, `reference-cycle`, or
  `callee-disqualified` (a caller whose callee is itself disqualified).

`alm_preflight.json` names every disqualified asset with its reason code and
detail. Foreign checkouts and locks are only **warnings** here; a foreign
checkout becomes `vc-blocked` later, during the upload, which aborts the run.

Discovery, which hands the gate its selection, fails closed too. It walks the
whole Test Plan, and any fault while it lists a folder or reads a test stops
the run with *ALM discovery failed: …*, naming the folder and the step, instead
of returning a shorter list as if it were complete. It then checks the walk
against the project's own list of tests, which catches a server that answers
short without an error. A conversion's discovery that fails — reaching the
server, opening the domain or project, reading the Test Plan — whose process
crashes or hits its 600-second limit without an answer, or that comes back
without assets the signed-off analysis covered — less those parked with
`--alm-exclude-test-id` and those the path exclusions remove — runs once more,
a minute later, in a new process with a new ALM session. It logs the warning
`alm-discovery-retried` with a `reason` (which names the exit code or the time
limit for a process that died), the first count, the missing ids and the
error, and a progress line announcing the wait. The gate then judges the
second answer, never a union of the two, which could bring back a test deleted
in between: assets still missing are refused as `analyzed-but-not-selected`.
An analysis has no signed-off scope to compare with, so it retries only a
discovery that failed or died. A discovery whose Login was refused is never
retried: a second try at a wrong password is a second failed login, which an
account lockout policy counts. In a conversion that continues an unfinished
wave, a discovery that still fails stops the wave (`discovery-failed`, §9)
instead of failing the run.

The CLI-only `--allow-partial-conversion` overrides this gate and converts the
eligible assets anyway. It knowingly leaves the project part Python and part
VBScript, and records every skipped asset as a `preflight-disqualified` failure.
Treat it as a last resort.

---

## 5. Reading the run artifacts like a support engineer

Everything lives under `out/<run_id>/`, in the folder Phoenix was launched from
(the Start Menu shortcut starts in your user profile, so that is where the `out`
folder appears). `--output-root` moves converted output, not the run folder.

| Artifact | What to look for |
| --- | --- |
| `alm_aom_results.json` | Per-test truth: `status`, `error`, `blockers[]`, `converter_findings[]`, `uploaded`, `upload_verified` (`ok`/`mismatch`/`failed`), `rollback_status`, `resumed` (an earlier run of this run id already converted it and the server still holds the Python), `wave` (the conversion wave, §9), `crash_recovery` (what crash recovery did around this test; the same lines open its `notes[]` with `[crash recovery]`), the run's `discovery` block (`retried`: whether discovery ran a second time; `unplaced_tests` / `unplaced_test_ids`: tests ALM lists that discovery could not place in a Test Plan folder, which the executive summary's Next Steps name), `runtime_helper_blocks`, `test_lab_run_id`/`_status`, and `notes[]` — the chronological story of each test. A gate rehearsal (`--upload --dry-run`) never writes this file, so during a rehearsal it still holds whatever the prior analysis left there. Neither does a conversion that stopped and stayed open to resume (`alm_wave_stop.json`, below). Start here. |
| `migration_log.txt` | JSON-lines event stream with timestamps — the cross-test timeline. Search for `"level": "error"` first (pre-flight refusals, run aborts, failed assets, upload-verify and rollback failures, failed ALM reconnects, native crashes of the conversion process and crash recovery that stopped — `alm-crash-detected`, `alm-crash-budget-exhausted`, `alm-crash-recovery-gave-up`, `alm-crash-wave-abort` — and stopped conversion waves, `alm-wave-stopped`), then `"level": "warning"` (transient retries, session reconnects, lock revocations, per-asset rollback outcomes, the cleanup and relaunch after a crash, the check of the test a crash left in flight — `alm-crash-reconcile-*` — a wave's copy of a test frozen again because the test changed in ALM before the wave wrote it, `alm-wave-snapshot-refrozen`, an unfinished wave that had written no test closed for a launch with other inputs, `alm-crash-wave-superseded`, a continued wave that skipped the pre-flight gate, `alm-preflight-skipped-wave-resume`, a discovery that failed while reading the Test Plan, died without an answer or came back short and ran a second time, `alm-discovery-retried`, and tests the project's list holds that the walk did not return and whose folder could not be read, `alm-discovery-folder-unreadable`). Each discovery that reached the Test Plan also logs one `alm-discovery-walk` info line: the start folder, the folders walked, the tests seen of every type in each top-level folder, the skips it counted, the check against the project's test list and, for a failed discovery, the error. In PowerShell: `Select-String -Path migration_log.txt -Pattern '"level": "error"'`. |
| `alm_preflight.json` | The pre-flight verdict, written on every conversion run: `status` (`pass`/`fail`), the selected and eligible ids, and every disqualified, out-of-scope and warning asset with its `reason_code` and detail. When `status` is `fail`, no ALM write happened (§4). A conversion that continues an unfinished wave does not run the gate again (§9); it writes back the gate report the wave started under, which the wave recorded in the journal. |
| `resume/alm_test_results.ndjson` | The durable conversion journal — one JSON line per event, each written as it happens. Since 1.1.5 the records of an upload conversion also carry its conversion wave id (`wave`). The `record` field: per asset `intent`, `attempt`, `terminal`, `already-converted` and `resume-mismatch`; the write markers `upload-started` (written to disk *before* the first write of a test's payload — no marker means that write never started), `upload-saved` and `upload-verified`; the abort and rollback records `aborted`, `not-attempted`, `rollback-started`, `restore-started`/`restore-done`, `rollback-asset-done`, `rollback-finished` and `rollback`; crash recovery's `crash`, `budget-exhausted`, `reconcile-untouched`, `reconcile-vc-undo`, `legacy-in-flight-verified`, `operator-settled` and `wave-snapshot-refrozen`; the wave's own `run-start`, `run-end`, `run-result`, `wave-start`, `wave-attempt`, `attempt-end`, `attempt-interrupted`, `wave-phase` and `wave-end` (whose `outcome` says how the wave closed — `superseded-no-writes`, for example, for an unfinished wave that had written no test and was replaced by a launch with other inputs); and `session-lost`/`session-restored`/`session-reconnect-failed`. A write that another program blocks for a moment — a backup or sync agent, an antivirus scanner — is retried for about 8 seconds. It survives a killed run, and a re-run of the same run id reads it to continue an unfinished wave and to skip assets that are already converted. The `terminal` record also carries the test's path and name and its converted action layout (`action_renumber_map`, `action_name_folders`, `action_folder_has_code`, `function_library_links`), which is what lets a skipped asset still serve as a callee for the tests converted after it. A journal written by an earlier version of Phoenix lacks those fields, and a caller of an asset carried forward from one blocks with `that callee has no conversion record in this run` (see [troubleshooting.md](troubleshooting.md)). Read it first after an interrupted conversion. In PowerShell: `Select-String -Path resume\alm_test_results.ndjson -Pattern '"record": "terminal"'`. |
| `alm_aom_work/test_<id>_source/` | The test as downloaded by the **latest** attempt in this run folder. It is deleted and downloaded again on every attempt, so after a re-conversion it can hold the converted Python. Contains `Download.xml` (asset-owner manifest, §1a). |
| `alm_aom_work/alm_rollback/test_<id>_source/` | The first-sight pre-conversion payload, written once on the first non-dry-run attempt in this run folder and never touched again. The copy lands under a temporary name and is renamed into place only once complete, so a copy cut short by a crash never looks complete. In an upload conversion it is made from the wave's copy (next row) as hard links where the disk allows, so it takes no extra space. `uft-migrate restore` without `--wave` puts back **this** copy; treat it, not `test_<id>_source`, as the original. A real conversion and a **deep** analysis (which AOM-builds every test) both create it; a standard analysis and a `--dry-run` rehearsal do not. |
| `alm_aom_work/alm_rollback/waves/<wave>/test_<id>/` | The copy one conversion wave froze of the test before it changed the test: `payload/` (exactly what the wave's first download held) and `manifest.json` (every file with its size and SHA-256, written last — a folder without it is a copy that never finished and is never used). Crash recovery, the wave's automatic rollback and `restore --wave` restore only from this copy, never from an older one. A `test_<id>.tmp-…` folder is a copy that died half-way; the next attempt deletes it. A `test_<id>.superseded-<time>` folder is a copy set aside — by `restore --accept-current-state`, or because the test changed in ALM before the wave wrote it and the wave froze it again. When a new wave starts, the copies of older waves that are closed and settled (§9) are deleted, except those of the newest one that wrote a test; a wave that wrote no test — a launch the pre-flight gate refused, for example, or one that only replaced function libraries, which the journal does not record — does not count, and its own copies go once a newer wave that wrote a test has finished. Only an upload conversion freezes these. |
| `alm_aom_work/alm_rollback/resources/<wave>/<id>/` | The bytes of each `.pfl` function library that conversion wave `<wave>` replaced while converting test `<id>`. The first copy the wave saves is kept; when a later attempt of the wave replaces bytes that differ from it, those bytes are kept beside it in a `replaced_<UTC time>_…` folder — and so are those of a second library of the same file name that the test links from another folder, since the first copy is kept by file name. Either way the per-asset note `EXISTING CONTENT REPLACED — prior copy saved to <path>` names the copy of exactly the bytes that write replaced. These copies are deleted with the wave's test copies (row above). |
| `crash_breadcrumbs.log` | One JSON line written immediately before each ALM call of an upload or a restore, and around each AOM build (§9). The last line for a process that died names the step it died in. |
| `crash_recovery/<wave>/` | What the crash supervisor kept for one conversion wave (§9): per attempt `attempt_NN/` with `command.txt` (the password masked), `stdout.log` and `stderr.log`, plus, after a native crash, `crash.json` and a copy of Windows' `Report.wer` when Windows wrote one; the wave's `supervisor.log`; and `restore_commands.txt` when recovery stopped with tests still to restore. Crash dumps are never copied here. A wave that completes without a crash keeps only `command.txt` and `supervisor.log`, and only the newest two finished waves that wrote a test keep their folder (a wave that wrote no test does not count, even if it replaced a function library: library writes are not journaled); an unfinished wave always keeps its own. |
| `alm_wave_stop.json` | Written when a conversion wave stops and stays open (§9): the reason, the test, the copy to restore from and the next steps. The report set is left as it was. Deleted when a later upload conversion in this run folder ends without stopping. |
| `resume/alm_wave.json`, `resume/phoenix_run.lock` | A summary of the latest wave, written by the crash supervisor (the journal, not this file, decides everything), and the run-folder lock: while one Phoenix process converts, analyzes or restores an ALM project in a run folder, another such process is refused there. |
| `alm_aom_work/test_<id>_build/<TestName>/` | The AOM-built payload that was (or would be) uploaded. The converted Python is human-readable in the `Action<N>/Script.pts` files: `Action0` is the main flow, and `Action1` holds a source action only when that action was itself named `Action1` (about 60% of the reference estate) — otherwise the AOM's inert default is removed and the named actions occupy `Action2..N`, usually leaving no `Action1/` at all. Read the `.usr` `[Actions]` section for the name→folder map rather than assuming the numbering. |
| `alm_aom_work/test_<id>_verify/` | The post-upload re-download used for byte verification. |
| `alm_aom_work/test_<id>_runresults/.../run_results.xml` | Test Lab run detail: `<ErrorText>` nodes carry the real failure; `<Parameter name=... value=...>` proves parameter delivery at run time. |
| `executive_summary.html` | The verdict + next-steps rollup with drill-down links. |
| GUI runs: `analysis_cli_*.log`, `run_cli_*.log` | Raw engine output as the console saw it. For an ALM conversion, `run_cli_stderr.log` also carries the crash supervisor's own lines, which start `[Phoenix crash supervisor]`; each attempt's own output is also kept in `crash_recovery/<wave>/attempt_NN/` until the wave completes without a crash. |
| `%LOCALAPPDATA%\Merito\UFT Phoenix\logs\*.ndjson` | Outside the run folder: one diagnostics log per process, named `<start time>_<role>_<pid>.ndjson`. Roles are `gui`, `cli` (it becomes `supervisor` when it supervises a conversion), `worker`, `collector`, and `build-child`, `analysis-child` and `discovery-child`, which write a file only once they have a warning or an error. Each line is one record: the envelope `timestamp_utc` (milliseconds), `level`, `event`, `role`, `pid`, `seq` (a gap is a lost record), `thread` off the main thread, and `ctx`, the bound context (`run_id`, `wave`, `attempt`, `test_id`, `step`, `retry`). `process-start` says which build ran (`phoenix.version`, `.commit`), on which Python, with or without a console, and with which crash settings; `run-bind` links the process to its run folder; `step` is each breadcrumb at millisecond resolution; `child-start`/`child-exit` name each child process and how it ended; `exception` and `swallowed` carry the error in full (next row); the `alm-*` events are copies of `migration_log.txt`'s warnings and key events, which survive when that file is cleared. The ALM password is masked before anything is written. Search them like `migration_log.txt`: `Select-String -Path "$env:LOCALAPPDATA\Merito\UFT Phoenix\logs\*.ndjson" -Pattern '"level": "error"'`. |
| Error ids `E-<time>-<pid>-<seq>` | The `error_id` of an `exception` or `swallowed` record. It is copied to where the failure shows: the CLI's failure result (`error_id`), the crash supervisor's failure result (`error_id`; its message itself names no id), the journal's `attempt` and `terminal` records, `alm_aom_results.json` (`error_id`, and `error_ids` for errors an asset carried on past) and the `alm-test-processing-completed` event. A test whose isolated AOM build failed (`aom-build-failed`) carries the id of the build child's own record. `error_ids` names only records written in full: a process writes the first 3 of one swallowed fault (its site and `fp`) in full and from then on only counts it, in `swallow-summary` records, which triage adds to the fault's scale. The record gives the exception type and message, every COM error in its chain (HRESULT, `scode` and the server's description), the innermost Phoenix frame that is not a generic helper (`where`) with its source line, the helper and the first frame outside Phoenix (`helper`, `boundary`), the COM member being read or called (`member`, `access`), the frames, and a fingerprint `fp` that stays the same for the same fault across retries and runs. Search for the id: `Select-String -Path "$env:LOCALAPPDATA\Merito\UFT Phoenix\logs\*.ndjson" -Pattern 'E-20261006T101500Z-7720-41'`. |

Standard triage: `alm_aom_results.json` status → that test's `notes[]` →
its `run_results.xml` `<ErrorText>` → the layer table in §1/§2/§3. With an
error id, start from its record in the process logs instead.

### Upload verification verdicts

The verdict is the `upload_verified` field in `alm_aom_results.json`, and the
matching note reads `Upload verification passed (re-download matches AOM
payload)`.

- `upload_verified: "ok"` — every built file round-tripped byte-identically
  and no stale test-definition artifacts remain. No server-side drift is
  tolerated: any file whose bytes differ after the round-trip is a mismatch,
  `Test.tsp` included. On the reference estate every uploaded file came back
  byte-for-byte, so a difference means the server did not store what was
  uploaded — in practice a renumbered action's `ObjectRepository.bdb` whose
  pre-conversion bytes were never overwritten. The `upload-verify:` notes name
  the file whose bytes were served instead.
- `upload_verified: "mismatch"` — files missing, stale artifacts present, or
  content drifted past the one automatic repair described below.
- `upload_verified: "failed"` — the verification re-download itself errored,
  so the server state is unverified. Treat it exactly like a mismatch.

Either of the last two fails the asset as `upload-verify-failed`, and that
**aborts the whole conversion**: later assets become `not-attempted`, and every
asset this run uploaded — including this one — is restored from
`alm_aom_work/alm_rollback/`. The asset's final `status` therefore reads:

- `rolled-back` — its **payload** is back on VBScript, but its resource
  relations are not. The asset that failed here was never re-pointed; an asset
  this run had already uploaded and verified has had each linked `.qfl` relation
  replaced by the converted `.pfl` (and, where its scripts install the VBScript
  compatibility helpers, a relation to `PhoenixVBRuntime.pfl`), and the rollback
  does not put that back. ALM delivers only *related* resources to Test Lab, so
  one of those restored VBScript tests reaches the execution host without the
  library it expects and fails on its library calls. Before running one,
  re-point its Test Resource relation to the original `.qfl` in ALM — or fix
  the cause and re-run the conversion, which converts it again and leaves the
  `.pfl` relation matching the payload.
- `rollback-failed` — it is **still modified in ALM**. Do not run it. Restore
  it with `uft-migrate restore … --wave <wave>` (the asset's `wave`; §9) or
  from ALM version history, and escalate with the run folder. Until it is
  restored or settled, its wave stays open and the next conversion in that run
  folder stops on it. `uft-migrate restore` puts back the files but not the
  resource relations, so the caveat above applies to it: check the test's Test
  Resource relations before running it, and re-point any that name a converted
  `.pfl` to the original `.qfl`.

`upload_verified` keeps its verdict either way, and the original
`upload-verify-failed` status survives in `error`, in
`resume/alm_test_results.ndjson` and in migration_log.txt.

Drift gets one automatic repair attempt before it condemns the asset: the
pipeline deletes exactly the drifted server paths
(`IExtendedStorage.Delete(path, 2)`), re-uploads, and re-verifies once,
recording `upload-verify: retried N file(s) the server did not overwrite
(delete + re-upload): <status>` and `upload-verify: re-verified after repair ->
<verdict>` in `notes[]`. Only drift that survives that single attempt — or a
repair that could not run — leaves `upload_verified: "mismatch"`.

---

## 6. OTA/COM environment quirks worth knowing

These are behaviors of the ALM COM API observed in the field that Phoenix
already accounts for — listed so a support engineer scripting around the
product doesn't rediscover them:

- `IExtendedStorage.Delete(path, nDeleteType)`: only `nDeleteType=2`
  (delete on client **and** server) reliably removes server files; `1` can
  be a silent no-op.
- `ExtendedStorage.Save` is **additive** — it never deletes server files.
  Stale-file cleanup must be explicit (Phoenix derives the deletion list
  from the pre-upload server listing, never guessed names).
- Creating asset relations requires `ASR_ORDER` on some servers even though
  the OTA documentation marks it optional.
- COM teardown noise (`Win32 exception occurred releasing IUnknown`) after
  a script finishes is cosmetic.
- The Test Plan is walked through `SubjectNode.NewList()`, which takes no
  argument (`NewList('')` raises *Invalid number of parameters*), and each
  folder's `TestFactory.NewList("")`. The general-purpose walk, which resolves
  a single asset, takes an error anywhere in it for "nothing there". Discovery
  makes the same calls strictly — an error stops it — and checks the result
  against `TDConnection.TestFactory.NewList("")`, the project's flat list. For
  a test in that list that the walk did not return, it reads the folder from
  `Field("TS_SUBJECT")`, which returns the folder node; a read that fails twice
  counts the test as unresolved (`alm-discovery-folder-unreadable`) instead of
  failing discovery, and after 20 such tests the rest are counted without
  being read. ALM's *Unattached* folder — a path of `Subject\Unattached`, or a
  folder `NodeID` of 0 or below — is outside the Test Plan for this check, even
  though the ALM client shows it under Subject. Folders are told apart by
  `NodeID`, so sibling folders whose names differ only in case are both walked.
- A `com_error` whose message is "The object invoked has disconnected from
  its clients" means the UFT/ALM client process died mid-call. If the ALM
  session drops *before* an asset's upload starts, Phoenix reconnects and
  retries that asset on its own (`alm-session-reconnect` in migration_log.txt);
  a drop after the upload has started aborts the run and rolls back. To carry
  on, re-run the conversion under the same run id (the Migration Console
  converts into the **Analysis Run ID**'s folder). An asset is skipped —
  `resumed: true`, reported `ok` — only when an earlier attempt recorded it as
  uploaded and verified, nothing recorded after that touched it again, **and**
  the server still holds its complete Python payload: no `Script.mts`, one
  `.usr` named after the test, a `Test.tsp`, and a `Script.pts` for every
  local action that `.usr` lists. Everything else is converted again,
  including assets an abort rolled back.
  A skipped asset still serves as a callee for the tests converted after it; the
  one exception, a journal written by an earlier version of Phoenix, is covered
  in [troubleshooting.md](troubleshooting.md) under *that callee has no
  conversion record in this run*.

---

## 7. IronPython runtime completeness

Converted tests execute in UFT's embedded IronPython 3.4. The UFT One 26.1
and 26.3 installers both ship it incomplete (missing `IronPython.Modules.dll`,
`Microsoft.Scripting.Metadata.dll`, and the `Lib\` standard library), which
surfaces as import errors at run time in otherwise-perfect tests.

`uft-migrate doctor` checks this explicitly. To repair, place the missing
files from the NuGet packages **IronPython 3.4.1**, **IronPython.StdLib
3.4.1**, and **DynamicLanguageRuntime 1.3.4** next to `IronPython.dll`
under the UFT installation, then re-run `doctor` until the check is green.
Do this on **every** machine that will execute converted tests.

---

## 8. Version-control internals (VC-enabled ALM projects)

On a version-controlled project, the per-asset conversion flow is:

1. **Clear any entity lock — best-effort, never a failure.** A 10-second
   grace period for the lock to clear on its own, then a release attempt,
   then the asset is converted and **overwritten** either way. An ALM lock
   does not gate `ExtendedStorage.Save` (the payload write: `Script.pts`,
   `Test.tsp`, `.usr`), only entity metadata writes (`SetField`/`Post`),
   which the upload path treats as optional. `UnLockObject()` releases only
   *your own* lock — against a foreign session it returns cleanly and does
   nothing, so the pipeline re-probes rather than trusting it; revoking a
   foreign lock means deleting its `LOCKS` row through the OTA `Command`
   object, which ALM disables by default. The run logs
   `entity-lock-force-revoked` (holder, machine, ALM session id, lock time and
   session last-active time) or `entity-lock-not-cleared-proceeding`. The second
   event carries the holder only as far as ALM exposes it — full lock-table
   detail when the `Command` object is available, otherwise at most the lock
   owner's user name — plus the reason the lock could not be revoked and the
   effect (content upload proceeds and overwrites; entity metadata writes are
   skipped).
2. **Undo any pre-existing checkout** — another user's or a stale own one.
   The server reverts the asset to its latest checked-in version, which is
   exactly what gets converted. Undoing another user's checkout requires
   the "Manage checkouts"-equivalent permission; without it the asset fails
   with status `vc-blocked` (report category *Version control blocked*).
3. **Check out fresh**, convert, upload, and verify.
4. **Check in only after post-upload verification passes**, with the
   comment "UFT Phoenix migration: AOM-canonical Python conversion
   (verified)".

**Abandon-on-failure:** any failure after checkout abandons (undoes) the
checkout, so the server keeps its last checked-in version — a failed
conversion never leaves a half-converted test checked out.

`.pfl` function-library resources (converted libraries, and
`Resources\UFT Phoenix\PhoenixVBRuntime.pfl`) are **not** held to that cycle.
Each is checked in as soon as its content is uploaded, with the comment "UFT
Phoenix migration: Python function library (.pfl) content" — before the test's
own AOM build, structure, carry-over, asset-repair and verification gates run.
A later failure of that test, or an abort rollback, does not revert the library.
When an existing library is replaced, the per-asset notes read `EXISTING
CONTENT REPLACED — prior copy saved to <path>`, and on a version-controlled
project the previous version also stays in ALM version history. Each
conversion wave keeps those copies in its own folder,
`alm_aom_work/alm_rollback/resources/<wave>/<test id>/`. The first copy the
wave saves of a library is never overwritten; when a later attempt of the same
wave — a crash relaunch, say — replaces bytes that differ from it, those bytes
are kept beside it in a `replaced_<UTC time>_…` folder. So `<path>` always
holds exactly the bytes that write replaced. The first copy is kept by file
name, so a second library of the same name that the same test links, from
another folder, is in a `replaced_…` folder too: go by the path the note
names, not by the folder. A wave's library copies are
deleted together with its test copies (§5).

Each successful conversion is a **new** checked-in version; the
pre-conversion version remains in ALM version history — a first-class
rollback path alongside the `restore` subcommand's run-folder snapshots.

In `alm_aom_results.json`, the status `vc-blocked` identifies these failures
(there is no `locked` status — a lock is recorded as a per-asset note, not a
failure), and each asset carries a `vc_state` field recording the
version-control and lock state observed for that asset.

**When ALM will not answer a version-control question.** Some servers refuse
individual version-control reads. On the first live run against a
version-controlled project (2026-10-05) the OTA client's
`VersionData.CheckedOutBy` failed with "Invalid field name
< TS_VC_CHECKOUT_USER_NAME >". A read like that no longer stops the
conversion. It is recorded in the asset's `vc_state` under `vc_read_errors`,
and `vc_state.vc_surfaces` lists which version-control surfaces the test
exposed. The checkout owner is then taken from the test's `VCS.LockedBy` (which
names the checkout owner, not an edit lock) or `VCS.CheckoutInfo`. If no
source can say whether the test is already checked out, `vc_state` carries
`checkout_state_unknown` and the pre-flight warns (`checkout-state-unknown`):
step 2 above — undoing a pre-existing checkout — cannot run, so a checkout
someone left in place makes the CheckOut fail and stops the conversion with a
`vc-blocked` message that says so. Check that test in, or undo its checkout in
ALM, and run the same command again. A checkout Phoenix took itself is always
checked in after verification, or undone after a failure, even when the
server cannot report it; the same holds for a restore, which is checked in
only when it completed and is undone otherwise.

---

## 9. Native crashes of the conversion process

A *native crash* is Windows ending a Phoenix process with an exception. It
shows as a very large exit code, for example `3221226505` (`0xC0000409`, a
fail-fast) or `3221225477` (`0xC0000005`, an access violation). The process
crashed rather than failing a check, so it leaves no Python traceback and no
result. The ALM client and Phoenix's COM calls into UFT run inside Phoenix's
own processes, and either can cause one.

**What Windows records.** Every Phoenix process asks Windows Error Reporting
(WER) to record a native crash without showing a dialog and without collecting
heap memory. An unattended run is never parked behind a "Python has stopped
working" box, and the crash still leaves evidence:

- **Event Viewer**, under *Windows Logs > Application*: events **1000** and
  **1001** at the time of the crash. They name the faulting module.
- **`Report.wer`**, in a folder named after the process under
  `C:\ProgramData\Microsoft\Windows\WER\ReportArchive` (or `ReportQueue`, or
  the same two folders under `%LOCALAPPDATA%\Microsoft\Windows\WER`) — for
  example `AppCrash_pythonw.exe_…` for a run started from the Migration
  Console, which runs on `pythonw.exe`; a command-line run uses `python.exe`.
  It names the faulting module and offset, and the fail-fast code.
- **A crash dump**, only where WER *LocalDumps* is configured on the machine:
  in `%LOCALAPPDATA%\CrashDumps`, or the folder LocalDumps names. It is named
  `<program>.<process id>.dmp`, and Windows keeps several, so a dump with the
  same name can be left by an earlier process that had the same id.

Phoenix does not change whether Windows sends reports to Microsoft; the
machine's WER consent settings decide that. On two kinds of machine Phoenix
falls back to switching crash reporting off for its processes, as before
1.1.5, and a crash then leaves no record: where Windows does not accept the
no-dialog request, and where a just-in-time debugger is registered to attach
automatically (`Auto=1` under the `AeDebug` registry key), which would
otherwise hold the crashed process behind a debugger prompt.

**What Phoenix does to make them less likely.** Every `uft-migrate` process,
and the build, analysis and discovery child processes it starts, keeps other
programs' global-hook DLLs out of itself (the Windows extension-point disable
policy; no administrator right needed). UFT 26.3 injects its agent DLLs into
any process that creates a window and services its messages, and the process
that holds the ALM session does both. The Migration Console process does not
get this policy: there it would also block legacy input methods. While a
conversion or a deep analysis waits for its AOM build child process, it keeps
its Windows message queue serviced, so work the ALM client queued during the
build is not all run inside the next ALM call — which is where the measured
crashes struck.

**Automatic recovery (ALM upload conversions).** A whole-project upload
conversion — `run` or `convert` with `--alm --upload` and no `--dry-run`, which
is what **Convert Project** runs — no longer runs in the process you start.
That process becomes a *crash supervisor*: it starts the conversion as a worker
process with the same command line and waits for it. An analysis, a gate
rehearsal and a filesystem run are not supervised. When the worker dies of a
native crash, the supervisor:

1. stops whatever the dead worker left running;
2. records the crash in the conversion journal
   (`resume/alm_test_results.ndjson`) — a crash it cannot record is never
   relaunched;
3. closes UFT and collects the Windows Error Reporting evidence, waiting up to
   15 seconds for Windows to write it;
4. starts the conversion again about 15 seconds later.

The new attempt settles what the crash left before it converts anything. A test
the crashed attempt may have half-written is compared with the copy this wave
froze before changing it: an identical server copy is left alone, a different
one is restored from that copy and verified, and either way the test is then
converted again. The comparison leaves out lock files (`*.lck`, such as
`Default.xls.lck`), which come and go from one download of a test to the next,
and `Download.xml`. The verification after any restore leaves out only the lock
files: `Download.xml` must come back, though its content may differ, and a
restore that does not put it back fails when the frozen copy has one. Tests already converted in this wave are carried forward, not
converted again. While this happens, the Migration Console's status line shows
the supervisor's latest message.

**The crash budget.** Recovery stops relaunching at the third crash while the
same test is in flight, at the sixth crash in the wave, or at the second crash
in a row that happened outside any test with no test finished in between.
The supervisor then starts the worker once more, in abort mode: it converts
nothing, marks the test that was in flight, if any, `process-crashed` (report
category *Crashed the conversion process repeatedly*), and rolls back
everything the wave wrote, callers first — tests converted by earlier attempts
of the wave included — from the wave's own copies. Each asset's status says
whether its restore worked (`rolled-back` or `rollback-failed`). When the
`process-crashed` test uses a function library — its own or
`PhoenixVBRuntime.pfl` — its notes add that its conversion may already have
created or replaced shared `.pfl` libraries, which no rollback reverts, and say
where the copies saved before they were replaced are, or that none were saved.
A wave with nothing to roll back — it wrote no test, or every test it wrote is
already back on its copy — is closed without an abort worker. The budget
belongs to the wave, so a later launch of the same wave starts in abort mode
too; if the abort itself crashes before its rollback starts, running the
conversion again retries it.

**What is never relaunched.** A worker that exits by itself, successfully or
not (a wave that stopped included); Ctrl+C or a closed console window; a
worker ended from outside, for example with `Stop-Process` (exit code
`0xFFFFFFFF`); a worker that could not be started; a crash after the worker
recorded its result, which is reported as recorded; a crash, or an exit
without a recorded result, after the last asset (running the conversion again
records the result or writes the reports, and converts nothing twice); a crash
during a rollback — finishing an interrupted rollback is not automated, and the
message names each test still to restore, callers first, with numbered
`uft-migrate restore … --wave` commands; and a crash the journal could not
record. Unless the wave had finished — completed, aborted and rolled back, or
ended with nothing in it left to undo — it stays open, and running the
conversion again with the same inputs continues it. The supervisor exits 0
only when the attempt recorded a result whose exit code is 0 (its `run-result`
journal record): a worker that exits 0 without one — most likely stopped from
outside — ends the run with exit code 2 and the wave open.

**What the supervisor keeps.** In the run folder, `crash_recovery/<wave>/`:

- `attempt_NN/` for every attempt: `command.txt` (the worker's command line,
  with the ALM password masked), `stdout.log` and `stderr.log`. After a native
  crash also `crash.json` — the exit code, where the crash struck, the last
  breadcrumbs, what was cleaned up and a summary of the WER report, with the
  fail-fast code named as Windows names it (`FATAL_APP_EXIT` for code 7, for
  example; a code Windows does not define reads `subcode N`) — and a copy of
  `Report.wer` when Windows wrote one. A crash dump is never copied: it can
  hold the ALM password, and run folders get zipped and shared. `crash.json`
  records where the dump is, under `wer.dump`, only when the dump was written
  while that attempt ran; a dump with the same name written outside that time
  is named in `wer.dump_note` instead, as possibly an earlier process's. It
  can also be this crash's own, written under a clock that differs (a
  LocalDumps folder on a network share), so check its time before you set it
  aside.
- `supervisor.log` — the supervisor's messages, in order.
- `restore_commands.txt` — when recovery stopped with tests still to restore,
  one `restore --wave` command per test, callers first, each with
  `--output-root` written out, under a reminder to set
  `UFT_MIGRATE_ALM_PASSWORD` first. The message itself shows the first three,
  numbered, and names this file.

A wave that completes without a crash keeps only `command.txt` and
`supervisor.log`. Only the newest two finished waves that wrote a test keep a
`crash_recovery` folder at all; an unfinished wave always keeps its own. A
finished wave that wrote no test — a launch the pre-flight gate refused, for
example, or one that only replaced function libraries, which the journal does
not record — does not count toward the two, and its folder is deleted once two
newer waves that wrote a test have finished. Copy a wave's folder elsewhere to
keep it longer.

`resume/alm_wave.json` summarises the latest wave and its attempts; the journal,
not that file, decides everything. When the supervisor ends a conversion
itself — a crash it could not get past, a worker that ended without a result,
or a refusal to start — it prints its own result, whose
`crash_recovery.operator_message` says what happened, what was done and the
next step; the Migration Console's *Conversion Failed* dialog shows that
explanation first, in full. When the crash budget runs out, the abort worker's
own report is printed instead, and — for `run --alm`, which the console runs —
its executive summary says why the wave was aborted. Collect diagnostics for
Merito support rather than sending the run folder: the bundle carries this
folder, the journal and the breadcrumbs, and also the process logs and the
Windows crash evidence the run folder lacks, without your test content (see
*Reading a diagnostics bundle* below).

**Where it died: `crash_breadcrumbs.log`.** During an upload conversion,
Phoenix appends one JSON line to `crash_breadcrumbs.log` in the run folder
immediately before each ALM call of an upload, or of a restore the conversion
makes (crash recovery, rollback), and before and after each AOM build, closing
the file each time. The last line a dead process wrote names the step it died
in, for example `upload: save`. A `modules: loaded` line lists DLLs from
outside Windows and the Python runtime that appeared in the process. When a
conversion attempt starts, a file larger than 5 MB is renamed
`crash_breadcrumbs.log.1`.

**Conversion waves.** One all-or-nothing conversion of the project is a
*wave*: its id, `W<date>T<time>Z-<6 hex>`, appears in the journal, in the
evidence folder and in every message about it. A wave spans every attempt it
takes — crash relaunches, and launches after a cancel or a stop — until it
finishes or is rolled back. It is *settled* when no test in it may still be
half-written or half-restored. A launch with the same inputs continues an
unfinished wave, and its discovery must find the tests the wave started with:
when some are missing it runs once more, and if they are still missing the
conversion stops (`wave-scope-changed`) before it writes anything — run it
again first, since a transient listing fault can cause that. A discovery that
fails outright, even after its retry, stops the wave the same way
(`discovery-failed`): the half-written test a crash may have left is checked
only once discovery succeeds, so run the same command again soon. The
supervisor treats both like any other stop and does not relaunch. A launch with
other inputs closes an unfinished wave that has
not written any test (outcome `superseded-no-writes`) and starts a new one, but
is refused once the open wave has written a test, with the options that differ
and the `restore --abandon-wave` command that closes it; and no new wave starts
while any wave in the run folder is unsettled ([alm_safety.md](alm_safety.md)
§ *Interrupting and resuming*). When a test the wave already froze changed in
ALM before the wave wrote it — after a Cancel, say — the wave freezes its copy
again from what ALM holds and keeps the old one beside it
(`alm-wave-snapshot-refrozen`). A wave that cannot go on safely *stops*: it
writes nothing more, leaves the report set alone, writes `alm_wave_stop.json`,
exits 2 and stays open, so the same command continues it once the named step is
done. A copy that cannot be made at all — a full disk, for example — is such a
stop too (`snapshot-failed`). The reasons, and what to do about each, are in
[troubleshooting.md](troubleshooting.md) § *The conversion stopped and stays
open*.

**Do not set `PYTHONFAULTHANDLER`.** The supervisor removes it, and
`PYTHONDEVMODE`, from the worker's environment, and the worker turns Python's
fault handler off before anything else: with it on, a native crash exits with
code 3 instead of `0xC0000409`, Windows records nothing, and the crash would
read as an ordinary failure that is never recovered. Use the Windows Error
Reporting evidence above instead.

**A crash that is not recovered.** An analysis, a gate rehearsal, a filesystem
run and the Migration Console itself are not supervised, and a crash ends them
with no result: for a conversion the console started, *Conversion Failed* says
the process ended without reporting a result and gives the exit code. Read the
Event Viewer entries for that time. The same happens if the supervisor itself
is stopped from outside. On an ALM conversion, running the conversion again
with the same inputs is all that is needed: the wave continues and checks the
test that was in flight first. Until then, do not let anyone run that test —
it may be half-written.

**Reading a diagnostics bundle.** Rather than the run folder, ask for a support
bundle: *Collect Diagnostics…* in the Migration Console (the Yes of its
*Conversion Failed* dialog runs it too), **Start Menu > Merito > Merito UFT
Phoenix Collect Diagnostics**, which needs no Migration Console, or
`uft-migrate diagnostics collect` ([troubleshooting.md](troubleshooting.md) §
*Collect diagnostics for Merito support*). The logs are always written and
kept up to 30 days, and every way to collect reaches that far back, so a recent
problem is collected after it happened, without reproducing it; only a native
crash that left no dump may need one (*Crash dumps for Merito support*, below).
It is a zip under `out\_support\`, beside a folder of the same files:

| Path | Contents |
| --- | --- |
| `README.txt` | What the bundle is, what is in it and never in it, how the redaction worked and how to check it |
| `MANIFEST.json` | Every file with its SHA-256; what was left out and why; the redaction rules' hash; the canary and final-scan results |
| `TRIAGE.md`, `triage.json` | The first look: build and risk flags, the process tree, the verdict and the failure that caused it, fault groups, native crashes, discovery, next steps |
| `environment\` | Windows, Python, pywin32, UFT One and the ALM client; WER and LocalDumps settings; the WER reports and Application events 1000/1001 of the window; `doctor`'s read-only checks; dumps and `%TEMP%` leftovers counted, never opened |
| `logs\` | The process logs of the window (§5) |
| `run\run-1\` | The run folder's allow-listed files under their own relative paths: the journal, `migration_log.txt`, the breadcrumbs, the results and `crash_recovery\` |

ALM names in it are tokens (`project-1`, `test-3f9a2c`); numeric test ids are
kept, and the map back to the real names stays with the customer.

`uft-migrate diagnostics triage <zip or folder>` prints the same `TRIAGE.md`
with the reader's own, newest known-issue table. It also reads a raw run folder
of an earlier release, from its journal and its error text. A fault group reads:

```text
FAULT F-3a91c0d2e7  error · 1 test × 3 attempts · deterministic (same fp 3/3) → 2 futile retries (~34 s)
  com   DISP_E_EXCEPTION 0x80020009 · scode 0x8004051C (FACILITY_ITF 0x051C) · "Invalid field name < TS_VC_CHECKOUT_USER_NAME >."
  call  CheckedOutBy (com-property-get)
        uft_migrate/alm/alm_repository.py:3188 entity_version_control_state   checked_out_by = _safe_get(version_data, "CheckedOutBy", default="")
        via _safe_get :232 → <site>/win32com/client/dynamic.py:620 __getattr__
  step  convert: prepare (lock/checkout) · first swallowed at convert_test.vc_snapshot in 2 processes (analysis-child) 17:23:10Z → vc_state={}
  known K-0001 — fixed in 1.1.7 → upgrade
```

*Deterministic* means every retry failed the same way, so the retries were
futile; retries are counted within one process's tries of a test, never across
waves or relaunched workers. The native crashes include those only Windows
recorded — the WER reports and Application events of a Phoenix process no
parent watched, such as the Migration Console itself — with whether a dump
exists or LocalDumps could write one; crash reports of other programs (UFT, the
ALM client) are counted apart. `--repo <checkout>` adds the code at the
customer's commit beside the failing frame and the commits that changed that
file since; `--compare <older bundle>` lists the faults that went away or
appeared after an upgrade; `--check-secret` asks for a value without showing it
and names every file of the bundle it appears in, without changing the exit
code. A legacy run folder's faults get the fingerprint the recorder gives the
same fault, so they group with recorded ones and `--compare` matches them
across the upgrade.

**Crash dumps for Merito support.** Only a crash dump holds the native call
stack of a fail-fast such as `0xC0000409`; the WER report names the module and
the offset, not the path to them. A dump can also hold the ALM password and
test data, so Phoenix never writes one, never reads one without consent, and
never puts one in a bundle: dumps go only into the separate
`…-EXTRAS-SENSITIVE.zip`, when the customer answers **Yes** to the question
*Collect Diagnostics…* and its Start Menu shortcut ask, or passes
`--include-dumps`, and only the dumps matched to a crash in the bundle, at
most three. When Merito support needs a
dump and the machine writes none, support may ask the customer's administrator
to switch WER LocalDumps on for Phoenix's `python.exe` and `pythonw.exe` for a
limited time, reproduce the crash, collect with the dump, and switch LocalDumps
off again; support sends the steps for that machine, the step that switches it
off included. Send that file only by a secure channel, and change the ALM
password afterwards.