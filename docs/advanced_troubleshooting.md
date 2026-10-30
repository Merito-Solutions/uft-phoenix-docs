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

### 1a. Pasted copies and shared asset ownership — status `shared-assets`

ALM's copy/paste gives the copy its own ExtendedStorage and copies the
original's stored `Download.xml` (the asset-owner manifest) into it, so the
copy's manifest still names the original test and the original's owner ids.
Phoenix detects this before converting (the manifest's TEST owner id doesn't
match the test) and then reads the test's own asset records. It decides from
the copy's manifest and its own records, and reads the original's records only
when those no longer match (*Without the record*, below). In a run folder that
holds the copy's first-sight record, or while its names still match, the
verdict does not depend on the original; without the record, the original's
current names decide. A conversion decides as the analysis in its run folder
did:

- **Pasted copy — converts.** The test owns asset records whose names match the
  manifest's relations one to one. That is the normal result of an ALM
  copy/paste (230 of 230 copies on the one server measured), but a paste can
  turn out differently, which is why Phoenix checks every copy. When ALM gave
  the copy its own asset records, it converts like any other test, from those
  records, and the original's records are never written. Its notes name the
  test it was copied from, and the scan report shows a *Pasted copies* row with
  the count (only when there are any).
- **`shared-assets` — refused.** The test owns no asset records of its own, or
  its records do not match its manifest (names missing, extra or repeated) and
  neither its first-sight record nor its original's records place them
  (below). The error names the kind and the other test, in the words
  `shares its asset ownership with test <id>`. This stop is deliberate and
  cannot be overridden.
- **Unreadable — retried, not refused.** ALM did not return the test's asset
  records, or the original's records that the check below reads. Phoenix
  tries three times, two seconds apart, then ends the asset `error`, saying it
  could not read the test's asset records. A conversion retries that like any
  other error before the upload starts; an analysis reports it as a failed
  asset to re-analyze. It is never reported as `shared-assets`.

**The first-sight record.** The first time an analysis or a conversion in a run
folder sees a pasted copy, Phoenix records which of the copy's own asset
records stands for each relation in its manifest, by record id, in
`out/<run>/alm_aom_work/alm_rollback/pasted_copy_owner_maps.json`. An entry is
never overwritten. A conversion renames an action's record when the rebuild
moves the action to another folder (§5, `test_<id>_build`), and a restore does
not rename it back, so after a conversion the names alone may no longer match:
Phoenix then recognises the copy through this record, and a restore uses it to
re-point each of the copy's action records by id. Keep the file with the
rollback snapshots. The parallel workers of a Standard analysis all write it:
each holds a lock on the empty `pasted_copy_owner_maps.json.lock` beside it
while it adds its entry, so none loses another's. When an entry could not be
kept, the copy's report note says so (*could not be kept in this run folder*),
with a record in the process logs (site `pasted_copy_maps.write`, or
`pasted_copy_maps.read` for a file that cannot be read); unless the file itself
cannot be read (the note then says *corrupt-file-left-alone*), a conversion in
the same run folder records the entry when it next matches the copy, before it
changes anything. An unreadable file is never written over: move it aside, or
restore it from a copy, before converting. Copy the `.json` file alone; the `.lock` file is never
needed.

**Without the record: the original's records.** In a run folder that does not
hold the record — one under a new run id, for example — a copy whose names no
longer match its manifest gets one more check, *source correspondence*.
Phoenix reads, by id, the original's records that the manifest lists, and
pairs them one to one with the copy's own records by current name and
description. A conversion changes a record's name, never its description, and
renames the records of a copy and of its original alike when both are
converted with the same actions; a restore renames neither back. So a copy
converted with its original is recognised — by an analysis, a conversion or a
restore — and an analysis or conversion records the match in the run folder's
file like a first sight. The pairing must take in every record on both sides,
with no name and description repeated on either; if one of the original's
records no longer exists, or belongs to another test or to a component, the
copy is refused. So is a copy with two action records, on either side, that
share a description (a blank one counts): only their names, which a
renumbering rewrites, could tell them apart. What the check cannot recognise
is a copy converted while its original was parked, or converted differently
from it (its actions changed since the paste, say), so that their records were
not renamed alike: without its record that copy is refused as `shared-assets`,
and a restore that cannot place every one of its action records fails instead
of reporting success. Before you analyze such a copy under a new run id, copy
`alm_aom_work/alm_rollback/pasted_copy_owner_maps.json` from the run folder
that first saw it to the same place in the new run folder.

Fix options for any other `shared-assets` test — both re-creations give the
test a new id, so its Test Lab history stays with the old one:
- re-create the test so it owns its records: in ALM, paste it again with
  *create copies of related entities*, or in UFT open the original and *Save
  As* a new ALM test — then re-run the analysis;
- if the copy is redundant, point its callers at the other test and delete it
  before migrating.

Converting the other test "instead" is not an available action: an ALM
conversion is whole-project, so that test converts in the same run regardless,
and the `shared-assets` test is still disqualified at the pre-flight gate (§4),
which refuses the whole run. Parking it is not a fix either — the other test
would still convert, leaving the two in different languages. The failed-assets
page badges a `shared-assets` asset **do not park** and withholds it from the
one-click exclusion list for that reason. For a similar reason it withholds
a failed asset whose shareable-action calls tie it to an in-scope test that
the list does not park, whether it calls that test or is called by it,
directly or through other tests: its row reads *park only together with* and
the tests' ids, and a note under the list names each one with its partners
(in `scan_report.md`, *Not in the Park List: Calls Tie Them to Tests That
Convert*). Parking it alone would leave a VBScript test and a Python test
calling each other, which the pre-flight gate refuses (§4).

**Parking a pasted copy — pending measurement.** Phoenix leaves a copy's stored
`Download.xml` as the paste left it, still naming the original, and does not
read or change the older `ERI.xml` some copies carry. How UFT runs a converted
copy has not yet been measured on a live server. Until it has, convert a pasted
copy and its original together: do not park one of them while the other
converts.

Verification for the curious: the pre-upload staging download in
`out/<run>/alm_aom_work/test_<id>_source/Download.xml` lists the owners —
`<OwnerType>TEST</OwnerType>` with a different `<OwnerId>` marks a copy.

### 1b. Shadow USER_ASSETS owners (stale `.mts` ARI rows)

