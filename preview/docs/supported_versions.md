# Supported Versions and Conversion Coverage

## Platform matrix

| Component | Supported | Notes |
| --- | --- | --- |
| Windows | 10 / 11, Server 2019+ | Windows-native tool; COM automation requires Windows |
| Python (tool host) | **3.14.0, 32-bit**, sealed inside the offline package | No Python install of your own is needed. A source install needs 32-bit Python 3.11 or newer; only 3.14.0 is validated. `uft-migrate doctor` hard-fails a 64-bit interpreter, because ALM OTA and UFT AOM are 32-bit COM servers |
| UFT One | **26.1** (validated) | Python test support must be installed; earlier UFT versions cannot execute Python tests. `doctor` checks that UFT is registered, not which version it is |
| UFT IronPython runtime | IronPython 3.4.1, IronPython.StdLib 3.4.1 and DynamicLanguageRuntime 1.3.4 | `doctor` checks for `IronPython.Modules.dll`, `Microsoft.Scripting.Metadata.dll` and the `Lib\` standard library beside `IronPython.dll`; it checks no versions. A missing `IronPython.dll` is a warning, a missing sibling file or a missing `Lib\` folder a failure — see [troubleshooting.md](troubleshooting.md) for repair steps |
| OpenText Application Quality Management | 24.1, 25.1 and 26.1, through the OTA client | Formerly Application Lifecycle Management; the short form **ALM** continues throughout this documentation, the command-line options and the run folder. Older versions are not supported — backward compatibility may still carry one, so validate on a copied project before a production wave. The ALM Client must be registered on the tool host; `doctor` reports a missing ALM client as a warning, not a failure, and looks only for the OTA ProgID `TDApiOle80.TDConnection` — nothing in the tool reads the server's version |
| ALM version control | Version-enabled projects handled automatically | Per-asset check-out/check-in, no configuration: pre-existing checkouts are undone first, check-in happens only after post-upload verification, and every conversion creates a new version (the prior version stays in ALM version history). Check out → convert → verify → check in has run against a live version-enabled project. Undoing a *foreign* checkout, a missing-permission `vc-blocked`, abandoning a checkout after a failure, and version control over the converted `.pfl` resources have not — validate those on a copy before a production wave |
| Source tests | UFT/QTP 11+ GUI tests (VBScript) | Only QuickTest GUI tests are in scope (ALM test type `QUICKTEST_TEST`). UFT **API/Service tests** (C#-based) and every other ALM test type — manual, business-process and the rest — are dropped from scope automatically and are never counted as failures |

## VBScript conversion coverage

Converted deterministically, with compatibility helpers installed from the
shared library `PhoenixVBRuntime.pfl` where needed:

- **Control flow**: If/ElseIf/Else, Select Case (single values,
  comma-separated value lists, Case Else — dispatch applies VBScript's
  string/number comparison coercion, so a string subject still matches a
  numeric `Case`), For/For Each (incl. Step), Do While/Until,
  Loop While/Until, While…Wend, Exit Function/Sub, and Exit For/Exit Do when
  the *innermost* enclosing loop is of the matching kind (see blockers below)
- **Procedures**: Sub/Function (with or without parentheses), Optional
  parameters and defaults, return-via-function-name; a procedure that writes
  one of its own parameters (an out-parameter — ByRef is VBScript's default, so
  the keyword is usually absent) converts with a per-site warning naming the
  parameters, because the write does NOT propagate to the caller in Python
- **With blocks**: expanded onto a bound target variable, nesting supported
- **Error handling**: On Error Resume Next / GoTo 0 with per-statement guards
  and a faithful `Err` object (Number/Description/Source/Clear/Raise)
- **Operators**: `^`, `\`, `Mod`, `&`, `<>`, `Is`, And/Or/Not/Xor (Xor exact,
  integers included); Eqv/Imp with boolean semantics (warning emitted; mixing
  either with a top-level `&` is refused — see blockers below)
- **Intrinsic functions** (~70): string (Left, Right, Mid, Len, Trim/LTrim/
  RTrim, UCase, LCase, Replace, Split, Join, InStr, InStrRev, StrReverse,
  String, Space, Chr, Asc, StrComp), conversion (CInt, CLng, CDbl, CSng, CStr,
  CBool, CByte, CCur, CDate, Hex, Oct), type checks (IsEmpty, IsNull,
  IsNumeric, IsObject, IsArray, IsDate, TypeName, VarType — approximated, see
  below), date/time (Now, Date, Time, Timer, DateAdd, DateDiff, DatePart,
  DateSerial, TimeSerial, Year…Second, Weekday, WeekdayName, MonthName,
  FormatDateTime), math (Abs, Int, Fix, Rnd, Randomize, Round, Sgn, Sqr),
  arrays and misc (Array, Filter, UBound, LBound, ReDim [Preserve],
  FormatNumber, FormatCurrency, FormatPercent)
- **COM**: CreateObject/GetObject via a case-insensitive dispatch wrapper;
  FileSystemObject and TextStream convert through the same wrapper, with the
  restrictions listed in [limitations.md](limitations.md) (note that
  `Scripting.Dictionary` and `RegExp` still raise error-severity findings in
  the **filesystem scan** — see the scan errors below; whole-ALM-project
  analysis does not flag them)
- **UFT API**: Reporter, DataTable, Parameter, test-object chains, descriptive
  programming, ExitAction/ExitTest family, OptionalStep, wait/sync patterns

  `OptionalStep.<object>.<action>` converts to an `exist()` existence guard
  around the step. `exist()` is called with **no argument**, so it waits the
  test's object synchronization timeout and runs the step if the object
  appears — the same wait VBScript's `OptionalStep` performs. If a converted
  test still calls `exist(0)`, it probes without waiting and skips any control
  that takes a moment to render: change the call to `exist()`, or restore the
  test to VBScript and convert it again; [limitations.md](limitations.md) has
  the steps. Its skip branch also writes a run-report node —
  `Reporter.ReportEvent(micDone, "Optional step skipped", "Object not present,
  step skipped: <object chain>")`, with `micDone` emitted by name rather than
  as a literal. This is a **declared divergence** from the VBScript baseline:
  the VBScript engine's own skipped-step node ("Replay Warning") renders with
  status "Passed", whereas the converted node renders "Done", so a converted
  run diffed against the VBScript baseline shows a one-status difference per
  skipped optional step. Both statuses are non-failing and the behavior is
  identical — only the report text differs, and no per-file converter warning
  is raised.

### Known semantic approximations (converted with warnings)

- `Empty`, `Null`, and `Nothing` all convert to Python `None`; code that
  distinguishes them (`IsEmpty` vs `IsNull` vs `TypeName`) is approximate and
  flagged per file.
- `Eqv`/`Imp` convert with boolean semantics — exact when the operands are
  conditions, approximate on integers (VBScript is bitwise there), which is
  what the per-file warning flags. An expression that mixes either with a
  top-level `&` is not approximated but refused (see blockers below). `Xor`
  converts exactly and needs no review.
- Out-parameters do not propagate reassignment — whether or not `ByRef` was
  spelled, since ByRef is VBScript's default and the keyword is almost never
  written. The warning keys off the *write*, not the keyword: every procedure
  that assigns one of its own parameters is flagged per site and by name. An
  explicit `ByVal` parameter and an element write into an array parameter
  (`arr(0) = x`) are correctly not flagged by that warning — neither loses
  anything. (The scanner's separate `ByRef`/`ByVal` *keyword* detector is a
  different thing: it fires on the literal keyword and raises an
  error-severity finding in the filesystem scan — see the scan errors below.)

### Carried automatically by both conversion paths

- **Action parameters**: definitions (name, type, direction, default) are
  harvested from the legacy test via UFT and authored onto the AOM-built test.
  The main flow (Action0) is not exposed in `Test.Actions`, so it has no
  action-level definitions of its own; instead TEST-level parameter definitions
  (File → Settings → Parameters) are harvested via `Test.ParameterDefinitions`
  and re-authored on the converted test, and main-flow `Parameter()` references
  resolve against them. Their *default* values are carried; test-set runtime
  overrides do not propagate through the AOM main-flow indirection. In an
  action that has **no** action-level definitions of its own — the main flow
  always, a sub-action when the harvest found none for it — a `Parameter()`
  name absent from the test-level definitions fails closed as a blocker. An
  action that does have harvested definitions of its own is not name-checked.
  That per-action check runs in a Deep analysis or a real conversion, not in a
  Standard ALM analysis.
- **Function libraries** (`.qfl`): converted **once** to a Python Function
  Library (`.pfl`, the Python analog of `.qfl`) and **linked** to each
  converted test (UFT Settings → Resources → Libraries). On the ALM path the
  library is a linked ALM Test Resource: it is downloaded, converted and
  uploaded as a shared ALM "Function library" resource in the source library's
  Resources folder (convert-in-place). On the filesystem path each `.qfl` (or
  `.vbs`) in the test's library list is converted to a `.pfl` in a shared
  library folder beside the converted tests and linked by absolute path.
  Either way libraries are shared by reference — converted once and linked,
  not inlined into actions.

  The link alone does not make the functions resolve at run time. Under the
  ALM Test Lab scheduler, in a warm (multi-test) session UFT's Python engine
  loses every linked-library function from a non-flow action's namespace from
  global iteration 2 onward, and
  `LoadFunctionLibrary("[QC-RESOURCE];;…")` returns success without injecting
  anything. (VBScript is unaffected — UFT binds it from the folder-scoped ALM
  link.) So every non-flow action of a library-linked test opens with a
  generated **library-binding prelude**, one load block per linked library: it
  locates the `.pfl` — in an ALM run, in UFT's extraction cache under
  `%LOCALAPPDATA%\Temp\TD_80\*\*\resources\<resource id>\<file>`; in a local
  run, at its absolute path — and `exec()`s it into the action's `globals()`
  on entry, unconditionally, on every iteration, with no probe. Functions are
  therefore callable directly with **no `import`**. `exec` into `globals()` is
  last-writer-wins, so the binding is correct regardless of what the engine
  bound or what a previous test left resident; the cost is one compile+exec of
  each linked library's converted text per such action per iteration, so it
  grows with the size and number of your linked libraries. The main flow
  (Action0) gets no prelude — a library function called directly from the
  converted main flow is therefore not self-healed. On the ALM path it instead
  publishes a library-scope key *before* the flow body, so an action called
  from another test binds the **calling** test's library — UFT scopes
  libraries per calling test, not per owning test.

  Libraries are identified by **ALM resource id**, never by file name alone:
  the prelude loads the copy UFT extracted under `resources\<resource id>`.
  Only if that copy is missing does it search by file name, and it then
  accepts a candidate only when it is the single file of that name or when it
  carries that library's own generated marker function (whose name is keyed on
  the resource's parent folder and file name). A local conversion has no
  resource id and loads the library from its absolute path.

  Loader lines are **not** rewritten or removed. An `ExecuteFile` statement is
  a fail-closed blocker whether or not the library is linked (see below), and
  `LoadFunctionLibrary` receives no special handling at all — it converts as
  an ordinary call and loads nothing. Delete both loader forms from the source
  before converting; the linked `.pfl` needs no loader line.
- **VBScript compatibility helpers** (`Right`, `InStr`, `CDate`, `Err`,
  `MsgBox`, …) are installed at run time from one shared function library,
  `PhoenixVBRuntime.pfl`, rather than pasted into each action. Each converted
  action that uses them opens with a generated `# _phoenix_vb_runtime` block,
  placed after the library-binding prelude. The block finds the library — at its
  absolute path in a local conversion, and in an ALM run in the extraction
  cache under `%LOCALAPPDATA%\Temp\TD_80\*\*\resources\*\PhoenixVBRuntime.pfl` —
  and installs the helpers it names into the action's `globals()` on every
  entry. The helpers are cached for the whole UFT process, so the file is read
  again only when a later script names a helper the cache lacks; copies are
  then tried in turn and their entries merged until every helper that script
  names is present. Each entry is named by a digest of its own text, so any
  unmodified copy that carries an entry carries the same code. If no copy
  supplies every named helper, the action stops with `RuntimeError:
  PhoenixVBRuntime.pfl file not found, or it does not contain the helpers this
  script needs: …`. A test that cannot reach the library at all keeps its
  helpers pasted into each action instead. See [limitations.md](limitations.md)
  for where the file lives and how it is versioned.

### Not converted (fail-closed blockers)

- `Execute` / `Eval` / `ExecuteGlobal` used as a **statement** (dynamic code),
  with or without parentheses, and with or without a `Call` prefix —
  `Call Execute(…)`, `Call Eval(…)` and `Call ExecuteGlobal(…)` are refused
  the same way. `ExecuteGlobal` is classified exactly like `Execute`. The one
  form that escapes is `Eval` inside an expression (`x = Eval(…)`), which the
  converter reads as an ordinary function call — see the scan errors below.
- `ExecuteFile` — **any** use, whether or not the library is linked. The
  statement itself fails closed; linking the library does not clear it. Link
  the library to the test (an ALM Test Resource for ALM conversion, the test's
  library list for local conversion) so it is converted once to a `.pfl` and
  linked automatically, then delete the `ExecuteFile` line from the script.
- `Exit For` / `Exit Do` whose **innermost** enclosing loop is of a different
  kind — `Exit For` inside a `Do` or `While…Wend`, `Exit Do` inside a
  `For`/`For Each` or `While…Wend` — or which sits outside any loop. VBScript
  leaves the innermost loop *of the matching kind*, but Python's bare `break`
  always leaves the innermost loop of any kind, so rather than emit a
  mis-aimed `break` (silently wrong results, or a `Do` that never terminates)
  the converter fails closed. Refactor the loop nesting — for example hoist
  the exit into a flag the outer loop tests — before converting. `While…Wend`
  is its own kind: neither `Exit For` nor `Exit Do` may target it. An
  `Exit For` inside a `For` that is itself nested in a `Do` still converts
  normally; only the innermost enclosing loop matters.
- An expression that mixes a top-level `Eqv`/`Imp` with a top-level `&` — for
  example `a Eqv b = "x" & y`. VBScript binds `Eqv`/`Imp` looser than both the
  comparison and the concatenation, and every grouping the converter could
  emit is valid Python that means something else, so it fails closed instead.
  Add explicit parentheses in the VBScript source.
- A variable, procedure or parameter named `None`, in any letter case.
  VBScript allows the name, but spelled exactly it cannot be bound in Python
  at all, and no casing of it can be renamed safely — the rename is
  case-insensitive and would rewrite the `None` literals the converter emits
  for Nothing/Empty/Null — so the converter refuses every casing. Rename it in
  the VBScript source. (`True` and `False` are reserved words in VBScript, so
  they cannot occur as names.)
- VBScript date/time literals (`#1/1/2000#`, `#10:30:00 AM#`). The converter
  cannot translate the `#…#` token and, in every use measured, the output does
  not compile, so the conversion refuses the test — with the generic "not valid
  Python" blocker described below, which does not name the literal. Replace
  each one with `DateSerial(2000, 1, 1)`, `TimeSerial(10, 30, 0)` or
  `CDate("1/1/2000")` before converting.

These block an ALM upload unless explicitly overridden with
`--allow-blockers`, which drops the construct from the converted script — on
the ALM path it becomes a `# BLOCKED` comment — and publishes the test without
it, so that step no longer runs.

That dropping applies to the dynamic-code statements, `ExecuteFile` and the
cross-kind `Exit For`/`Exit Do` only. The `Eqv`/`Imp` regrouping and the
unbindable identifier are recorded after the line has already been converted,
so the override drops nothing there: it publishes the line exactly as
converted — an expression grouped differently from VBScript's own grouping, or
an identifier the converter could not rename, which can turn the `None` it
emits for Nothing/Empty/Null into a reference to your variable. The test then
runs and can give wrong results with no error. Correct those in the VBScript
source rather than overriding them.

The override cannot rescue a script that is not valid Python either: where the
blocked construct leaves the converted text unparseable — as every date-literal
form measured does, and as an identifier spelled exactly `None` does — the test
is refused whatever the flag says.

Of these, the filesystem scan reports only the first two
(`Execute`/`Eval`/`ExecuteGlobal` and `ExecuteFile`) and the date literal as
errors. The cross-kind `Exit For` / `Exit Do`, the `Eqv`/`Imp` regrouping and
the unbindable identifier are caught by the converter alone — the scanner
classifies `Exit For`/`Exit Do` as a review warning and does not classify the
other two at all.

Flagged as errors by the **filesystem scan** (`scan` or an `analyze` of a
local test tree, verdict `no-go`) but still converted, for manual porting. On
that path any hit lands in the report's blockers and forces
`go_no_go: no-go`. **Whole-ALM-project analysis and conversion do not run
these detectors**, so on the main ALM path these constructs neither block the
test nor change the verdict — the exceptions are `ExecuteFile` and statement
`ExecuteGlobal`, which the converter blocks as well. Sweep an ALM estate for
the rest by hand before converting (see [limitations.md](limitations.md)):

- Checkpoint/OutputValue objects
- `GetROProperty` / `GetTOProperty` / `SetTOProperty` property APIs (UFT
  Python API ambiguity)
- `.Object` native-object access
- `Scripting.Dictionary`
- `RegExp` (COM regular expressions)
- the literal `ByRef` / `ByVal` keywords in a signature (the keyword
  detector, distinct from the out-parameter warning above)
- `ExecuteFile` — every occurrence, including a library that *is* linked;
  this one is also a converter blocker, per the section above
- ALM/QC resource references (`[ALM]`, `td://`, `qc://`, `alm://`)
- descriptive-programming whitespace — misaimed. The pattern matches a
  backslash-`s` placed directly after `:=`, which is a regular-expression
  value such as `"text:=\s*Welcome"`, not literal whitespace. So
  `"name:= Submit"` is never flagged, while a descriptor whose value starts
  with `\s` raises a no-go error. The descriptor itself converts unchanged;
  review the flagged line, and rewrite the value (for example drop the leading
  `\s*`) if you need the scan verdict to clear.
- `Eval` inside an expression (`x = Eval("…")`) — raised by the dynamic-code
  detector. The converter emits a bare `Eval(...)` call that compiles and
  raises `NameError` at run time; port it to explicit dispatch before
  converting.
- `ExecuteGlobal` — also raised by the dynamic-code detector, and the converter
  blocks it too: as a statement, with or without parentheses and with or
  without a `Call` prefix, it is classified exactly like `Execute` and fails
  closed, per the section above. Replace it before converting; if it was
  loading a library, link that library to the test instead.

### Refused, but never named — remediate before converting

No detector classifies these, so a **filesystem scan** raises no blocker for
them and still reports `go_no_go: go` (at most a generic "implicit-call
syntax" warning that does not name the construct). The converter emits them
verbatim as Python that does not compile, and the syntax gate then refuses the
test with the generic blocker `converted output is not valid Python (line N of
the converted '<action>' script (from source line M): …) … This is a converter
defect — capture the VBScript source … and report it`. That refusal happens in
whole-ALM-project analysis (Standard and Deep both mark the asset `blocked`,
so the verdict is no-go) and in every ALM and filesystem conversion, and
`--allow-blockers` cannot override it. Because the blocker never names the
construct, check the source line it points to for one of these before
reporting a defect:

- `GoTo <label>`, including `If … Then GoTo <label>`
- `On Error GoTo <label>` (`On Error Resume Next` / `GoTo 0` are supported)
- VBScript classes (`Class` … `End Class`, `Property Get/Let/Set`)

Separately, and not a syntax failure: a library attached only through Test
Settings, called with bare function calls and with no ALM resource link, is
not converted or linked at all. Verify library linkage in ALM before
migrating.

See [limitations.md](limitations.md) for the pre-migration sweep that finds
these constructs in a source estate.
