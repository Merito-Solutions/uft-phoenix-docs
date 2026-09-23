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
| `alm_aom_results.json` | Per-test truth: `status`, `error`, `blockers[]`, `converter_findings[]`, `uploaded`, `upload_verified` (`ok`/`mismatch`/`failed`), `rollback_status`, `resumed` (an earlier run of this run id already converted it and the server still holds the Python), `runtime_helper_blocks`, `test_lab_run_id`/`_status`, and `notes[]` — the chronological story of each test. A gate rehearsal (`--upload --dry-run`) never writes this file, so during a rehearsal it still holds whatever the prior analysis left there. Start here. |
| `migration_log.txt` | JSON-lines event stream with timestamps — the cross-test timeline. Search for `"level": "error"` first (pre-flight refusals, run aborts, failed assets, upload-verify and rollback failures, failed ALM reconnects), then `"level": "warning"` (transient retries, session reconnects, lock revocations, per-asset rollback outcomes). In PowerShell: `Select-String -Path migration_log.txt -Pattern '"level": "error"'`. |
| `alm_preflight.json` | The pre-flight verdict, written on every conversion run: `status` (`pass`/`fail`), the selected and eligible ids, and every disqualified, out-of-scope and warning asset with its `reason_code` and detail. When `status` is `fail`, no ALM write happened (§4). |
| `resume/alm_test_results.ndjson` | The durable per-asset journal — one JSON line per event (the `record` field: `intent`, `attempt`, `terminal`, `aborted`, `not-attempted`, `rollback`, `already-converted`, `resume-mismatch`, `session-lost`/`session-restored`/`session-reconnect-failed`), each written as it happens. It survives a killed run, and a re-run of the same run id reads it to skip assets that are already converted. The `terminal` record also carries the test's path and name and its converted action layout (`action_renumber_map`, `action_name_folders`, `action_folder_has_code`, `function_library_links`), which is what lets a skipped asset still serve as a callee for the tests converted after it. A journal written by an earlier version of Phoenix lacks those fields, and a caller of an asset carried forward from one blocks with `that callee has no conversion record in this run` (see [troubleshooting.md](troubleshooting.md)). Read it first after an interrupted conversion. In PowerShell: `Select-String -Path resume\alm_test_results.ndjson -Pattern '"record": "terminal"'`. |
| `alm_aom_work/test_<id>_source/` | The test as downloaded by the **latest** attempt in this run folder. It is deleted and downloaded again on every attempt, so after a re-conversion it can hold the converted Python. Contains `Download.xml` (asset-owner manifest, §1a). |
| `alm_aom_work/alm_rollback/test_<id>_source/` | The frozen pre-conversion payload, written once on the first non-dry-run attempt and never touched again. The abort rollback and `uft-migrate restore` put back **this** copy; treat it, not `test_<id>_source`, as the original. A real conversion and a **deep** analysis (which AOM-builds every test) both create it; a standard analysis and a `--dry-run` rehearsal do not. |
| `alm_aom_work/alm_rollback/resources/<id>/` | The prior bytes of any `.pfl` function library this run replaced. |
| `alm_aom_work/test_<id>_build/<TestName>/` | The AOM-built payload that was (or would be) uploaded. The converted Python is human-readable in the `Action<N>/Script.pts` files: `Action0` is the main flow, and `Action1` holds a source action only when that action was itself named `Action1` (about 60% of the reference estate) — otherwise the AOM's inert default is removed and the named actions occupy `Action2..N`, usually leaving no `Action1/` at all. Read the `.usr` `[Actions]` section for the name→folder map rather than assuming the numbering. |
| `alm_aom_work/test_<id>_verify/` | The post-upload re-download used for byte verification. |
| `alm_aom_work/test_<id>_runresults/.../run_results.xml` | Test Lab run detail: `<ErrorText>` nodes carry the real failure; `<Parameter name=... value=...>` proves parameter delivery at run time. |
| `executive_summary.html` | The verdict + next-steps rollup with drill-down links. |
| GUI runs: `analysis_cli_*.log`, `run_cli_*.log` | Raw engine output as the console saw it. |

Standard triage: `alm_aom_results.json` status → that test's `notes[]` →
its `run_results.xml` `<ErrorText>` → the layer table in §1/§2/§3.

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
  it with `uft-migrate restore` or from ALM version history, and escalate with
  the run folder. `uft-migrate restore` puts back the files but not the
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
- A `com_error` whose message is "The object invoked has disconnected from
  its clients" means the UFT/ALM client process died mid-call. If the ALM
  session drops *before* an asset's upload starts, Phoenix reconnects and
  retries that asset on its own (`alm-session-reconnect` in migration_log.txt);
  a drop after the upload has started aborts the run and rolls back. To carry
  on, re-run the conversion under the same run id (the Migration Console
  converts into the **Analysis Run ID**'s folder). An asset is skipped —
  `resumed: true`, reported `ok` — only when an earlier attempt recorded it as
  uploaded and verified **and** the server still holds a Python-only payload for
  it. Everything else is converted again, including assets an abort rolled back.
  A skipped asset still serves as a callee for the tests converted after it; the
  one exception, a journal written by an earlier version of Phoenix, is covered
  in [troubleshooting.md](troubleshooting.md) under *that callee has no
  conversion record in this run*.

---

## 7. IronPython runtime completeness

Converted tests execute in UFT's embedded IronPython 3.4. Some UFT installs
ship it incomplete (missing `IronPython.Modules.dll`,
`Microsoft.Scripting.Metadata.dll`, or the `Lib\` standard library), which
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
project the previous version also stays in ALM version history.

Each successful conversion is a **new** checked-in version; the
pre-conversion version remains in ALM version history — a first-class
rollback path alongside the `restore` subcommand's run-folder snapshots.

In `alm_aom_results.json`, the status `vc-blocked` identifies these failures
(there is no `locked` status — a lock is recorded as a per-asset note, not a
failure), and each asset carries a `vc_state` field recording the
version-control and lock state observed for that asset.
