# Blocker Remediation Guide

An ALM conversion is fail-closed twice over: a pre-flight gate checks the whole
selection against the analysis in its own run folder before the first ALM
write, and any test whose conversion produces blockers is refused. At the
default Standard depth the gate proves that the converter reported no blockers,
not that each test builds in UFT — it says so itself, as a
`standard-depth-evidence` warning in `alm_preflight.json`; run a Deep analysis
for build-proven evidence. This guide covers the blockers the converter raises,
the pre-flight gate's refusal codes, the filesystem scan findings that hold a
verdict without stopping a conversion, and the warnings worth acting on. The
full coverage matrix is in [supported_versions.md](supported_versions.md); deep
diagnosis in [advanced_troubleshooting.md](advanced_troubleshooting.md).

## Blockers and their fixes

**1. `executefile` — script loads a library at run time**
`ExecuteFile` blocks **unconditionally**: the converter routes the statement to
its unsupported-construct handler, and the filesystem scan flags
`language-executefile` at error severity. The blocker is raised on the statement
itself, so linking the library to the test does not clear it. The fix is two
steps — link the library to the test (ALM: *Test Resources* tab; local: the
test's library list) **and delete the `ExecuteFile` statement**. A linked
library is converted once to a Python Function Library (`.pfl`, the Python
analog of `.qfl`) and linked to each converted test (not inlined into actions);
the converted test loads the linked `.pfl` into each action's namespace on
entry, so the loader call is redundant. ALM conversion uploads the `.pfl` as a
shared ALM "Function library" resource; local conversion writes it once to a
shared `FunctionLibraries/` directory under the output root.

**2. `Parameter()` read with no matching definition**
Reported as `<Action>: Parameter() referenced but no parameter definitions
(action or test-level) were found on the legacy test`, or `<Action>:
Parameter() references ['Name'] not found among the legacy test's action or
test-level parameter definitions`. A filesystem conversion words them
`<Action>: Parameter() referenced but no parameter definitions were found` and
`<Action>: Parameter() references ['Name'] not found among the local test's
action or test-level parameter definitions`.

Both **action-level** parameters (Action Properties → Parameters) and
**test-level** parameters (File → Settings → Parameters) are harvested from the
source test via UFT and re-authored on the converted Python test; test-level
definitions also satisfy `Parameter()` reads in any action that defines none of
its own, including the main flow (Action0).

The check is per action, not per name. An action that defines any parameters of
its own is not checked further, so a read of a name it does not define raises no
blocker and fails at run time — review those reads by hand. An action with no
definitions of its own blocks when a name it reads is also missing from the
test-level definitions.

Harvesting needs UFT, so this blocker appears only in a **Deep** ALM analysis or
in a real conversion. A Standard analysis (the default) never opens UFT; it
notes instead that the definitions will be harvested at conversion time, and a
filesystem scan never raises the blocker at all. An ALM asset can therefore pass
analysis and the pre-flight gate and then block during the conversion, which
aborts and rolls back the whole run. Run a Deep analysis (Analysis Depth = Deep)
before the conversion window on any project whose actions read `Parameter()`.

The fix is to add the missing definition in UFT, or replace the read with a
DataTable/Environment lookup. (Note: test-level default *values* carry, but
test-set runtime overrides do not propagate through the AOM main-flow
indirection.)

A third message, `Parameter() referenced by [...] but harvesting definitions
from the legacy test failed: <error>`, is not a missing definition: UFT could
not open the test to read them. Phoenix already retries transient UFT faults
three times, so read the error text and, if it names a UFT or license fault,
re-run.

**3. `shared-assets` — the test owns no matching asset records** *(hard stop, no override)*
A test whose stored `Download.xml` names another test is usually an ALM
copy/paste, and that alone is not a stop. When ALM gave the copy its own asset
records (Phoenix checks this), it is a *pasted copy*: it converts like any other
test, from its own records, its notes name the test it was copied from, and the
scan report counts it in a *Pasted copies* row. Until a live run has measured
how UFT runs a converted copy, do not park a pasted copy while its original
converts, or the original while the copy converts.

`shared-assets` is what is left: the test owns no asset records of its own, or
its records do not match its manifest — for example a pasted copy converted
while its original was parked or converted differently, analyzed in a run
folder that does not hold Phoenix's first-sight record of it. The error names
the other test. Converting that test does not clear a test that owns no
records, or one whose records differ from its manifest in a way other than a
conversion's rename: that asset stays disqualified at the pre-flight gate. A
copy whose records its own conversion renamed is recognised again once its
original has been converted with the same actions — unless two action
records of either test share a description, which the error then names — or
once its first-sight record is in the run folder (copy
`alm_aom_work\alm_rollback\pasted_copy_owner_maps.json` there from the run
folder that first saw the copy). Do not park a `shared-assets` test on its
own: the other test converts in any run that proceeds. Both ways to give the
test records of its own change its identity — paste it again with *create
copies of related entities*, or save it as a new test from UFT, and it gets a
new test id and leaves its Test Lab history with the old one. If the copy is
redundant, point its callers at the other test and delete it instead. See
[advanced_troubleshooting.md](advanced_troubleshooting.md) §1a, which also
covers the renamed copy.

**4. Dynamic code (`Execute` / `Eval`)**
Replace the dynamic dispatch in the **VBScript source** with explicit calls or a
function map. A custom mapping rule cannot clear this blocker: mapping rules run
over the Python the converter has already emitted, after the blocker was
recorded, and the filesystem scan reads the unmodified VBScript source and never
consults mappings at all.

The **filesystem scan** raises this blocker for both the statement form and
`Eval` inside an expression (`x = Eval("…")`). The **converter** recognizes only
the statement form, and the whole-ALM-project path takes its blockers from the
converter rather than the scan detectors — so on that path `x = Eval("…")`
passes silently and is emitted verbatim as Python that fails with `NameError`
only when UFT runs the test.

**5. `converted output is not valid Python`**
Four constructs reach the converter unrecognized: `GoTo`, `On Error GoTo
<label>`, `Class` blocks, and `#…#` date/time literals. It passes them through
and the result does not parse, so the syntax gate refuses the asset with
`converted output is not valid Python …` — on ALM analysis and on both
conversion paths. `--allow-blockers` cannot override it.

For an action converted from VBScript, the message ends by asking you to report
a converter defect. Before you do, open the named action at the reported source
line and look for those four constructs. Rewrite them in the source —
structured control flow instead of `GoTo`, `On Error Resume Next` with `Err`
checks instead of `On Error GoTo`, a function library instead of a class, and
`DateSerial(2000, 1, 1)`, `TimeSerial(10, 30, 0)` or `CDate("1/1/2000")` instead
of a `#…#` literal — then re-run the analysis. If none of them is present, the
message is right: report it with the run id and the action's VBScript. A message
that says instead that the Python source of an action does not parse refers to
an action that is already Python: fix it in ALM and re-run.

A filesystem scan names the date literal (`language-date-literal`, error
severity). It does not name `GoTo`, `On Error GoTo` or `Class` at all — they
raise at most a generic review warning — so a clean filesystem verdict is not
evidence that they are absent.

**6. Cross-test reusable-action references (RunAction/LoadAndRunAction)**
The test calls a reusable action that lives in another test. For **ALM
conversion** this is not a blocker: because ALM conversion is whole-project,
the callee is converted in the same run and the caller's external reference is
reconstructed natively (via `AddExistingAction`) so the shareable action stays
in its own test and is consumed by reference.

A reference that points at a test **outside the project being converted** is a
different matter: fix it so it points at a test inside this project. Converting
the other project in a separate run does not help — the pre-flight gate resolves
every reference against this run's own analysis records, so a caller whose
callee is elsewhere is refused as `unresolved-callee`, and every test that calls
that caller is refused as `callee-disqualified`.

For **local filesystem conversion**, a caller that references an action in
another local test must have that callee converted in the same batch (whole call
chain together); a reference whose local callee is not converted fails closed
rather than producing a test that can't resolve the call.

**7. Missing resource path references**
Fix broken absolute paths or convert them to relative. Per-action object
repositories and the test DataTable are carried into the converted test
automatically; external resources referenced by absolute path should be made
reachable (or relative) before conversion.

**8. Dependency cycles**
Refactor cyclical library/action references into a shared utility layer, then
re-run the analysis until the cycle clears: `scan` for a filesystem estate,
where it is a `dependency-cycle` blocker, or `convert --alm --dry-run` (the
Migration Console's *Analysis* step) for an ALM project, where it shows as
*Dependency Cycles* above zero and keeps the verdict no-go. A conversion
attempted while a cycle remains is refused by the pre-flight gate with reason
`reference-cycle`, recorded in `alm_preflight.json`.

**9. `linked function libraries could not be resolved`**
The resource link exists but the download failed — check the resource still
exists in ALM and the account can read it.

**10. `Version control blocked` (status `vc-blocked`)**
A version-control operation failed for this asset. The usual cause is a
pre-existing checkout the connected ALM user is not allowed to undo — undoing
another user's checkout requires the "Manage checkouts"-equivalent ALM
permission — but a failed check-out or check-in carries the same status, so
read the asset's error text first. Grant that permission to the migration
account (or have the holder check in / undo their own checkout), then re-run
the whole-project conversion. There is no failed-asset-only re-run: ALM
conversion is whole-project and all-or-nothing, so `--failed-only` is refused
for it (it applies to ALM *analysis* — `--dry-run` without `--upload`). Do not
reach for `--resume`: it is never forwarded to the ALM pipeline, and because a
vc-blocked run ends in the `failed` state it is refused outright (exit 2) once
that run's rollback has completed. To
land the new run in the same folder, pass the same `--run-id` *without*
`--resume`.

That re-run converts everything the aborted run did not leave converted: the
vc-blocked asset, the assets recorded `not-attempted`, and the ones the abort
rolled back. An asset that an earlier conversion in the same run folder already
uploaded and verified, and that the server still holds as Python, is not rebuilt
— it is carried forward, reported `ok`, and counted under *Carried Forward* in
the executive summary. A carried-forward asset still serves as a callee: its
journal record holds the converted action layout its callers need, so a caller
converted later in the re-run is retargeted as usual. The one exception is a
journal written by an earlier version of Phoenix, before that layout was
recorded: a caller of a test carried forward from it blocks with *that callee
has no conversion record in this run* and stops the run. Convert in a new run
folder (a fresh run id, with the analysis run under it first) so caller and
callee convert together. If a pasted copy was converted while its original
was parked or converted differently, first copy
`alm_aom_work\alm_rollback\pasted_copy_owner_maps.json` from the earlier run
folder to the same place in the new one (blocker 3).

## Pre-flight gate refusals (`alm_preflight.json`)

A whole-project ALM conversion is judged against the analysis in its own run
folder before the first ALM write. If any asset is disqualified the run stops
with `status: preflight-failed`, nothing is written to ALM, and every
disqualified asset is named in `alm_preflight.json` with a reason code and a
`detail` line naming the asset, reference or blockers involved.

| Reason code | What it means | Fix |
| --- | --- | --- |
| `not-analyzed` | This run folder holds no analysis record for the asset. | Re-run the analysis into the same run id, or park the asset with `--alm-exclude-test-id` (park a test together with everything it calls and everything that calls it: see `parked-caller`). |
| `analyzed-but-not-selected` | The analysis covered it and it is in scope, but this run's discovery did not return it — not even the second time, which Phoenix runs before the gate when discovery comes back short (`alm-discovery-retried`). | If the test is still in ALM where it was, run the conversion again: a transient fault while ALM listed the Test Plan can cause this. Otherwise re-run the analysis so the scope matches, or park it explicitly. If the test was deleted from ALM, re-run the analysis rather than park it: a parked test that the analysis measured calling tests still in scope refuses them as `parked-caller`. |
| `blocked` — or any other non-`ok` analysis status (for example `shared-assets`, `no-actions`, `aom-build-failed`, `error`) | The analysis did not finish `ok` for this asset. The detail carries that analysis error, which for `blocked` quotes the first blockers. A pasted copy that owns its asset records is `ok` and is not listed here (blocker 3). | Fix the cause the detail names — see the blocker entries above. An `error` saying Phoenix could not read the test's asset records is a transient ALM fault, not a defect in the test: re-analyze the failed assets. |
| `converter-blockers` | Converter blockers on an asset the analysis nonetheless recorded `ok` — seen when the analysis ran with `--allow-blockers` and the conversion did not. The first three are quoted in the detail. | Fix them, or re-run the analysis without the override so it reports them too. |
| `unresolved-callee` | It calls a shareable action in a test that is not part of this analysis. | Re-point the reference at a test inside this project, or bring the callee back into scope if it was parked. |
| `ambiguous-callee` | Several tests in the project carry the callee's name and its path did not resolve. | Rename the duplicate tests in ALM. |
| `self-referencing-callee` | Its external reference resolves to the test itself. | Fix the reference in ALM. |
| `reference-cycle` | It belongs to a cross-test reference cycle, which the detail names in full. | Break the cycle. |
| `parked-caller` | A test parked out of this run — listed in *Out-of-scope test IDs* (`--alm-exclude-test-id`), or left out by a path filter: a *Path Exclusions* (`--exclude`) pattern it matches, or a CLI `--include` pattern it does not match — calls a shareable action in this test. The parked caller stays VBScript, and a shareable action runs in its caller's script engine, so converting this test to Python would break that call at run time. The detail names up to three callers, then *and N more*. A parked test may also call this test without naming it unambiguously: its call names no test of the analysis by full path (the test it called may have moved or been renamed since), and its name matches more than one test — several analyzed tests, or an analyzed test and a parked test, which can be the calling test itself. Phoenix cannot tell which one the call means, so it refuses each of them this run would convert rather than guess. That detail starts *May be called by a parked test, which stays VBScript, through a call that matches more than one test*, or, when a known parked caller also calls the test, continues after the known caller's detail with *It may also be called through a call that matches more than one test*. Either way it names each such call (after *Unmatched call(s):* in the first form) (the parked test, the path it calls, and the tests its name matches). A call whose full path names another parked test, or a test a path filter or its type leaves out of the analysis, means that test and refuses nothing this way. The analysis report lists each such test, with the tests that call it, under *Tests Step 6 Refuses Because Parked Tests Call Them*, before the conversion is tried. *Conversion Failed* quotes one example per reason code; `alm_preflight.json` holds every test's detail. | Fix and un-park the caller(s), or park this test too, with the rest of its call chain (every test that calls it or that it calls, directly or not). For an unmatched call: fix that call in ALM so it names its test by full path, then re-run the analysis; or park this test with its call chain, or un-park the caller with its chain. When that caller is left out by a path filter, the analysis never reads it, so re-running it hides the call without fixing it (the detail says so): fix the call in ALM first. For a caller in *Out-of-scope test IDs*, re-running the analysis with it still parked does not clear this refusal: the analysis reads which tests each parked test calls (read-only; see `parked-references-unread`), in the Migration Console as on the command line. A caller left out by a path filter is different: the analysis never reads it, so the gate sees its calls only when the analysis it judges measured it (a test moved since then into a folder a path exclusion removes, for example), and re-running the analysis with it still left out hides the call without fixing it. The detail says which case applies. If a calling test was deleted from ALM since the analysis, re-run the analysis. A test in a `.TrashCan` or `Recycle Bin` folder never counts as a caller. |
| `parked-references-unread` | A test parked out of this run in *Out-of-scope test IDs* (`--alm-exclude-test-id`) whose calls Phoenix could not read. It stays VBScript, and whether it calls a test this run converts is unknown, so it is refused under its own id. The detail starts with what to do and ends with *Not read:* and the reason: the analysis could not read the test from ALM (*could not read the test (ALM): …*, or a reading process that crashed, did not answer or could not log in); ALM did not find it (*not found in ALM*); its analysis record stopped before its calls were read (status `error`, `not-found`, `vc-blocked`, `process-crashed` or `shared-assets`), which is what *Refresh Report* leaves when you park such a test; the analysis this conversion is judged on never saw the test (a path exclusion left it out then, or it is newer); or the run folder's analysis was made by an earlier Phoenix build, which did not read which tests a parked test calls. The analysis report lists each such test under *Parked Tests That Need Manual Intervention*. | Re-run the analysis with the test still parked: *Run Analysis*, or `convert --alm --dry-run` (*Re-analyze Failed Assets* reads it as well, when the button offers that). The analysis reads the test's calls from ALM, read-only. *Refresh Report* does not read ALM and cannot clear this. If the read fails again, ALM cannot give this test's definition: delete the test in ALM if it is no longer used, or bring it back into scope and fix it there. If ALM did not find the test because it was deleted, a full analysis no longer lists it. The Migration Console has no override. On the command line `--allow-partial-conversion` overrides it, and the run still holds approval (below). A test in a `.TrashCan` or `Recycle Bin` folder never counts. |
| `callee-disqualified` | A test it calls cannot be converted in this run; the detail names the callee. When that callee is refused as `parked-caller`, the analysis report lists this test with it under *Tests Step 6 Refuses Because Parked Tests Call Them*. | Fix the named callee, or bring it back into scope if it was parked. If the callee is refused as `parked-caller`, follow that row: un-parking its caller, or parking the whole chain, clears both. |

`--allow-partial-conversion` overrides the gate: the run converts the eligible
assets and knowingly leaves the project part Python and part VBScript, with
every cross-test action chain through a skipped asset broken. The gate still
runs and still names every disqualified asset. A parked test refused as
`parked-references-unread` is not one of the skipped assets: you parked it, so
it was never part of the conversion and stays VBScript. The override over it
still holds approval. The executive summary lists *--allow-partial-conversion
was used over N parked test(s) whose calls could not be read* under its gate
failures, `uft-migrate summarize` over that run folder says the same, and the
command exits 2, even when every test in the conversion converted.

Failures during the conversion itself are a separate list. The analysis and
conversion reports carry a **Failure Breakdown by Category** table with a
*Recommended Action* for each per-asset status.

## Filesystem scan findings that still convert

A filesystem scan runs detectors the ALM path does not. Several are error
severity and hold the scan verdict at no-go, but no gate stands between the scan
and the conversion: the command line converts every discovered test whatever the
verdict says, and the Migration Console only asks you to confirm *Proceed With
Findings* first. Strictness still decides whether a test carrying a converter
blocker is built — see *Strictness strategy*. Treat these as a review list, not
a stop.

- `uft-checkpoints-output` — `Checkpoint` / `OutputValue`.
- `uft-property-method-ambiguity` — `GetROProperty`, `GetTOProperty`,
  `SetTOProperty`.
- `uft-native-object` — `.Object` native access.
- `uft-descriptive-whitespace` — a descriptor whose value begins with the
  regex whitespace class (`"name:=\s+Foo"`); the report calls it a
  whitespace-sensitive descriptive string. Confirm the object still matches
  after conversion. Regular-expression descriptors in other shapes are not
  flagged.
- `language-dictionary` — `Scripting.Dictionary`.
- `language-regexp-com` — COM `RegExp`.
- `language-byref-byval` — a literal `ByRef` or `ByVal` keyword in a signature.
- `enterprise-alm-reference` — an `[ALM]`, `td://`, `qc://` or `alm://`
  reference inside a script.
- `language-date-literal` — a `#…#` date/time literal. This one is more than a
  review item; see blocker 5.
- `unresolved-dependency-edge`, and `missing-resource` for the same reference —
  a resource reference the scan could not resolve to a file: missing,
  unreachable, or built dynamically. See blocker 7; an unresolvable *linked
  function library* is more than a review item and stops its own test below.

Ordinary framework code raises several of these on nearly every test, so
"re-analyze until the report is clean" is not a reachable end state for a
typical estate. Review each finding against
[supported_versions.md](supported_versions.md), accept it, and approve on that
evidence rather than chasing a green verdict.

Two findings do stop their own test at every strictness: an unresolvable
reference (a missing linked function library, or a cross-test callee that cannot
be resolved), and converted output that Python cannot parse. Both are named in
the conversion report.

The ALM path does not run these detectors — it checks cross-test references and
dependency cycles by its own rules (see blocker 6 and the pre-flight table) — so
an ALM project full of checkpoints can still report go. If you need those
constructs found across an ALM estate, search your own source for them.

## Warnings worth acting on (not blockers)

- **`unrecognized-object-member`** — framework wrapper methods the converter
  doesn't know. Add only names that really are methods: `custom_uft_methods`
  (Migration Console: *Custom UFT Methods*) is a parentheses-enforcement list,
  so a property name added there gets `()` appended wherever it is read. The
  warning's usage label helps — `method-call` and `method-call-no-parentheses`
  are methods; `member-access` can be either a property read or a no-argument
  call, so check the snippet before adding it.
- **Out-parameter writes** — a procedure that writes its own parameter, flagged
  whether or not `ByRef` is spelled: by the converter's own warning on both
  paths, and as `language-implicit-byref-out-parameter` in a filesystem scan.
  VBScript passes ByRef by default, so the write reaches the caller's variable;
  Python parameters are by value, so the caller keeps its old value. Return the
  value and update the call sites, or confirm the write is scratch-only. The
  literal `ByRef`/`ByVal` keyword is a separate, error-severity finding that
  only a filesystem scan raises.
- **Empty/Null/Nothing collapse** — review any logic distinguishing
  `IsEmpty` / `IsNull` / `TypeName` results.
- **Eqv/Imp on integers** — these convert with boolean semantics (`==`, `<=`)
  while VBScript is bitwise on integers, so review integer operands. The
  warning still opens "Eqv/Imp/Xor" for continuity with older reports; `Xor`
  converts exactly. An expression that mixes a top-level `Eqv`/`Imp` with a
  top-level `&` is a blocker, not a warning — add explicit parentheses.
- **Reserved word collisions** — a VBScript identifier that is a Python keyword
  (for example `pass`, `import`) or one of the Python builtins the generated
  helpers rely on (for example `str`, `len`) is renamed with a `_vbs` suffix,
  and `_vbs_2` onwards if that name is taken. No warning is raised and no
  mapping file is written, so search the converted scripts for `_vbs` wherever
  other code refers to those names as text.
- **On Error regions** — statements are guarded individually with a faithful
  `Err` object; validate intended skip/continue behavior on error paths.
- **ALM entity locks** — a lock never fails an asset. After a 10-second
  grace period and a release attempt, the asset is converted and
  **overwritten** either way (an ALM lock does not gate
  `ExtendedStorage.Save`, only entity metadata writes). The run records
  `entity-lock-force-revoked` or `entity-lock-not-cleared-proceeding`, and
  the asset's note names the lock holder — plus their machine, ALM session id
  and lock times when the migration account can read the project's LOCKS table
  through OTA, which is usually only the case where the lock was revoked.
  Nothing to re-run — but whoever was editing that asset has lost their
  work and may hold a stale copy in their ALM client. On a version-controlled
  project, use the analysis report's **Version Control & Locks** section as the
  chase list to get people out of the project *before* the window; that section
  is rendered only where the project uses version control. Without it, a lock
  shows only in the notes of the assets it affects.

## Strictness strategy

Strictness is a **filesystem-conversion** lever. The whole-project ALM path
runs at `strict` unconditionally — analysis as well as upload — because ALM
conversion overwrites live tests in place, and the analysis pass must judge each
asset with the same converter that would convert it. `convert --alm --dry-run`
(the Migration Console's *Analysis* step, at both Standard and Deep depth) goes
through the same per-test routine as the upload, so whatever Strictness you set
is coerced there too: silently for `standard`, with a per-asset note for
`permissive`.

- `strict` — refuse to build any test that carries a converter blocker (the
  rest of the wave still converts), and fail a filesystem run's status while
  any scan blocker or review-required finding remains. Use for release
  conversions (forced automatically on the entire ALM path, analysis and
  upload).
- `standard` — record the blocker, replace the blocked construct with a
  `# SKIPPED` comment, and still build the test.
- `permissive` — replace the construct with a `raise NotImplementedError` stub
  and record a warning rather than a blocker. The test still reports converted
  and fails only when that line runs. Filesystem exploration only; it never
  reaches an ALM run.

Strictness changes which tests are built and the run's pass/fail status, not
what is found: every strictness inventories every finding in one pass. Two
blockers ignore it entirely — an unresolvable reference, and converted output
that Python cannot parse, refuse their test at every strictness.

## The override, and when not to use it

`--allow-blockers` (CLI only; the Migration Console has no override — park
deferrals on Step 5) uploads a blocked test anyway and records the override in
the run notes. It is an **ALM** lever: on a filesystem run it is not consulted
at all, and Strictness is what decides whether a blocked test is built. The
only legitimate use is a blocker you have personally verified is unreachable
(dead debug branches).

Uploading under the override does not mean the test fails where the blocker is.
ALM conversion always runs at `strict`, so an unsupported construct — an
`Execute`, `Eval` or `ExecuteFile` statement, or an `Exit For`/`Exit Do` aimed
at the wrong loop kind — becomes a `# BLOCKED:` comment and silently does
nothing at run time. A dropped `Exit` can let a loop run on or never end. Some
blockers convert to logic Phoenix already knows is wrong, such as an `Eqv`/`Imp`
mixed with `&`. Others fail only when the line runs, such as a `Parameter()`
with no definition. The test can pass while skipping or miscomputing work, so
never use the override to make a status report green.

## Remediation loop

1. Run the analysis — `scan`/`analyze` for a filesystem estate,
   `convert --alm --dry-run` (the Migration Console's *Analysis* step) for an
   ALM project — and read the Scan HTML blocker inventory.
2. Fix at the source where possible (link libraries and delete the
   `ExecuteFile` lines, add missing parameter definitions or replace the
   `Parameter()` reads, remove dead dynamic code).
3. Add custom mapping rules for mechanical, framework-specific patterns. Rules
   tidy lines that already convert; they cannot clear a blocker, because they
   run over the emitted Python after the blocker has been recorded.
4. `Re-analyze Failed Assets` (Migration Console) or `--failed-only` until only
   reviewed, accepted findings remain.
5. **ALM projects only:** for anything you are deferring rather than fixing,
   copy the report's **Park the Failed Assets** list into *Out-of-scope test
   IDs* (Step 5, Risk Analysis) and re-analyze — parked assets leave the scope
   and stop counting as failures. Park a shareable-action chain whole or not at
   all: parking a test that a surviving test calls turns that call into an
   unresolved reference, so the report stays no-go, and parking a caller whose
   callee still converts would leave a VBScript test calling Python actions,
   which the pre-flight gate refuses (`parked-caller`, above): the analysis
   reads which tests each parked test calls, and its report lists every test
   the conversion would refuse for that under *Tests Step 6 Refuses Because
   Parked Tests Call Them*. The copy block leaves out a
   failed asset whose calls tie it to tests the block does not park, whether
   it calls them or they call it, and names the tests to park with it (*park
   only together with …*). It counts a call the way the pre-flight gate will
   once the asset is parked: a call that names no test by full path and
   whose name matches more than one test ties the asset to every test of
   that name. Assets the report marks "do not park" are
   withheld from the copy block too and stay in scope. If you park a failed asset whose
   analysis stopped before it read the test's calls (status `error`,
   `not-found`, `vc-blocked`, `process-crashed` or `shared-assets`) and
   refresh with *Refresh
   Report*, which does not read ALM, the conversion refuses it as
   `parked-references-unread` until *Run Analysis* has read it. On the
   filesystem path, *Out-of-scope tests* only removes tests from the
   conversion; their findings still count in the scan verdict.
6. **ALM project:** re-run the read-only analysis (`convert --alm --dry-run`,
   or the Migration Console's *Analysis* step) — no ALM writes, and no
   `--confirm-alm-backup` on the CLI (the Migration Console takes the backup
   confirmation earlier, on Step 3) — review the report, then convert for real
   with `--upload --confirm-alm-backup`. Convert into the same run id as the
   analysis you reviewed: pass the same `--run-id` to both, or give
   `--domain`/`--project` on the command line both times so the default
   `<Domain>-<Project>` run id matches. Domain and project read only from the
   config file produce a new timestamped id on every run, and the pre-flight
   gate then refuses every asset as `not-analyzed`. **Filesystem:** `convert`
   writes the converted tests every time; `--dry-run` is an ALM-only control and
   is silently ignored on a filesystem run, so there is no preview mode — review
   the previous `analyze`/`scan` report instead, and point `--output-root`
   somewhere disposable if you want a throwaway pass.