On some ALM builds, uploading a `Script.pts` where the action historically
had `Script.mts` spawns a **second** (shadow) owner holding the `.pts` row,
while the original owner — the one UFT follows — keeps its stale `.mts`
row. The result is the placeholder above even though the storage is
correct.

Phoenix repairs this automatically during upload: it purges stale
`Action*/Script.mts` sidecars from the server and rewrites the ARI
`ARI_PATH` rows on **every** owner (resolved from the download manifest, or,
for a pasted copy, from the copy's own records — §1a) from `.mts` to `.pts`.
The run notes show the outcome:

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
- `owner_resolution` names where the action owners came from:
  `'download-manifest'` — by id, from the test's own `Download.xml`;
  `'pasted-copy-map'` — a pasted copy, by id through its first-sight record,
  or the match made again where there is none (§1a), the usual value when a
  pasted copy converts or is restored;
  `'user-assets-ownership'` — from the test's own asset records, matched by
  name; `'asset-repository-items'` — `Download.xml` was missing or listed no
  action owners, so the fallback lookup supplied them. That lookup searches the
  project's asset rows for the test's `.usr` file name, which a pasted copy's
  rows can carry too; an owner it lands on that ALM shows belongs to another
  test is dropped, and the owners are looked up again among the test's own
  records.
- Two keys of the sync's `alm-action-repository-item-sync` event in
  `migration_log.txt` appear only when they have something to report.
  `dropped_foreign_owners` lists each owner the fallback lookup dropped — the
  action, the owner id, the test or component that owns it, and its script
  row — and none of them is written. A restore adds a warning line for each,
  which does not fail it: `warning: owner <id> (<action>) belongs to TEST
  <id>, not to test <id>, and was not touched by this restore; its script row
  is <row>` (COMPONENT for a component's record). When that row is a converted
  `.pts` path, the line goes on to say that an earlier conversion of this test
  re-pointed that owner and that it needs repair in ALM: no restore of this
  test writes it. `unmapped_owned_action_owners` appears when the test's own
  records were matched by name (`user-assets-ownership`): it lists each action
  record the payload has no folder for, such as one a conversion renamed
  (`Action1` → `Action2`) whose rows still point at the converted folder.
  Nothing is written for it; it does not fail an upload by itself, and a
  restore fails on it (*ALM asset model not fully restored: action owner(s) of
  this test matched by name have no folder in the snapshot …*).
- `status='skipped'` on the **ARI sync** means no action owner could be
  resolved at all. Its `alm-action-repository-item-sync` event in
  `migration_log.txt` gives the `reason`: `missing-action-owner-ids` (none
  found), `ambiguous-owned-owners` (the test owns two records of the same name,
  and Phoenix will not guess which is which), `ownership-unreadable` (ALM did
  not return the test's own records; re-run) or `pasted-copy-map-incomplete`
  (with `owner_resolution='pasted-copy-map'`: the pasted copy's record names
  no copy record for one of the action owners its manifest lists, and Phoenix
  never translates only some of them). This is **not** benign. The
  asset-repair gate fails the asset (`asset-repair-failed`, see §1f), the whole
  conversion aborts, and every asset this run uploaded — including this one —
  is restored from its frozen snapshot. A test with no asset model at all
  therefore cannot be converted in place: re-create it by saving it from UFT
  into ALM (it gets a new test id), check that the connected user may modify
  test assets, then re-run the conversion.
- Phoenix does not write another test's asset records. Before it re-points the
  ARI rows of an action owner it resolved, or renames that owner, it reads the
  owner's record, and when ALM shows that the record belongs to a different
  test, or to a component (a BPT component can have the same id as a test), the
  write is refused: the ARI sync returns an error naming the record, the test
  that owns it and this test, and the asset fails as `asset-repair-failed`
  (§1f). The check refuses only on that evidence — a record ALM does not return
  is written as before.

### 1c. Stale UFT test cache (TD_80)

UFT extracts ALM tests into `%LOCALAPPDATA%\Temp\TD_80` to run them. After
a re-upload or a revert, a stale cache entry makes UFT run the **old**
build — symptoms include the placeholder above, or Python-era errors from a
test you reverted to VBScript (`Cannot use parentheses when calling a Sub`).

Phoenix clears TD_80 **on the machine running Phoenix, for the account running
it**: before a conversion, after any conversion that wrote to ALM, before each
Test Lab run it starts with `--run-via-alm`, and before a standard analysis
reads the tests. The Migration Console has no option to disable this; on the
CLI, `--no-purge-uft-cache` switches off the conversion purges. Phoenix cannot
reach the cache on any other machine, which is why a separate Test Lab
execution host needs a manual purge.

Each purge records what it did in the notes of every asset it concerns:
*UFT test extraction cache purged*, *not present … nothing to purge*, or a
`[warning] UFT test extraction cache (TD_80) only partly purged` (or *could not
be purged*) note that names what is still there, the error (typically *being
used by another process*) and what to do. The note says a file is held only
when Windows reports it in use by another process; any other error is quoted
as it is. The same warning is in `migration_log.txt`. When the run's last
purge left files behind, the Executive Summary's Next Steps says what to close
and delete; a warning from an earlier purge that a later one in the same run
cleared stays in the asset's notes only. A cache left partly deleted is the
cause of a converted test that reads `No Run` in Test Lab with *Unable to open
… Test not found* in the ALM execution log (§3).

Once UFT One is closed, the process that holds files in TD_80 is usually a
leftover **UFT Remote Agent** (`UFTRemoteAgent.exe`), the process an ALM Test
Lab run uses to drive UFT on a host. When a conversion or a Deep analysis has
just closed UFT One and its purge still leaves files behind, Phoenix stops a
running UFT Remote Agent and purges once more, and the note says so. It never
does this while a Test Lab run that Phoenix itself started is in progress, and
a standard analysis, which leaves UFT One open, never stops it. Stopping the
agent ends any Test Lab run on that machine, as closing UFT One already does,
so do not run Test Lab tests on the machine running Phoenix while a conversion
is in progress.

Before running the command: close UFT One and confirm no test is running on
that host (an open handle makes the delete fail partway and leaves a partial
cache); the first line ends a leftover UFT Remote Agent. Run it as the Windows
account that executes the tests — `%LOCALAPPDATA%` is per user. It removes
only UFT's local extraction cache; UFT re-extracts each test on its next run.

```powershell
Get-Process UFTRemoteAgent -ErrorAction SilentlyContinue | Stop-Process -Force
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
| A test reads `No Run` with no run id; its classification is `environment-failure` (`Matched environment pattern: license`) | The Test Lab scheduler finished without running the test — on the host it logged *You cannot use the current test. A UFT One license is needed.* (another UFT One, or a stale `UFTRemoteAgent`, can hold the seat). In a test set the test has run in before (a reused `--alm-test-set-name`), Phoenix never reports the earlier run as this one's result: a test that got no new run is `No Run`, with no report. A run that ALM records only after Phoenix has stopped waiting for it (about 20 seconds after the scheduler finishes, then between 30 seconds and two minutes more, by `--uft-timeout`) also reads `No Run`: a failure, never a false pass. | Free the license (close other UFT One sessions, stop a stale `UFTRemoteAgent`) and re-run; a `No Run` is never a pass. |
| A converted test reads `No Run` with no run id after a conversion; the ALM execution log says *Unable to open … Test not found* | UFT on that host read a partly deleted copy of the test from its extraction cache (`%LOCALAPPDATA%\Temp\TD_80`): a process, usually a leftover UFT Remote Agent (`UFTRemoteAgent.exe`), held files in it when the cache was purged. On the machine running Phoenix, the asset's notes carry a `[warning] UFT test extraction cache (TD_80)` note; the Executive Summary's Next Steps also says what to do when the cache was still not cleared at the end of the run. The converted test in ALM is not affected; this is a false failure. | Close UFT One, end `UFTRemoteAgent.exe`, delete TD_80 (§1c), and run the test again. |
| A test reads `Error` with no run id; its reason (and the asset's notes) say what raised, for example `Test Lab orchestration failed: ...` | Phoenix could not start or follow the Test Lab run: the test set or the test instance could not be created, or the scheduler would not start. The test did not run, and it counts as a failed run, never as one that was not requested. | Fix what the reason names (the Test Lab folder or set, the host, the ALM connection) and re-run. |
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
  with no override, for a test that owns no asset records of its own or whose
  records do not match its manifest. A pasted copy that owns matching records
  is not refused.
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

### The free-edition limit (`license-limit`)

Before the pre-flight gate, every ALM conversion that is not an analysis —
an upload, a build-only run without `--upload`, and the `--upload --dry-run`
rehearsal — takes the project's test-case count from its own discovery, and
every filesystem `convert` and `run` counts the test cases under its source
folders. Neither takes the count from the reports in the run folder, so a
test added since the analysis is counted. Over the limit that applies — 100
for the free edition, or the installed license's — the run stops with status
`license-limit` and exit code 2: an ALM run after discovery and before it
opens its own ALM session or builds anything, so it writes nothing to ALM
(discovery has signed in and read the Test Plan, to count); a filesystem
`convert` or `run` before it touches the run folder's files, so it leaves
them as they were (it writes its logs). Either way no test is converted,
backed up or changed. The filesystem conversion counts again before its first
write, and a `--resume` of one that had started is counted only there.
Refused at that point, the run has already rescanned (new scan reports and
scoping summary) and `resume_state.json` records it as failed
(`license-limit`), so `--resume` is refused afterwards: run it again without
`--resume`. `--allow-partial-conversion` does not lift the limit.

- The `licensing` block of the output, and of the analysis's
  `scan_report.json`, gives the count (`test_cases`), the `limit`, the
  `edition`, the `licensee`, the `alm_projects` the license names and the
  `counting_rule`; `license_problems` says
  why an installed license file did not apply.
- The ALM count is every `QUICKTEST_TEST` test discovery finds under the Test
  Plan, outside the `.TrashCan` and `Recycle Bin` folders, taken inside the
  discovery process before the path filters and before parking. So parked
  and excluded tests, failing tests, tests already in Python and API tests
  that ALM stores as `QUICKTEST_TEST` all count, and the count can be higher
  than *Assets in Scope*. On disk it is every folder with a `Test.tsp` and a
  `.usr` under the source folders, less tests in `.TrashCan` and `Recycle
  Bin` folders and Phoenix's own copies, before `--exclude-test-path` and
  `--include`/`--exclude` — except tests under folders named `out`, `.git`
  or `__pycache__`, which the default `--exclude` leaves out: they count only
  when the run's `--include`/`--exclude` keep them.
- `migration_log.txt` records the decision: an `alm-test-case-count` line on
  every run that counted (the count, the limit, the edition, the license id —
  never the licensee — and `count_basis`: `discovery`; for a failed-only
  refresh, `carried-forward` from the full analysis, or
  `derived-from-prior-selection` when the run folder's `alm_aom_results.json`
  holds no licensing block — written before 1.3.0, or last written by a
  continued conversion wave — so the count is every test id it names, less
  the tests in `.TrashCan` and `Recycle Bin` folders)
  and, on a conversion, an `alm-license-gate` line, level `error` when it
  refused. A discovery that sent no count logs the warning
  `alm-test-case-count-fallback`, and every test it returned is counted, the
  deleted-test folders included: the count can only come out high. On disk,
  the conversion's stderr says `license:` and the count as it starts.
- A refused ALM run leaves the run folder's analysis as it was: no report
  set, no executive summary, no `alm_wave_stop.json`, and `resume_state.json`
  back to the bytes it had. Unsupervised (the rehearsal, a build-only run),
  only `migration_log.txt` gains lines. A crash-supervised launch (every
  upload) relays the refusal and closes the wave it opened as
  `closed-no-writes`, so the next launch is a new wave, judged again; that
  wave is recorded in `resume\alm_test_results.ndjson`, `resume\alm_wave.json`
  and `crash_recovery\<wave>\`.
- A conversion that continues an unfinished wave (§9), its abort and
  finish-rollback workers, and `restore` are never refused for the limit,
  whichever release started the wave; nor is a filesystem `--resume` of a
  conversion that had started, unless its source folders now hold more test
  cases than it recorded when it started.
- An analysis is never refused. Over the limit, a **Deep** analysis without a
  license that covers the project deletes each `alm_aom_work\test_<id>_build\`
  once the test is checked and measured (§5), and the asset's notes say so.

[licensing.md](licensing.md) has the customer-facing rules.

### The all-or-nothing pre-flight gate

Separately, every ALM conversion first re-reads the signed-off analysis in its
own run folder and judges the **whole** selection before the first ALM write. If
any in-scope asset is disqualified, the run is refused with status
`preflight-failed` and nothing is written. Disqualified means:

- an analysis status other than `ok` — for example `blocked` without
  `--allow-blockers`, `shared-assets`, or `error` (a pasted copy that owns its
  asset records is `ok` and converts with the rest, §1a);
- converter blockers on an otherwise-`ok` asset (`converter-blockers`) — the
  analysis was run with `--allow-blockers` and the conversion was not;
- no analysis record at all (`not-analyzed`), or a record the run's discovery
  did not return (`analyzed-but-not-selected`);
- a cross-test reference that cannot be retargeted: `unresolved-callee`,
  `ambiguous-callee`, `self-referencing-callee`, `reference-cycle`, or
  `callee-disqualified` (a caller whose callee is itself disqualified);
- a selected test that a parked test calls (`parked-caller`): a test listed
  with `--alm-exclude-test-id`, or removed by a path filter (a *Path
  Exclusions* / `--exclude` pattern it matches, or a CLI `--include` pattern
  it does not match), stays VBScript, so a test whose shareable action it
  calls cannot become Python. The gate reads a parked test's calls from its
  analysis record when the analysis measured it, and otherwise from what the
  analysis read about it: an analysis that parks tests reads which tests each
  one calls, read-only, before it analyzes anything (below). So the refusal
  stands when the analysis and the conversion park the same tests, as the
  Migration Console always does, and after a re-analysis that keeps the
  parking. A test a path filter leaves out is never read: the gate sees its
  calls only when the analysis it judges measured it. A test in a `.TrashCan`
  or `Recycle Bin` folder never counts, because it does not run. The detail
  names up to three callers. A parked test's call that names no test of the
  analysis by its full path (the test it called moved or was renamed) and
  whose name matches more than one test refuses every test of that name this
  run would convert, rather than guess: the detail then starts *May be called
  by a parked test … through a call that matches more than one test* (or,
  when a known parked caller also calls the test, continues with *It may
  also be called through a call that matches more than one test*) and
  names the call (under *Unmatched call(s)* in the first form). Such a call whose path names
  another parked test, or a test left out by path or by type, refuses
  nothing this way;
- a parked test whose calls could not be read (`parked-references-unread`),
  refused under its own id because whether it calls a test this run converts
  is unknown: the analysis's read of it in ALM failed or did not find it, its
  analysis record stopped before the read (`error`, `not-found`, `vc-blocked`,
  `process-crashed`, `shared-assets`) and lists no call, the analysis never saw
  it (path-excluded then, or newer), or the run folder's analysis was made by
  an earlier Phoenix build, which did not read parked tests. An id this run
  parks that discovery does not return and the analysis knows nothing about
  (a mistyped one, say) refuses nothing. `alm_preflight.json` counts these tests in
  `counts.assessed`, and the refusal headline's *N of M asset(s)* includes
  them.

**The parked-reference read.** A parked test stays VBScript, so before an
analysis that parks tests (*Out-of-scope test IDs*, `--alm-exclude-test-id`)
measures anything, and before it opens its own ALM connection, it reads which
tests each parked test calls. It does this read-only, in separate processes as
discovery does: one ALM login per process, up to 25 parked tests per process,
and never more processes at once than the analysis's workers. For each test
it finds the test, downloads its definition to
`alm_aom_work\parked_references\` (removed after the read) and reads the
calls from its `Test.tsp`. Nothing is checked out, locked, built or written,
and an asset record's owner is not read. A test that cannot be read is tried
once more in place, then once more by a fresh process with its own login;
until one process has logged in the others wait, and after a refused login
no other starts, so a wrong password costs one failed login. Measured live
on 2026-10-26 (316 parked tests, 0 unread, 10 workers), the read took 128
seconds of wall-clock, about 0.4 seconds per parked test, and about 2.5
seconds per test inside one reading process, its login included. Each
reading process reads up to 25 parked tests and up to *Threads* of them run
at once, so up to 25 parked tests take about 2.5 seconds each (one process:
more workers do not help), and more take about ceil(N/25)/*Threads* rounds
of roughly a minute each; the 0.4 seconds per test holds only for a few
hundred parked tests. An analysis
that parks nothing does none of this. A full analysis reads every parked test
again; *Re-analyze Failed Assets* (`--failed-only`) keeps what the analysis it
refreshes already proved and reads only the rest; *Refresh Report* reads
nothing from ALM. The result is kept as the `parked_references` list of
`alm_aom_results.json`: per parked test its id, name, path, the tests it
calls (`external_test_paths`), `references` (`read` or `unread`), `source`,
and for an unread one `error` and, when diagnostics recorded the fault,
`error_id`. `migration_log.txt` logs one `alm-parked-references-read` info
line (`parked`, `read`, `unread`, `sources`) and, when any test could not be
read, the warning `alm-parked-references-unread` naming them, also printed as
an `[analysis]` progress line. The analysis verdict, its counts and the
test-case count do not change.

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
A parked test refused as `parked-references-unread` is not a skipped asset and
gets no such row; the override over one still makes the conversion exit 2, and
the executive summary and `summarize` hold approval with the line
*--allow-partial-conversion was used over N parked test(s) whose calls could
not be read*. The `alm-preflight-override-applied` event's `disqualified`
count leaves those tests out. Treat the override as a last resort.

---

## 5. Reading the run artifacts like a support engineer

Everything lives under `out/<run_id>/`, in the folder Phoenix was launched from
(the Start Menu shortcut starts in your user profile, so that is where the `out`
folder appears). `--output-root` moves converted output, not the run folder.

| Artifact | What to look for |
| --- | --- |
| `alm_aom_results.json` | Per-test truth: `status`, `error`, `blockers[]`, `converter_findings[]`, `uploaded`, `upload_verified` (`ok`/`mismatch`/`failed`), `rollback_status`, `resumed` (an earlier run of this run id, or an earlier attempt of this conversion wave, already converted it, and ALM was read and still held the Python; two keys, present only when true, mark a carried-forward test this attempt did not read from ALM: `recycle_trusted`, carried forward after a planned restart, §9, and `server_not_reread`, an outcome rebuilt from the journal alone), `wave` (the conversion wave, §9), `crash_recovery` (what crash recovery did around this test; the same lines open its `notes[]` with `[crash recovery]`), the run's `discovery` block (`retried`: whether discovery ran a second time; `unplaced_tests` / `unplaced_test_ids`: tests ALM lists that discovery could not place in a Test Plan folder, which the executive summary's Next Steps name), `runtime_helper_blocks`, `test_lab_run_id`/`_status`, and `notes[]` — the chronological story of each test. An analysis that parks tests also writes `parked_references`: which tests each parked test calls, or why that could not be read (§4, *The parked-reference read*); an analysis that parks nothing writes no such key. A gate rehearsal (`--upload --dry-run`) never writes this file, so during a rehearsal it still holds whatever the prior analysis left there. Neither does a conversion that stopped and stayed open to resume (`alm_wave_stop.json`, below). Start here. |
| `migration_log.txt` | JSON-lines event stream with timestamps (UTC, as in every JSON file; the run folder's HTML and Markdown reports show local time, while the diagnostics bundle's `TRIAGE.md` keeps UTC like the logs it summarizes) — the cross-test timeline. Search for `"level": "error"` first (pre-flight refusals, refusals over the free-edition limit — `alm-license-gate` — run aborts, failed assets, upload-verify and rollback failures, failed ALM reconnects, native crashes of the conversion process and crash recovery that stopped — `alm-crash-detected`, `alm-crash-budget-exhausted`, `alm-crash-recovery-gave-up`, `alm-crash-wave-abort` — and stopped conversion waves, `alm-wave-stopped`), then `"level": "warning"` (transient retries, session reconnects, lock revocations, per-asset rollback outcomes, the cleanup and relaunch after a crash, the check of the test a crash left in flight — `alm-crash-reconcile-*` — a wave's copy of a test frozen again because the test changed in ALM before the wave wrote it, `alm-wave-snapshot-refrozen`, an unfinished wave that had written no test closed for a launch with other inputs, `alm-crash-wave-superseded`, a continued wave that skipped the pre-flight gate, `alm-preflight-skipped-wave-resume`, a discovery that failed while reading the Test Plan, died without an answer or came back short and ran a second time, `alm-discovery-retried`, and tests the project's list holds that the walk did not return and whose folder could not be read, `alm-discovery-folder-unreadable`; a discovery that sent no test-case count, `alm-test-case-count-fallback`; a planned restart of the conversion process to free memory, `alm-worker-recycle` (§9), and, once per conversion process, the same memory condition in an upload conversion that runs without its supervisor (one started by calling Phoenix from Python code; the Migration Console and the `uft-migrate` command always supervise an upload conversion), which cannot restart and goes on, `alm-worker-memory-high`; and, on a failed-only refresh, tests the previous analysis parked that are no longer parked and are analyzed now, `alm-failed-only-unparked`, or that name no test ALM could find, `alm-failed-only-unparked-not-found`; and, on an analysis that parks tests, the parked tests whose calls could not be read, `alm-parked-references-unread`; and a purge of UFT's TD_80 cache that left files behind, `alm-uft-cache-purge-incomplete`; and a conversion that could not keep the analysis's reports in `analysis_reports/` before rewriting them, `alm-analysis-reports-not-kept`, after which the conversion went on). Each planned restart the supervisor makes logs one `alm-crash-planned-restart` info line (§9). A conversion that keeps the analysis's reports in `analysis_reports/` logs one `alm-analysis-reports-kept` info line. Every run that counted test cases logs one `alm-test-case-count` info line (§4), and every analysis that parks tests one `alm-parked-references-read` info line (§4). Each discovery that reached the Test Plan also logs one `alm-discovery-walk` info line: the start folder, the folders walked, the tests seen of every type in each top-level folder, the skips it counted, the check against the project's test list and, for a failed discovery, the error. In PowerShell: `Select-String -Path migration_log.txt -Pattern '"level": "error"'`. |
| `analysis_reports/` | The analysis's report set, copied before the conversion rewrote the same file names at the top of this folder; its `migration_log.txt` is the log as it stood when the conversion started, so it ends with the conversion's first lines ([usage.md](usage.md) § *ALM run artifacts*). After a conversion, the top-level `scan_report.*` and `analysis_*.html` describe the conversion; read the analysis's findings here. `kept_analysis.json` names the analysis it holds (the SHA-256 of that analysis's `alm_aom_results.json`, the same bytes `alm_analysis_results.json` holds once the pre-flight gate has passed) and lists the files. The executive summary and the Migration Console link the copy only while it holds the analysis the folder is judged on; after an `alm-analysis-reports-not-kept` warning, a copy left here is of an earlier analysis. `diagnostics collect` counts it and never reads it. |
| `alm_preflight.json` | The pre-flight verdict, written on every conversion run: `status` (`pass`/`fail`), the selected and eligible ids, and every disqualified, out-of-scope and warning asset with its `reason_code` and detail. When `status` is `fail`, no ALM write happened (§4). A conversion that continues an unfinished wave does not run the gate again (§9); it writes back the gate report the wave started under, which the wave recorded in the journal. |
| `resume/alm_test_results.ndjson` | The durable conversion journal — one JSON line per event, each written as it happens. Since 1.1.5 the records of an upload conversion also carry its conversion wave id (`wave`). The `record` field: per asset `intent`, `attempt`, `terminal`, `already-converted` and `resume-mismatch`; the write markers `upload-started` (written to disk *before* the first write of a test's payload — no marker means that write never started), `upload-saved` and `upload-verified`; the abort and rollback records `aborted`, `not-attempted`, `rollback-started`, `restore-started`/`restore-done`, `rollback-asset-done`, `rollback-finished` and `rollback`; crash recovery's `crash`, `budget-exhausted`, `reconcile-untouched`, `reconcile-vc-undo`, `legacy-in-flight-verified`, `operator-settled` and `wave-snapshot-refrozen`; the planned restart's `worker-recycle` (§9); the wave's own `run-start`, `run-end`, `run-result`, `wave-start`, `wave-attempt`, `attempt-end`, `attempt-interrupted`, `wave-phase` and `wave-end` (whose `outcome` says how the wave closed — `superseded-no-writes`, for example, for an unfinished wave that had written no test and was replaced by a launch with other inputs); and `session-lost`/`session-restored`/`session-reconnect-failed`. A write that another program blocks for a moment — a backup or sync agent, an antivirus scanner — is retried for about 8 seconds. It survives a killed run, and a re-run of the same run id reads it to continue an unfinished wave and to skip assets that are already converted. The `terminal` record also carries the test's path and name and its converted action layout (`action_renumber_map`, `action_name_folders`, `action_folder_has_code`, `function_library_links`), which is what lets a skipped asset still serve as a callee for the tests converted after it. A journal written by an earlier version of Phoenix lacks those fields, and a caller of an asset carried forward from one blocks with `that callee has no conversion record in this run` (see [troubleshooting.md](troubleshooting.md)). Read it first after an interrupted conversion. In PowerShell: `Select-String -Path resume\alm_test_results.ndjson -Pattern '"record": "terminal"'`. |
| `alm_aom_work/test_<id>_source/` | The test as downloaded by the **latest** attempt in this run folder. It is deleted and downloaded again on every attempt, so after a re-conversion it can hold the converted Python. Contains `Download.xml` (asset-owner manifest, §1a); a pasted copy's names the test it was copied from, before and after its conversion, because Phoenix never changes it. |
| `alm_aom_work/alm_rollback/test_<id>_source/` | The first-sight pre-conversion payload, written once on the first non-dry-run attempt in this run folder and never touched again. The copy lands under a temporary name and is renamed into place only once complete, so a copy cut short by a crash never looks complete. In an upload conversion it is made from the wave's copy (next row) as hard links where the disk allows, so it takes no extra space. `uft-migrate restore` without `--wave` puts back **this** copy; treat it, not `test_<id>_source`, as the original. A real conversion and a **deep** analysis (which AOM-builds every test) both create it; a standard analysis and a `--dry-run` rehearsal do not. |
| `alm_aom_work/alm_rollback/waves/<wave>/test_<id>/` | The copy one conversion wave froze of the test before it changed the test: `payload/` (exactly what the wave's first download held) and `manifest.json` (every file with its size and SHA-256, written last — a folder without it is a copy that never finished and is never used). Crash recovery, the wave's automatic rollback and `restore --wave` restore only from this copy, never from an older one. A `test_<id>.tmp-…` folder is a copy that died half-way; the next attempt deletes it. A `test_<id>.superseded-<time>` folder is a copy set aside — by `restore --accept-current-state`, or because the test changed in ALM before the wave wrote it and the wave froze it again. When a new wave starts, the copies of older waves that are closed and settled (§9) are deleted, except those of the newest one that wrote a test; a wave that wrote no test — a launch the pre-flight gate refused, for example, or one that only replaced function libraries, which the journal does not record — does not count, and its own copies go once a newer wave that wrote a test has finished. Only an upload conversion freezes these. |
| `alm_aom_work/alm_rollback/resources/<wave>/<id>/` | The bytes of each `.pfl` function library that conversion wave `<wave>` replaced while converting test `<id>`. The first copy the wave saves is kept; when a later attempt of the wave replaces bytes that differ from it, those bytes are kept beside it in a `replaced_<UTC time>_…` folder — and so are those of a second library of the same file name that the test links from another folder, since the first copy is kept by file name. Either way the per-asset note `EXISTING CONTENT REPLACED — prior copy saved to <path>` names the copy of exactly the bytes that write replaced. These copies are deleted with the wave's test copies (row above). |
| `alm_aom_work/alm_rollback/pasted_copy_owner_maps.json` | The first-sight record of each pasted copy this run folder has seen (§1a): which of the copy's own asset records stands for each relation in its manifest, by record id, with the test it was copied from and when Phoenix first saw it. Written by the first analysis or conversion that sees the copy, and never overwritten; a damaged file is ignored and left as it is. An entry Phoenix found by pairing the copy's records with its original's (§1a) carries `derived_by: source-correspondence`. A copy that a conversion renamed while its original was parked or converted differently is recognised and restored only through this file, so keep it with the rollback snapshots, and copy it to the same place in a new run folder before analyzing such a copy there. |
| `crash_breadcrumbs.log` | One JSON line written immediately before each ALM call of an upload or a restore, and around each AOM build (§9). The last line for a process that died names the step it died in. |
| `crash_recovery/<wave>/` | What the crash supervisor kept for one conversion wave (§9): per attempt `attempt_NN/` with `command.txt` (the password masked), `stdout.log` and `stderr.log`, plus, after a native crash, `crash.json` and a copy of Windows' `Report.wer` when Windows wrote one; the wave's `supervisor.log`; and `restore_commands.txt` when recovery stopped with tests still to restore. Crash dumps are never copied here. A wave that completes without a crash keeps only `command.txt` and `supervisor.log`, and only the newest two finished waves that wrote a test keep their folder (a wave that wrote no test does not count, even if it replaced a function library: library writes are not journaled); an unfinished wave always keeps its own. |
| `alm_wave_stop.json` | Written when a conversion wave stops and stays open (§9): the reason, the test, the copy to restore from and the next steps. The report set is left as it was. Deleted when a later upload conversion in this run folder ends without stopping. |
| `resume/alm_wave.json`, `resume/phoenix_run.lock` | A summary of the latest wave, written by the crash supervisor (the journal, not this file, decides everything), and the run-folder lock: while one Phoenix process converts, analyzes or restores an ALM project in a run folder, another such process is refused there. |
| `alm_aom_work/test_<id>_build/<TestName>/` | The AOM-built payload that was (or would be) uploaded. The converted Python is human-readable in the `Action<N>/Script.pts` files: `Action0` is the main flow, and `Action1` holds a source action only when that action was itself named `Action1` (about 60% of the reference test set) — otherwise the AOM's inert default is removed and the named actions occupy `Action2..N`, usually leaving no `Action1/` at all. Read the `.usr` `[Actions]` section for the name→folder map rather than assuming the numbering. A Deep analysis of a project over the free edition's limit, with no license that covers it, deletes `test_<id>_build/` once the test is checked and measured, so the folder is absent: the asset's notes say *The build was checked and measured, then deleted, because this project was over its test-case limit.*, and the measurements are in the reports ([licensing.md](licensing.md)). A build UFT still held is retried when the analysis ends, and the report names how many could not be deleted. |
| `scoping_summary.json`, `scoping_summary.html` | The analysis in counts and summary figures, with no names, paths, identifiers or test code, written by every analysis on both paths, for the customer to send Merito, if they choose, when scoping a license: the `license` decision without the licensee, `test_cases` by type and by scope, the analysis results, blockers by category, `cross_test` and `function_libraries` (schema `uft-phoenix-scoping-summary/1`). Never a name, path, id, run id or line of code. |
| `alm_aom_work/test_<id>_verify/` | The post-upload re-download used for byte verification. |
| `alm_aom_work/test_<id>_runresults/.../run_results.xml` | Test Lab run detail: `<ErrorText>` nodes carry the real failure; `<Parameter name=... value=...>` proves parameter delivery at run time. |
| `executive_summary.html` | The verdict + next-steps rollup with drill-down links, and **Run Timing**: when the run started and finished and how long it took, in the local time of the computer that wrote it (a conversion over every attempt of its wave, the time between attempts included; with more than one attempt it also gives the timing report's total, which leaves that time out). `executive_summary.json` carries the same as `timing`, in UTC (`started_utc`, `finished_utc`, `elapsed_seconds`, `run`, `basis`, and `attempts` for a conversion wave). |
| `scan_report.html`, `scan_report.md`, `analysis_assets_failed.html` | The analysis report and its failed-assets page. When a parked test's calls could not be read, each carries the section *Parked Tests That Need Manual Intervention* (in `scan_report.html` just before the *Recommended Remediation Queue*, in `scan_report.md` before the out-of-scope list, and first on the failed-assets page): per test its name and id, ALM path, why its calls were not read, with the error id when there is one, and what to do (§4, `parked-references-unread`); a parked test the analysis has no entry for (an analysis by an earlier Phoenix build) is listed there by id, with the gate's reason. The section is absent when every parked test was read. When a parked test calls a test that passed the analysis, each also carries *Tests Step 6 Refuses Because Parked Tests Call Them*, after it: per test its name and id, ALM path, the parked caller(s) or the refused test(s) it calls, and the pre-flight gate's refusal word for word (§4, `parked-caller`, `callee-disqualified`). With an error id, start from its record in the process logs (Error ids row). |
| GUI runs: `analysis_cli_*.log`, `run_cli_*.log` | Raw engine output as the console saw it. For an ALM conversion, `run_cli_stderr.log` also carries the crash supervisor's own lines, which start `[Phoenix crash supervisor]`; each attempt's own output is also kept in `crash_recovery/<wave>/attempt_NN/` until the wave completes without a crash. |
| `%LOCALAPPDATA%\Merito\UFT Phoenix\logs\*.ndjson` | Outside the run folder: one diagnostics log per process, named `<start time>_<role>_<pid>.ndjson`. Roles are `gui`, `cli` (it becomes `supervisor` when it supervises a conversion), `worker`, `collector`, and `build-child`, `analysis-child` and `discovery-child`, which write a file only once they have a warning or an error. Each line is one record: the envelope `timestamp_utc` (milliseconds), `level`, `event`, `role`, `pid`, `seq` (a gap is a lost record), `thread` off the main thread, and `ctx`, the bound context (`run_id`, `wave`, `attempt`, `test_id`, `step`, `retry`). `process-start` says which build ran (`phoenix.version`, `.commit`), on which Python, with or without a console, and with which crash settings; `run-bind` links the process to its run folder; `step` is each breadcrumb at millisecond resolution; `child-start`/`child-exit` name each child process and how it ended; `uft-force-kill` gives each kill of UFT its two taskkill exit codes (0 killed, 128 not running, 1 refused) and whether it waited its 8 seconds; `uft-remote-agent-stop` records each time Phoenix tried to stop a leftover UFT Remote Agent to finish a TD_80 purge (`outcome`: `stopped`, `not-running`, `failed` or `test-lab-in-flight`, and taskkill's `exit_code`); `temp-sweep`, once per ALM run in the `cli` or `supervisor` log, counts the old Phoenix folders it removed from `%TEMP%` (never their names); `exception` and `swallowed` carry the error in full (the Error ids row); the `alm-*` events are copies of `migration_log.txt`'s warnings and key events, which survive when that file is cleared. The ALM password is masked before anything is written. Search them like `migration_log.txt`: `Select-String -Path "$env:LOCALAPPDATA\Merito\UFT Phoenix\logs\*.ndjson" -Pattern '"level": "error"'`. |
| `%TEMP%\uft_*`, `%TEMP%\uftphx_alm_*` | Outside the run folder: Phoenix's scratch folders, each named with its prefix and eight random characters. `uft_alm_ari_manifest_` is a whole download of a test after its upload, read once to repair its asset records; `uft_pfl_`, `uft_pfl_verify_` and `uft_pfl_read_` hold a converted function library on its way to ALM and back; `uft_alm_mts_probe_` is the listing that finds leftover VBScript files; `uft_aom_build_` holds the isolated build's request and result; `uftphx_alm_results_` and `uftphx_alm_discover_` hold an analysis's worker results (and the answers of the parked-reference read, §4) and discovery's answer, with each worker's own `%TEMP%` (the ALM client's cache) inside. They hold customer test content and only the user who ran Phoenix can read them. Each goes as soon as Phoenix has read it; one left behind means a crash, a kill or a child process Phoenix could not stop, or that 1.3.0 or earlier ran here: those left a download of every uploaded test (about 4 MB on average) and a folder per analysed test for good. The next ALM run removes those not changed for 7 days, at most 500 a run (the `temp-sweep` record above counts them). Folders an elevated run left deny a normal user: delete them from an elevated prompt while no Phoenix process runs. |
| Error ids `E-<time>-<pid>-<seq>` | The `error_id` of an `exception` or `swallowed` record. It is copied to where the failure shows: the CLI's failure result (`error_id`), the crash supervisor's failure result (`error_id`; its message itself names no id), the journal's `attempt` and `terminal` records, `alm_aom_results.json` (`error_id`, and `error_ids` for errors an asset carried on past; a parked test whose calls could not be read carries its `error_id` in `parked_references`, and the analysis report prints it) and the `alm-test-processing-completed` event. A test whose isolated AOM build failed (`aom-build-failed`) carries the id of the build child's own record. `error_ids` names only records written in full: a process writes the first 3 of one swallowed fault (its site and `fp`) in full and from then on only counts it, in `swallow-summary` records, which triage adds to the fault's scale. The record gives the exception type and message, every COM error in its chain (HRESULT, `scode` and the server's description), the innermost Phoenix frame that is not a generic helper (`where`) with its source line, the helper and the first frame outside Phoenix (`helper`, `boundary`), the COM member being read or called (`member`, `access`), the frames, and a fingerprint `fp` that stays the same for the same fault across retries and runs. Search for the id: `Select-String -Path "$env:LOCALAPPDATA\Merito\UFT Phoenix\logs\*.ndjson" -Pattern 'E-20261006T101500Z-7720-41'`. |

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
  `Test.tsp` included. In the reference conversion every uploaded file came back
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
restore that does not put it back fails when the frozen copy has one. A pasted
copy's action records are re-pointed by id through its first-sight record
(§1a); without that record, a restore that cannot place every one of the copy's
action records fails rather than report the copy restored. Tests already
converted in this wave are carried forward, not converted again. While this
happens, the Migration Console's status line shows the supervisor's latest
message.

**The crash budget.** Recovery stops relaunching at the third crash while the
same test is in flight, when the wave's crashes reach the wave's crash budget,
or at the second crash in a row that happened outside any test with no test
finished in between. The wave's crash budget is 6 plus 2 % of the tests the
wave has begun converting, rounded down: 6 until it has begun 50, 7 at 50, 8
at 100, 12 at 348, 106 at 5,000. A test counts once, when the wave first
starts converting it: converting it again after a crash, carrying it forward
as already converted and restoring it add nothing. The start and relaunch
messages give the budget as it stands and how it was reached, and every
crash's `crash.json` and journal `crash` record carry it as
`wave_crash_budget`. A wave an earlier Phoenix opened keeps that build's fixed
budget of 6 when this build continues it. The reverse does not hold: finish an
open wave with the build that opened it or a newer one. An earlier Phoenix
(1.3.0, for example) applies its fixed 6 to any wave, so at its next launch it
can abort and roll back a wave that the newer build said would continue.
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

**Planned restarts (memory).** Only a supervised upload conversion restarts
this way; an analysis, a gate rehearsal and a filesystem run never do. The
worker is a 32-bit process, so it has at most 2 GB of address space. Once it
has finished at least 25 tests in one attempt (a test that failed counts) and
its memory is high — 1,100 MB of private memory, or 700 MB or less of address
space left — it ends itself between two tests, after a test that converted
`ok` and never after the last one. It commits a `worker-recycle` journal
record, disconnects from ALM the normal way and exits with code 3, recording
no result, and the supervisor starts it again in convert mode. This is no
crash: no `crash` record is written, the wave's crash budget does not move,
the supervisor neither stops UFT nor collects Windows evidence, and its
message says *Restarted the conversion process to free memory (attempt N,
planned restart K of at most 100 in this session)*. Exit code 3 alone does not
mean a planned restart — with Python's fault handler on, a native crash exits
3 as well (*Do not set `PYTHONFAULTHANDLER`*, below) — so the supervisor also
requires the attempt's last journal record to be `worker-recycle`, after at
least one finished test. The relaunch carries forward the tests this wave
converted without reading them from ALM again, across any number of planned
restarts in a row: the supervisor holds the run-folder lock across its
attempts, so no `restore` can run between them. After a crash relaunch, or a
new launch of the conversion, each such test is checked in ALM once before it
is skipped, and is trusted again after that; a test an earlier run converted
is checked in ALM every time.
A test that failed in the earlier attempt is converted again, as after any
relaunch. A worker that crashes natively while it shuts down after its
`worker-recycle` record is recorded as a crash at location `after-recycle`
(in `crash.json` and the journal's `crash` record; the message says it
*crashed while shutting down*). Its evidence is collected and UFT is stopped,
as after any crash, but it is relaunched as planned with no crash budget
charged, and that relaunch checks the converted tests in ALM before it skips
them. A supervisor session — one launch of the conversion — makes at most 100
planned restarts. A restart needed after the 100th is not made: the run ends
with `planned-restart-limit` (exit code 2) and the wave open, and running the
conversion again with the same inputs continues it, with a new session.

**What is never relaunched.** A worker that exits by itself, successfully or
not (a wave that stopped included, and a conversion refused over the free
edition's limit, `license-limit`, whose wave closes `closed-no-writes`),
unless it ends for a planned restart (above);
Ctrl+C or a closed console window; a
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
  breadcrumbs, the crash counts and the wave's crash budget the decision was
  taken against (`wave_crash_budget`), what was cleaned up and a summary of the
  WER report, with the
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

**Conversion waves.** One all-or-nothing conversion of the project is a *wave*:
its id, `W<date>T<time>Z-<6 hex>`, appears in the journal, in the evidence
folder and in every message about it. A wave spans every attempt it takes —
crash relaunches, planned restarts (above), and launches after a cancel or a
stop — until it finishes or is rolled back. It is *settled* when no test in it
may still be half-written or half-restored. A launch with the same inputs
continues an unfinished wave, and its discovery must find the tests the wave
started with: when some are missing it runs once more, and if they are still
missing the conversion stops (`wave-scope-changed`) before it writes anything —
run it again first, since a transient listing fault can cause that. A discovery
that fails outright, even after its retry, stops the wave the same way
(`discovery-failed`): the half-written test a crash may have left is checked
only once discovery succeeds, so run the same command again soon. The supervisor
treats both like any other stop and does not relaunch. A launch with other
inputs closes an unfinished wave that has not written any test (outcome
`superseded-no-writes`) and starts a new one, but is refused once the open wave
has written a test, with the options that differ and the `restore
--abandon-wave` command that closes it; and no new wave starts while any wave in
the run folder is unsettled ([alm_safety.md](alm_safety.md) § *Interrupting and
resuming*). When a test the wave already froze changed in ALM before the wave
wrote it — after a Cancel, say — the wave freezes its copy again from what ALM
holds and keeps the old one beside it (`alm-wave-snapshot-refrozen`). A wave
that cannot go on safely *stops*: it writes nothing more, leaves the report set
alone, writes `alm_wave_stop.json`, exits 2 and stays open, so the same command
continues it once the named step is done. A copy that cannot be made at all — a
full disk, for example — is such a stop too (`snapshot-failed`). The reasons,
and what to do about each, are in [troubleshooting.md](troubleshooting.md) §
*The conversion stopped and stays open*.

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
| `environment\` | Windows, Python, pywin32, UFT One and the ALM client; the edition in use (its license id, limit, dates and number of ALM projects, and each license file's store and status — never the licensee, a path or a signature); WER and LocalDumps settings; the WER reports and Application events 1000/1001 of the window; `doctor`'s read-only checks, without the `license` row, which names the licensee; dumps and `%TEMP%` leftovers counted, never opened |
| `logs\` | The process logs of the window (§5) |
| `run\run-1\` | The run folder's allow-listed files under their own relative paths: the journal, `migration_log.txt`, the breadcrumbs, the results and `crash_recovery\` |

ALM names in it are tokens (`project-1`, `test-3f9a2c`), and so is the
licensee of a UFT Phoenix license (`licensee-1`), with the ALM projects a
license names, wherever a `licensee` field or Phoenix's own license sentences
carry them; numeric test ids are kept, and the map back to the real names
stays with the customer.

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