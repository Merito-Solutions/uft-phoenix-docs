# Known Limitations

The complete conversion coverage matrix — what converts automatically, what
is approximated with warnings, and what fails closed — lives in
[supported_versions.md](supported_versions.md). This page covers the
boundaries and caveats that apply to the current release.

Phoenix offers exactly two conversion paths: **local filesystem** conversion
of UFT test directories on disk, and **whole ALM project** conversion. Both are
**AOM-canonical** — each test is opened, converted, and re-saved through UFT's
own Automation Object Model, producing a structurally valid, runnable UFT 26.1
Python test (never hand-patched binary `Test.tsp`/`.usr`, never a source-only
transpile). Both therefore require UFT installed locally; the filesystem path
saves to a local directory, the ALM path saves back into ALM (preserving each
test's ID). ALM conversion is all-or-nothing for a given domain/project — you
cannot convert an arbitrary subset. This is a hard rule, not a limitation to
work around: a callee action runs inside the *caller's* script engine, so a
call chain must be uniformly one engine (all Python). Converting the whole
project keeps every chain uniform and lets Phoenix rebuild cross-test
shareable-action references natively (see below). The CLI-only
`--allow-partial-conversion` override exists, but it knowingly leaves the
project half Python and half VBScript and is not a safe way to convert a
subset; see [alm_safety.md](alm_safety.md).

## Conversion boundaries (fail-closed)

These constructs are refused rather than converted. ALM project conversion
always runs at `strict`, so each one blocks its test and stops the
whole-project run unless it is overridden with the CLI-only
`--allow-blockers` (the GUI has no override). Local filesystem conversion
follows its Strictness setting, which changes what "refused" means — see
*Strictness on the local path* below.

- **Dynamic code** — `Execute` / `Eval` used as a statement (`ExecuteGlobal` is
  refused the same way). No deterministic translation exists; replace it in the
  source with explicit dispatch (a custom mapping rule cannot clear this
  blocker). (`Eval` *inside an expression* is a different case: the filesystem
  scan raises it, but neither path refuses it — see below.)
- **`ExecuteFile`** — every `ExecuteFile` statement is refused, whether or not
  the library it loads is linked to the test. Link the `.qfl` to the test (as
  an ALM Test Resource for ALM conversion, or on the test's library list for
  local conversion) so it is converted once to a Python Function Library
  (`.pfl`) and linked automatically, then **delete the `ExecuteFile` line** —
  linking the library does not clear the blocker.
- **`Parameter()` names with nothing to resolve against.** Action-level and
  test-level parameter definitions are both harvested from the source test and
  re-authored on the converted one, and a main-flow `Parameter()` read
  resolves against the test-level set. What fails closed is a name that is in
  neither: in an action with no action-level definitions of its own — the main
  flow always — a `Parameter()` name absent from the test-level definitions
  blocks the test. Only *default* values are carried; test-set run-time
  overrides do not propagate. The check is per action and needs UFT, so it runs
  during a conversion or a Deep ALM analysis, never in a standard ALM analysis.
  On a local filesystem conversion this blocker is waived at the default
  `standard` strictness, and unlike the constructs above it leaves no trace in
  the script: the `Parameter()` call is published unchanged, with no
  `# SKIPPED` comment, and the test fails at run time with UFT's
  `Parameter <name> not found`. Use `strict` if you want the conversion to
  refuse it.
- **Cross-test reusable-action callers require whole-project conversion.**
  A test that calls another test's reusable actions (`RunAction "X
  [OtherTest]"`) executes the callee inside the *caller's* engine, so the
  whole chain must be uniformly Python — a mixed VBScript/Python chain
  fails at runtime (a VBScript caller executing a Python callee errors on
  line 1). This is why ALM conversion is whole-project: converting the
  entire project together keeps every chain uniform and lets Phoenix see
  inbound references from any test. When a caller is converted, its
  external "call to existing action" references are **reconstructed
  natively** (via UFT's `AddExistingAction`) so the shareable action stays
  in its own test and is consumed by reference — the action body is never
  copied or inlined into the caller.

**Strictness on the local path.** `strict` refuses the test: the construct
becomes a `# BLOCKED` comment and nothing is built. `standard` — the shipped
default — still builds and publishes the test, with the construct replaced by
a `# SKIPPED unsupported …` comment and the blocker recorded as waived
(`OVERRIDE: proceeding despite N blocker(s)` in the conversion notes).
`permissive` publishes a `raise NotImplementedError(...)` stub in its place and
records only a warning. At `standard` the construct is silently skipped rather
than failed; at `permissive` it stops the action the moment it is reached. In
both cases the verdict alone will not tell you, so read the conversion notes as
well.

**Checkpoint/OutputValue objects and `GetROProperty`-family APIs are flagged
by the local filesystem scan only.** There they are **scan-report errors**:
they turn the run's verdict to `no-go` and are listed per line. **ALM project
analysis does not run those detectors at either depth**, so an ALM project full
of checkpoints can still report `go`. On both paths the line itself is still
converted (the UFT Python API's property model differs), so review every such
line before you approve the run. Before an ALM conversion, find them in your
own source:

```powershell
Get-ChildItem -Recurse -Include Script.mts,*.qfl,*.vbs |
  Select-String -Pattern '\.(Check|Output)\s*\(?\s*CheckPoint\s*\(|GetROProperty|GetTOProperty|SetTOProperty'
```

For an ALM project, run it over an export or over the downloaded folders named
in the next section.

### Not detected before conversion — find these yourself (known gap)

The **local filesystem scan** does not classify the first three constructs
below. They raise no blocker and no finding that names them — at most a generic
*"Call statement or implicit-call syntax detected"* warning, because the line
parses as an ordinary procedure call — and warnings do not affect the go/no-go
verdict. A filesystem scan of an estate whose only issue is a `GoTo` still
reports `go_no_go: "go"`; the conversion then refuses to build that test with
*"converted output is not valid Python"*.

**ALM project analysis is the exception.** It parses every converted action
body, so those three are refused at analysis time by that same *"converted
output is not valid Python"* blocker, which names the converted action and —
where it can map it — the source line number, and cannot be overridden. That
message describes itself as a converter defect — for the constructs below it is
not one, and the fix is in the VBScript.

Search your estate for all four and remediate the VBScript *before* you
convert:

- **`GoTo <label>`** (and its inline form `If … Then GoTo <label>`) — the
  label and the jump are emitted verbatim; the action does not compile.
- **`On Error GoTo <label>`** — emitted verbatim; the action does not
  compile. (`On Error Resume Next` and `On Error GoTo 0` *are* supported.)
- **VBScript classes — `Class` … `End Class`, `Property Get/Let/Set`** —
  emitted as calls (`Class(Cart)`, `Public(Property Get T)`); the action
  does not compile.
- **`Eval` inside an expression** (`x = Eval("…")`, as opposed to the
  statement form `Eval "…"`) — emitted as a call to an undefined `Eval`,
  which *does* compile and then raises `NameError` at run time. The local
  filesystem scan **does** raise this one, as a dynamic-code error that turns
  the verdict to `no-go`; ALM analysis is silent on it, precisely because the
  Python it produces parses. It is the one case in the list that reaches a
  live run.

A pre-migration sweep of the source, run from the root of your test estate,
finds them:

```powershell
Get-ChildItem -Recurse -Include Script.mts,*.qfl,*.vbs |
  Select-String -Pattern '(?<![\w.])(GoTo\s+(?!0\b)\w+\s*(''.*)?$|Class\s+\w+\s*(''.*)?$|Property\s+(Get|Let|Set)\s+\w+|Eval\s*\()'
```

It deliberately keeps `On Error GoTo 0` and member access such as
`obj.Class` out of the results; treat every remaining hit as a review item
(a match inside a comment or a string literal is a false positive), and note
that a `GoTo` or `Class` statement followed on the same line by a `:`
separator will not match.

For an ALM project, run the same sweep over an export, or over the folders a
GUI Analysis or `convert --alm --dry-run` downloads under
`out\<run id>\alm_aom_work\` in the folder you launched Phoenix from:
`test_<id>_source` holds each test's scripts and `test_<id>_libraries` its
linked function libraries. Remediation is ordinary VBScript refactoring:
replace `GoTo` with structured flow, replace a class with a function library,
and replace `Eval` with explicit dispatch.

The filesystem scan does not classify `GoTo`, `On Error GoTo <label>` or
VBScript classes, so that path's verdict does not reflect them the way the ALM
path's does; this manual sweep is the control.

## Semantic approximations (converted, with per-file warnings)

- `Empty`, `Null`, and `Nothing` all convert to Python `None`; code that
  distinguishes them (`IsEmpty` vs `IsNull` vs `TypeName`) is approximate.
- `Eqv` / `Imp` convert with boolean semantics: exact when the operands are
  conditions (`If a = 1 Eqv b = 2`), approximate on integers, where VBScript
  is bitwise (`5 Eqv 3` is -7) — those sites are flagged per file and need
  review. `Xor` is **not** approximate: it converts exactly, integers
  included (`5 Xor 3` is 6 in both languages).
- **Out-parameters do not propagate.** VBScript passes ByRef *by default*, so a
  procedure that assigns one of its own parameters updates the caller's
  variable; Python parameters are always by value, so the caller keeps its old
  value. This applies whether or not `ByRef` was spelled — the keyword is
  almost never written in practice. Every procedure that WRITES a parameter is
  flagged per site — by the local filesystem scan, and by the converter's own
  per-file warnings on both paths — naming the parameters involved. Rewrite
  those helpers to return their value(s).
  Two cases are correctly *not* flagged because nothing is lost: an explicit
  `ByVal` parameter (VBScript does not propagate it either) and an element write
  into an array parameter (`arr(0) = x`, which propagates in both languages).
  That concerns the out-parameter warning only. The local filesystem analysis
  separately raises an error-severity finding on any literal `ByRef` or `ByVal`
  keyword, which turns the verdict to `no-go`; see
  [supported_versions.md](supported_versions.md).
- `MsgBox` / `InputBox` convert to non-blocking shims (print /
  default-return) so batch runs never hang on a dialog; tests designed
  around human acknowledgement change behavior by design.

## Test-level artifacts not carried

A converted test is **rebuilt** through the AOM, not copied. Only what Phoenix
explicitly re-applies survives; **everything else in the source test comes out
at UFT's defaults.** That is the rule to plan against, and it is the safer way
round from a list of known gaps, because the gaps below are the cases we have
measured and can advise on — they are examples, not an exhaustive inventory.

What is re-applied in **both** conversion paths:

- the action map and action names, and cross-test shareable-action references
  (rebuilt natively via `AddExistingAction`)
- per-action object repositories (copied, and content-hash verified)
- the root `Default.xls` / `.xlsx` DataTable workbook
- action-level and test-level parameter definitions
- the linked function libraries

What **only ALM project conversion** re-applies:

- the per-action shared-repository (`.tsr`) associations — subject to the open
  defect documented below
- six `Settings.Run` fields: iteration mode, start and end iteration, on-error
  behaviour, object sync timeout, disable smart identification
- the associated add-in set

A local filesystem conversion carries none of those three, and the consequences
are concrete: a single-iteration source test comes out running every DataTable
row; a shared object repository is not associated at all, with no warning; and
the built test is saved with whatever add-ins the UFT session happens to have
loaded, which changes which class claims a window (see the add-in note below).
Set these on the converted test in UFT, or convert through ALM.

The counts in brackets below are how often each gap was hit in the reference
validation (116 tests, 239 actions). They are evidence that the gap is real, not
a statement of how often it will affect you.

- **UFT Environment variables are not carried.** Neither internal user-defined
  variables nor the association to an external environment XML file. Nothing in
  the rebuild reads or writes them, so a converted test starts with an empty
  Environment and every `Environment("name")` read returns nothing. Local
  filesystem analysis flags `Environment(...)`, `Environment.Value` and
  `Environment.LoadFromFile` usage; ALM project analysis does not. Search for
  them before you convert — for scripts on disk, for example
  `Get-ChildItem -Recurse -Include Script.mts,*.qfl,*.vbs | Select-String
  -Pattern 'Environment\s*(\(|\.Value|\.LoadFromFile)'`; for ALM tests, search
  the test and library scripts in UFT or ALM — then re-create the variables on
  the converted test or move them into the DataTable.
- **An externally linked Data Table is not carried.** Only a `Default.xls` /
  `.xlsx` sitting at the test root is copied. A test pointed at a Data Table
  elsewhere (*Settings → Resources → Data Table*) comes out on the rebuilt
  test's own workbook, silently losing its data source.
- **Run-logic and configuration profiles (`default.usp`, `default.cfg`) are not
  carried.** They are generated by the AOM for the rebuilt flow. The run *order*
  survives because Action0's script is re-emitted with its `RunAction` calls,
  and on the ALM path the six `Settings.Run` fields above are re-applied — but
  anything else those profiles held (additional Vuser profiles, per-action
  run-logic customisation) is not. Every test in the reference estate shared
  one identical `default.usp`, so that validation could not have detected this
  and did not.
- **Action descriptions are not carried.** Each rebuilt action is authored with
  an empty description.
- **Recovery scenarios are not carried.** *[6 of 116]* UFT 26.1 does **not**
  support recovery scenarios for Python tests at all, so there is nothing to
  carry them into. UFT 26.3 adds support but requires them re-authored as
  Python (`.prs`), a different file format from the VBScript `.qrs` the source
  references — so this is not a gap Phoenix can close on 26.1 at any effort.
  **Any test relying on a recovery scenario to survive an unexpected dialog,
  crash or session state will behave differently after conversion**: the
  recovery never fires. Identify these before you convert — neither analysis
  path is a reliable detector. ALM project analysis records a test's linked
  recovery scenarios only as a per-asset note (`Linked ALM Test Resources: …
  Recovery scenario`) in `alm_analysis_results.json`; it raises no finding, does
  not show in the HTML reports and does not affect the verdict. The local
  filesystem scan counts the `.qrs` files it finds under the source roots, but
  warns only when a single script line both names a `.qrs` file and contains
  the word *recovery*, and a scenario associated in Test Settings is never
  named in script text. Check *File → Settings → Recovery* in UFT, or the
  test's Test Resources in ALM, and either re-author the scenarios in 26.3 or
  handle the condition in the script.
- **Analog recording tracks (`AnalogTrackList.dat`) are not carried.**
  *[2 of 116, both inert]* Analog replay records literal mouse paths and
  keystroke timing; it has no Python equivalent. **A test that genuinely calls
  `RunAnalog` still converts, with no blocker and no finding that names it, but
  the analog track it replays is not carried, so those steps cannot replay.**
  Re-author them as ordinary object steps. In the reference estate both affected
  tests carried the file without ever invoking analog replay, so nothing was
  lost there — do not read that as the general case. Search your estate for
  `RunAnalog` before converting.
- **Debug watch expressions (`Watches.xml`) are not carried.** *[12 of 116]*
  IDE-only debugging aids saved with the test; they have no effect on
  execution. Re-add them in UFT if you want them. No action required.
- **Record-and-Run / launcher settings are not round-tripped.** *[all tests]*
  The test's Record and Run Settings — which browser or application UFT
  launches — are left at the converted test's defaults rather than copied.
  This is deliberate: the AOM exposes a writable `Browser` on the Web launcher
  but no consistent `Active` flag across launcher types, so copying the
  source's values can make UFT launch the *wrong* application. **A test that
  depends on Record and Run Settings to start its AUT will not start it after
  conversion.** Set Record and Run Settings on the converted test, or drive
  launch from the script with `SystemUtil.Run` — which is what the reference
  estate does throughout.

### Known defect (ALM path): a shared object repository can be dropped on a caller test

**Status: open, disclosed at conversion time, not yet root-caused.** This
concerns ALM project conversion, the only path that re-applies shared
repositories at all; a local filesystem conversion drops every one of them, as
the list above says.

A test that both (a) calls another test's reusable actions and (b) associates a
**shared object repository** (`.tsr`) may lose that association during
conversion. Measured across the reference estate: 17 tests carried a shared
repository, 16 kept it, and the one that lost it was the only test that was
*both* a cross-test caller and a repository owner. Tests that are one or the
other are unaffected.

The consequence is severe where it happens: every object that resolves through
the repository becomes unresolvable, and the test fails with
`Cannot find the "<object>" object's parent`. It is also the combination most
likely to occur in a mature estate, where shared repositories and
reusable-action chains are both common.

ALM project conversion **reports** this per asset rather than dropping it
silently — look for `[warning] shared object repository NOT carried into the
rebuilt test: <repository>` in the conversion notes.

**Do not check for this in ALM — it will lie to you.** The ALM *asset relation*
between the test and the `.tsr` resource **survives** even when the action-level
association is lost, so the repository still shows as a linked resource on the
test while no action actually uses it. UFT resolves objects through the
per-action association stored in `Action<N>/Resource.mtr`, not through the ALM
relation. Verified on the affected test: the ALM relation to the repository was
intact, and the live action carried no association at all. The only reliable
checks are the conversion warning above, or running the test.

**Until it is fixed:** after an ALM project conversion, check the notes for that
warning and re-associate the repository on the affected test in UFT
(*Resources → Associate Repositories*). Note that **re-running the conversion
does not repair an already-affected test** — the converter faithfully carries
what the source has, the harvest reads the live action, and the association is
already gone from it. Restore the affected test from a pre-conversion snapshot
first, or re-associate by hand.

Two further differences are expected and benign rather than limitations, but
are called out because a byte-level comparison of source against build will
surface them: each converted action receives a **new GUID, author and
timestamp** (it is a newly authored asset), and action **folder numbers may
shift** (a source `Action1` can land as `Action2`, because UFT's action-folder
allocator never reuses a number). Action *names* — which are what scripts and
cross-test references resolve by — are preserved exactly, as are the object
repositories and the DataTable. The run configuration and the shared-repository
associations are preserved on the ALM path only; on the filesystem path expect
them to differ, per the re-apply list above.

A third difference applies to the ALM path, looks alarming, and is not: the
converted test's `.usr` file lists **fewer add-ins** than the source's. That
section records which add-ins were *installed* when the test was saved, not
which the test is associated with, and it is typically identical across an
entire estate. Phoenix carries the associated set reported by
`GetAssociatedAddinsForTest`, which is the **minimal set the test actually
needs** — a test driving `Browser`/`Page` objects gets Web; one driving
`WpfWindow` gets WPF and UI Automation. This is
deliberate and load-bearing: an over-broad add-in set changes which class
claims a window, and has been measured to break object identification outright
(`WpfWindow` stops matching and every object beneath it fails). Compare
add-ins with `GetAssociatedAddinsForTest`, not with the `.usr`. A local
filesystem conversion carries no add-in set at all, so the built test keeps
whichever add-ins the UFT session had loaded — check and set them by hand.

## What the reference validation did and did not exercise

A clean conversion only proves the paths the source estate actually walked. The
reference estate (116 VBScript tests, 239 actions) did not exercise the features
below, or exercised only the narrow slice each row names, so while Phoenix has
unit coverage and, in several cases, explicit handling for them, they have not
been proven end-to-end on a real conversion. Treat any of these in your own
estate as **needing a pilot conversion and a run comparison before a production
wave** — convert a representative handful first rather than the whole project
blind:

| Not exercised | Why it matters |
| --- | --- |
| **Environment variables** (`Environment(...)`) and external environment XML files | Not merely untested — **not carried at all**; see the entry above. No test in the reference estate used them, so the gap was never exercised end-to-end either. |
| **Active Screen data** | Not carried and never exercised; Active-Screen-dependent maintenance workflows do not survive. |
| **Virtual objects** | No conversion path has been demonstrated. |
| **`LoadFunctionLibrary`** and **`ExecuteFile`** at run time | The *linked*-library path is well covered (39 tests); loading a library dynamically from script is not. Every `ExecuteFile` statement is refused on the ALM path; on the filesystem path its treatment follows the Strictness setting (see *Strictness on the local path*). |
| **Runtime `Recovery.*` API calls** | Distinct from recovery scenarios above; the runtime object is untested. |
| **WMI beyond `Win32_Process`** (`winmgmts:`) | Only `Win32_Process` ran end to end — enumeration (`InstancesOf`), a filtered `ExecQuery`, property reads, collection `.count` and `Terminate()`, in the reference estate's process-closing helper (see the process-scan note below). Other namespaces and classes have unit coverage only. |

**Checkpoints are the exception to read carefully.** They were exercised: the
reference estate's converted tests ran them, and its approved regression set
reported the same checkpoint count as its VBScript baseline. What is missing is
detection — ALM project analysis does not flag a checkpoint, an `OutputValue` or
a `GetROProperty`-family call at all, so find them yourself with the sweep above
and review every such line before you approve the run.

The constructs Phoenix is known **not** to detect before a filesystem
conversion — `GoTo`, `On Error GoTo <label>`, VBScript `Class` and
`Property Get/Let/Set` — also did not appear in the reference estate, and nor
did `Eval` inside an expression, which the filesystem scan does raise. The
pre-migration sweep above is the control for all four; run it.

## Function libraries (`.qfl` → `.pfl`, shared and linked)

A VBScript function library (`.qfl`) linked to a test is converted **once** to
a Python Function Library (`.pfl`, the Python analog of `.qfl`) and **linked**
to each converted test (UFT Settings → Resources → Libraries) — the same in
both conversion paths, differing only in where the shared `.pfl` lives:

- **ALM project conversion** — the `.pfl` is created as an ALM Test Resource of
  type "Function library" in the same Resources folder as the source `.qfl`
  (convert-in-place) and linked by its `[QC-RESOURCE]` path.
- **Local filesystem conversion** — the `.pfl` is written once to a shared
  `FunctionLibraries/` directory beside the converted tests and linked by its
  on-disk path. That path is stored **absolute**, and cross-test shareable
  action references are likewise rebuilt against the callee's **absolute**
  published action folder — so the converted tree is **not relocatable**: run it
  from the output root it was written to, or re-run the conversion with the
  final location as `--output-root`. Every such binding is listed in the
  "Portability Manifest" section of `convert_report.html`.
- **Libraries linked from outside the source roots are converted but not
  analysed.** Design-time library linkage lives in the binary `Test.tsp` and is
  readable only through the AOM, so the analysis (which reads the source roots
  from disk) cannot see it: a library a test links from a folder outside every
  source root gets no inventory entry, no planned-transformation row and no
  blocker assessment, while the conversion still converts and links it. Add the
  folder holding the linked libraries to the source roots and re-run the
  analysis to have them assessed. A linked library **missing** from disk blocks
  its own test at every strictness.
- **Keep shared libraries out of test folders under Convert Mode = in-place.**
  In-place publishing replaces each test directory; what happens to the original
  is the Overwrite Policy's decision. Under `backup` — which is also what the
  default `fail` becomes in in-place mode, since it would otherwise refuse every
  test — the directory is renamed to `<name>.bak`; under `overwrite` it is
  replaced outright. Either way every non-test file inside it goes with it,
  including a `.qfl` stored under the test folder. Phoenix links the
  already-converted `.pfl` it produced from that library so the other tests
  still convert, but the library is **not re-translated** on later runs (its
  source is gone), so a converter fix cannot reach it. Store shared libraries
  in a folder no test publishes over, or convert with Convert Mode = new.

At run time UFT loads the linked `.pfl` into every action's namespace, so its
functions resolve **directly, with no `import`**, and can use the UFT runtime
objects (`Reporter`, `SystemUtil`, …). Libraries are **linked, not inlined**:
the library is converted once and every referencing test links the same shared
`.pfl`, exactly like native UFT `.qfl` behavior. Library procedures are never
copied into each action's `Script.pts`.

### VBScript compatibility helpers live in `PhoenixVBRuntime.pfl`

Converted scripts need Python versions of VBScript built-ins (`Right`, `InStr`,
`CDate`, `Err`, `MsgBox`, …). Phoenix writes those helpers **once**, to a shared
function library named `PhoenixVBRuntime.pfl`, instead of pasting a copy into
every action and every converted library. Each script that uses them carries a
short generated block marked `# _phoenix_vb_runtime` that lists the helpers it
needs. The block sits at the top of the script, or directly after the
`# _phoenix_library_binding` block when the test links a function library.

- **Where it lives.** ALM project conversion: an ALM "Function library" resource
  in the Resources child folder `UFT Phoenix`, created by the first conversion
  that needs it, linked to every converted test whose scripts use it — or that
  calls an action whose scripts use it — and related to that test so Test Lab
  delivers it. Local filesystem conversion:
  `FunctionLibraries/PhoenixVBRuntime.pfl` beside the converted libraries,
  linked by absolute path and listed in the Portability Manifest.
- **What runs is unchanged.** The block installs the same helper text into the
  script's own namespace, in the same order, at the point where the pasted copy
  ran — after any linked function library — so a function in a customer library
  that shares a helper's name behaves exactly as before. A helper the converter
  altered inside a particular script stays pasted in that script.
- **The file only grows.** Each helper entry is named with a digest of its text,
  and conversion only ever adds entries. A test converted by an earlier Phoenix
  version keeps running the exact helper text it was converted with.
- **On the filesystem path, Overwrite Policy can stop it growing.** With
  Convert Mode `new` and Overwrite Policy `fail` (the default), the file is
  never rewritten. So if a later conversion into the same output root needs
  helper entries the existing `FunctionLibraries\PhoenixVBRuntime.pfl` lacks —
  typically after upgrading Phoenix — or finds one of its entries edited, each
  such test is blocked with *"shared function library … already exists with
  different content and overwrite policy is 'fail'"*. Use `backup` or
  `overwrite` for that run (existing entries are kept, so tests converted
  earlier are unaffected), or convert into a new output root.
- **Do not edit it.** A converted script runs whatever text the file holds
  under the names it lists, so an edit takes effect on the next run. The next
  conversion that writes the file checks every entry against its digest: an
  edited entry for a helper the current version still has is put back to its
  original text, and an edited entry for an older helper is dropped, after which
  scripts that name it stop with the error described in
  [troubleshooting.md](troubleshooting.md). ALM conversion reports such a
  rewrite as replaced content and keeps the prior copy; a filesystem conversion
  needs Overwrite Policy `backup` or `overwrite` to rewrite the file at all.
- **Analysis writes nothing.** Standard and deep analysis leave the helpers
  pasted in what they build, and create no library.
- **Report line counts still include the helpers.** "Python lines produced" and
  "Changed Lines" measure the converter's output, which is produced before the
  helpers move into the library.
- **Mixed estates are fine.** A script converted by a Phoenix build that
  predates `PhoenixVBRuntime.pfl` — recognisable by pasted helper definitions
  and no `# _phoenix_vb_runtime` block — keeps its pasted helpers until it is
  converted again; both forms run side by side.
- **A converted library already on the server keeps its pasted helpers.** If
  the existing copy of a converted function library still carries pasted
  helpers, tests outside the current conversion may load it without being
  related to `PhoenixVBRuntime.pfl`, so conversion rewrites it with its helpers
  pasted. Only a library that is new, or already uses the runtime library, is
  written without them. To remove the pasted helpers from such a library,
  delete its converted `.pfl` resource and convert the whole project again.
- **If the runtime library is unavailable, nothing breaks.** ALM conversion
  relates `PhoenixVBRuntime.pfl` to a test before any of its scripts depend on
  it. If the library cannot be written, read or related, that test keeps its
  helpers pasted and converts exactly as before, and the conversion notes say
  "helpers stay pasted". A test fails only when something it links is already
  compacted on the server and cannot fall back.

Measured on the reference estate: a whole-project conversion moved the helpers
of 45 tests into the runtime library and related it to 6 more that call actions
using it; all 51 were then run in Test Lab. None failed on the library or a
missing helper. The approved regression set of 81 tests, 31 of which use the
runtime library, passed with the same status and the same checkpoint count as
its VBScript baseline.

### Library links are fixed when a test is converted

Every converted action other than the main flow that uses a linked function
library starts with a generated block marked `# _phoenix_library_binding`,
which loads the library itself on every iteration (the reason is in
[supported_versions.md](supported_versions.md)). In an ALM conversion the main
flow instead gets a `# _phoenix_library_scope` block, which tells the actions
it runs which library to load.

Both blocks record the library **the test was linked to when it was
converted**: its ALM resource ID (for example `_phx_want = '<resource id>'`) and
its file name, or, for a filesystem conversion, its absolute path. The values
come from each test's own links — they are not built into Phoenix — but they are
written into the script as literals. **Nothing updates them when a library link
changes afterwards.**

Changing the *content* of the linked library is safe: its resource ID and path
stay the same, so the block loads the new content. Changing *which* library is
linked is not. The block keeps loading the originally linked library for as long
as a copy of it can be found — in an ALM run, in UFT's extraction cache on the
execution host (`%LOCALAPPDATA%\Temp\TD_80`); for a filesystem conversion, at
its original path. It loads that library after UFT has bound the new one, so
the old library's functions replace any with the same name. No step fails and
nothing is reported.

| After conversion, you… | The converted test… |
| --- | --- |
| edit or replace the content of the linked library | runs the new content. Not affected. |
| link a different library with the **same file name** (for example, a copy from another folder) | runs the **old** library if a copy of it is in the cache — left by an earlier run, or extracted in the same run for another test that still links it. If none is, it uses the new library when that is the only one of that name in the cache, and otherwise leaves the choice to UFT. |
| link a library with a **different file name**, or add a second library | does not load the new library itself, so it has the problem the block exists to fix: in a multi-test Test Lab session the new library's functions can be missing from the second iteration onward. If a copy of the old library is still found, that is loaded too and its same-named functions win. |
| remove the link | still loads the old library while a copy can be found, which hides the removal. |

For a filesystem conversion the rule is simpler: the old library is loaded
whenever its file still exists at the original path.

Relinking a test that calls other tests' actions changes those actions too:
when run from that test, they load the library its main flow names.

Editing the generated lines by hand does not fix this. An action's own
`_phx_want` is overridden by the ID the main flow publishes, and the next
conversion rewrites both blocks.

**Workaround:**

1. **Change library content, not links, where you can.** To give converted
   tests different library code, update the library they already link: upload
   new content into the same ALM Function library resource, or overwrite the
   same `.pfl` on disk. Leave the `_phoenix_lib_marker__…` function at the end
   of the library in place; the block uses it to recognise the right library
   when it has to search by file name.
2. **If a link must change, convert again afterwards.** Conversion removes both
   generated blocks and writes them again from the test's links at that moment.
   - **ALM:** Phoenix reads a test's links from its ALM resource relations (the
     Test Resources the test uses). Before you convert, check in ALM that the
     relation names the new library.
   - **ALM:** conversion is whole-project and needs a current analysis in the
     same run folder, so choose a **new run ID** and run the analysis under it
     first, then convert. In the GUI, change **Analysis Run ID** on Step 5 — it
     defaults to `<Domain>-<Project>`, the same value on every run; on the CLI,
     pass `--run-id`. A conversion under an earlier run's ID resumes that run
     and skips every test it already converted that is still Python on the
     server, including the test you relinked, and re-running the analysis under
     that same ID does not clear the record.
   - **ALM, if a resumed run stops on a cross-test reference:** a test carried
     forward from an interrupted run still serves as a callee, so its callers
     convert as usual. The exception is a run folder whose journal an earlier
     version of Phoenix wrote, before the converted action layout was recorded:
     a caller of a test carried forward from it is blocked with *"cross-test
     reference … that callee has no conversion record in this run"*, and the
     callee's entry in `alm_aom_results.json` shows `resumed: true` and a note
     that its journal record carries no conversion maps. Re-running the
     conversion in that run folder cannot get past it and re-running Analysis
     there does not help; start over under a new run ID as above. The same
     message also appears when a callee failed or was not converted in the run;
     see [troubleshooting.md](troubleshooting.md). Keep the old run folder — the
     snapshots in its `alm_aom_work\alm_rollback` directory are the only
     pre-conversion originals of the tests converted before the interruption.
   - **Filesystem:** convert the test again; its links are read through UFT.
3. **Clear the cache on every execution host before the next run**, using the
   command in [advanced_troubleshooting.md](advanced_troubleshooting.md) §1c, so
   no old copy is left to find. On its own this is not enough if another test in
   the same run still links the old library, because UFT extracts it again for
   that test.

## ALM environment boundaries

- **Copy/paste-derived tests** are refused (`shared-assets`): ALM clipboard
  copies share the source test's asset ownership and cannot be converted in
  place. See [advanced_troubleshooting.md](advanced_troubleshooting.md) §1a.
- **Libraries attached only through Test Settings** (no ALM resource link)
  with bare function calls are **not detectable** — verify library linkage
  in ALM before migrating.
- OTA entity contracts vary by ALM deployment and patch level; site-specific
  behaviors encountered so far are catalogued in
  [advanced_troubleshooting.md](advanced_troubleshooting.md) §6.
- UFT **API/Service tests** (C#-based) are inventoried and skipped;
  conversion coverage is GUI/script assets.

## Asset locks

A lock never fails a conversion — **locked assets are converted and
overwritten**, and there is no `locked` failure status on the conversion
path. This is safe because an ALM lock does not block
`ExtendedStorage.Save`, the write that carries a test's payload
(`Script.pts`, `Test.tsp`, the `.usr`); it blocks only entity *metadata*
writes (`SetField`/`Post`), which the upload path already treats as
optional. Per asset the pipeline allows a 10-second grace period for the
lock to clear on its own, attempts to release it, then converts either way.
It has to: a whole-project ALM conversion is all-or-nothing, and a run that
dies partway leaves the project half Python and half VBScript, breaking
cross-test action chains and poisoning every later conversion.

The limitation is in the *release*, not the conversion. `UnLockObject()`
releases only your own lock — against another session's it returns cleanly
and silently does nothing, so the pipeline never trusts it and always
re-probes. Revoking a foreign lock means deleting its row from the
project's `LOCKS` table through the OTA `Command` object, which ALM
**disables by default** — most customers will not have it. Where it is
unavailable the conversion still completes and overwrites. The run records
`entity-lock-force-revoked` (revoked) or `entity-lock-not-cleared-proceeding`
(overwrote anyway), and each affected asset carries a note naming the holder.
The machine, ALM session id, lock time and last-active time appear only where
the `LOCKS` table is readable through the OTA `Command` object — the same
surface the revoke needs; without it the note names the user alone.

Overwriting takes the work of anyone still editing a locked asset, and
their ALM client may hold a stale copy afterwards — run conversions in an
agreed window with the project empty. See [alm_safety.md](alm_safety.md)
§ *The safety model*, item 9 (locks), for the full policy.

## Scanner risk flags (review, not blockers)

**Local filesystem analysis only.** Its scan flags elevated-risk feature areas
for human review: Keyword View dependencies, Active Screen dependencies,
recovery scenarios, Business Process Testing indicators, and interactive input
methods. These are warnings; they do not change the verdict. ALM project
analysis raises none of them, and the recovery flag in particular fires only
when a script line names a `.qrs` file and contains the word *recovery* — see
the recovery entry above.

## Supported Windows COM and WMI patterns

`CreateObject`/`GetObject` convert through a case-insensitive COM dispatch
wrapper. Validated patterns:

- `GetObject("winmgmts:")`, `InstancesOf("Win32_Process")`,
  `ExecQuery(...)`, `For Each` over WMI collections, `Process.Name`,
  `Process.ProcessId`, collection `.count`, `objProcess.Terminate()`
- `StrComp(left, right, vbBinaryCompare|vbTextCompare)`

More complex WMI namespaces or broader COM object models should be reviewed
during sign-off.

## FileSystemObject coverage and restrictions

`CreateObject("Scripting.FileSystemObject")` converts to a COM-backed
Python equivalent. The converter handles the FileSystemObject and TextStream
members explicitly, including `OpenTextFile`, `CreateTextFile`,
`OpenAsTextStream`, `Read`, `ReadAll`, `ReadLine`, `Skip`, `SkipLine`, `Write`,
`WriteLine`, `WriteBlankLines`, `Close`, `FileExists`, `FolderExists`,
`CreateFolder`, `DeleteFile`, `DeleteFolder`, `CopyFile`, `CopyFolder`,
`MoveFile`, `MoveFolder`, `GetFile`, `GetFolder`, `GetSpecialFolder`,
`BuildPath`, `GetTempName` and `GetAbsolutePathName`.

Restrictions:
- Local Windows filesystem semantics are assumed; UNC, locked-file, and
  permission-sensitive flows need runtime validation.
- Encoding, sharing, and line-ending behavior should be validated for
  scripts depending on non-default text handling.
- The property-heavy object graphs `GetFile`/`GetFolder` return, binary
  workflows, stream seeking, and ADODB-based file handling remain outside the
  qualified path: they convert, but no run has validated them.

## OptionalStep handling

`OptionalStep.<object>.<action>` converts to an existence guard around the
action — `if <object>.exist(): <action>` — with an `else` branch that reports
*"Optional step skipped"* as an informational (`micDone`) node, so a skipped
optional step still leaves evidence in the run report.

`exist()` is called **with no argument**, which waits the test's object
synchronization timeout — the same wait VBScript's `OptionalStep` performs.
This matters: an optional step is commonly used to dismiss a dialog or click a
control that takes a moment to render, and the step is meant to *run* if the
object turns up inside that window. An instantaneous `exist(0)` probe would
skip it and still pass, turning a wait-then-act step into a silent no-op.
Earlier Phoenix builds emitted `exist(0)`, and a test converted by one of them
keeps it: re-converting a test preserves an action that is already Python as it
stands. To find them, search converted action scripts for `.exist(0):` followed
by an `else` branch that reports *"Optional step skipped"*. To fix one, change
`.exist(0)` to `.exist()` in the script, or restore the test to VBScript
(`uft-migrate restore`, see [alm_safety.md](alm_safety.md)) and convert it
again; a filesystem conversion can simply be run again from the VBScript source.
In the reference estate the affected tests finished in 1–9 s against 22–26 s
under VBScript, the difference being exactly the wait that had been dropped.

## Runtime parity

- **Local UFT execution is not a Phoenix feature.** `--run-uft` was removed
  when the AOM conversion path became canonical. The flag is still accepted
  purely so it can be refused by name — it fails the command (exit 2) rather
  than silently running nothing. To check a converted test locally, open it
  in UFT One and run it by hand.
- ALM Test Lab execution (CLI-only support tooling, `--run-via-alm`; the GUI
  never runs Test Lab) requires an **active interactive desktop session** on the
  execution host (GUI identification fails on locked/disconnected sessions) and
  report artifacts can vary by ALM/UFT patch level.
- A "Passed" Test Lab run whose report is missing expected actions is
  flagged `incomplete-execution` rather than trusted.

### Conversion can surface object-identification failures your baseline hid

**This is the one result most likely to be mistaken for a regression, so read
it before you compare a converted run against its baseline.**

A test whose object descriptors no longer match the application can *pass*
under VBScript and *fail* after conversion, having changed in no other way.
The failure is not introduced by the conversion — it was already there, graded
as a warning.

Measured on the reference estate, three tests failed after conversion against an
84/84 VBScript baseline. Their baseline runs look like this next to their
passing near-duplicates:

| | Duration | Final step | Graded |
| --- | --- | --- | --- |
| the three affected tests | **24–27 s** | `Replay Warning` | Passed |
| their passing twins | **2–4 s** | `Verification` | Passed |

24–27 seconds is the **object sync timeout** (`ObjectSyncTimeOut`, 20,000 ms
by default) plus overhead. Those runs sat waiting for an object they could not
find, gave up, logged a **Replay Warning** — and UFT still graded the run
**Passed**. After conversion the same condition is booked as a **Replay
Error**, which fails the run. The underlying cause was stale identification
data: the tests carried vendor-era window titles that no longer match the
installed application.

**How to find these before you convert.** In your baseline results, look for
runs whose duration is at or just above your object sync timeout and whose
step list ends in a `Replay Warning` on a step that is **not** an
`OptionalStep`, with no checkpoint or verification step. A test that genuinely
exercises its application finishes far faster and books a real verification.
Fix the descriptors first and your baseline becomes a true baseline.

**Do not over-read this.** It is not a general rule that the Python engine is
stricter. Other tests in the same estate logged a `Replay Warning` at a similar
duration under VBScript and still passed after conversion. Those warnings came
from `OptionalStep` lines: under VBScript a skipped optional step is recorded as
a `Replay Warning` after the sync timeout has been waited out, which is intended
behaviour (see *OptionalStep handling* above). The tests that failed logged
their `Replay Warning` on a mandatory step. The grading difference itself is UFT
engine behaviour that Phoenix does not control; what is actionable is the
detection method above.

### A source helper that scans every process runs slower after conversion

A VBScript helper that walks the **whole** process table — a "close process by
name" helper that calls
`GetObject("winmgmts:").InstancesOf("Win32_Process")` and reads `.Name` on every
returned object — adds seconds to every call once converted. Nothing fails and
no step result changes; the run is simply slower.

Measured on the reference estate, the same 84 tests on the same host, VBScript
baseline against the converted estate: the six tests that call such a helper
once or twice each ran **6–15 s slower per run** (+15 s, +12 s, +10 s, +8 s,
+7 s, +6 s), roughly 4–12 s per call, where their whole VBScript runs took
1–8 s. The added time sits between the run's `Start Action` node and its first
reported step, and the cost grows with the number of processes on the machine.

Two controls locate the cost in the loop rather than anywhere else: tests that
**link** the same function library but never call the helper showed no change
(so it is not library loading), and tests calling a sibling copy of the helper
that asks WMI for the process **by name** —
`ExecQuery("Select ... from Win32_Process where Name = '<exe>'")` — showed no
change either. The cost therefore sits in the enumeration: one property read
across a COM boundary for every process on the machine.

The conversion is faithful: it carries whichever form the source library has.
If the run time matters, change the **source** helper to the filtered query
before converting, and the cost disappears.

## Version-controlled ALM projects

Version-control support is **implemented** and needs no configuration:
versioning is detected automatically per asset; a pre-existing
checkout — another user's, or a stale one of ours — is undone first,
reverting the server working copy to the latest checked-in version (which is
what gets converted); check-in happens **only after post-upload verification
passes**; any failure after check-out abandons the checkout so the server
keeps its last checked-in version; and Python function-library resources
(`.pfl`) are checked out and checked in too, though each is checked in as
soon as its content lands — before the test's own verification — so a
failed test or an abort rollback does not revert a replaced library (its
previous version stays in ALM version history). Undoing another user's
checkout requires the connected ALM user to hold the "Manage
checkouts"-equivalent permission — without it the asset fails as "Version
control blocked" (`vc-blocked`).

The basic path — check out, convert, verify, check in as a new version — has
been run against a live version-enabled project, for tests without linked
function libraries. Undoing another user's checkout, the missing-permission
`vc-blocked` failure, abandon-on-failure, and check-out/check-in of function
library (`.pfl`) resources including `PhoenixVBRuntime.pfl` have unit coverage
only. Validate them on a **copy** of a version-enabled project before a
production wave.
