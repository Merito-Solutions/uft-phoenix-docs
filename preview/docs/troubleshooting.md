# Troubleshooting Guide

Start every investigation with the environment check:

```
uft-migrate doctor
```

It verifies Windows, Python, pywin32, the UFT installation, the IronPython
runtime, the ALM client, and output-folder write access — and can test a live
ALM login with `--alm-url`/`--username` (password via the
`UFT_MIGRATE_ALM_PASSWORD` environment variable). An `offline-package` row
marked `[ -- ]` is normal on an installed copy: that check is for whoever builds
the package, not for you.

---

## Installation and environment

### "pywin32 import failed: No module named 'win32com'"
ALM and UFT automation require pywin32. What to do depends on how Phoenix was
installed.

**Installed with `MeritoUFTPhoenix-<version>-Setup.exe` (the recommended
install).** pywin32 is already present in the product's own runtime, and the
package build import-tests it before the package is sealed. If `doctor` still
reports this, that runtime is damaged: run the installer again, as
administrator, over the existing installation — it replaces the installed files
in place. Do not install packages into the product runtime — it carries no
`pip`.

**Installed from source with `pip`** (development only — see
[install.md](install.md) § *Installing from source*). Install pywin32 into the
same 32-bit Python that runs `uft-migrate`:

```
python -m pip install pywin32
```

If COM errors persist after installation, run the post-install script once from
an elevated prompt: `python Scripts\pywin32_postinstall.py -install` (from that
Python's installation folder).

### "QuickTest.Application COM ProgID is not registered"
UFT One is not installed (or its COM registration is broken) on this machine.
Install UFT One 26.1 or run a repair install. The converter's ALM pipeline
builds tests through UFT's Automation Object Model and cannot run without it.

### IronPython runtime incomplete
`doctor` reports missing files such as `IronPython.Modules.dll` or the `Lib\`
standard library next to `IronPython.dll` under the UFT installation. Converted
Python tests will import-fail at run time until these are present. Copy the
missing files from the NuGet packages **IronPython 3.4.1**, **IronPython.StdLib
3.4.1**, and **DynamicLanguageRuntime 1.3.4** into the folder that contains
`IronPython.dll`, then re-run `doctor`.

---

## ALM connection problems

### "ALM connection timed out" (GUI) or a hang on Connect
The ALM server did not answer within 45 seconds. Check:
- the URL form — `http://server:8099/qcbin`. Only the URL *path* is retried:
  Phoenix tries the URL exactly as typed, and if it carries no path it also
  tries `<scheme>://<host>[:port]/qcbin` and the trailing-slash form. The
  scheme and port are used exactly as you type them — if your server is HTTPS
  or on a different port, you must type that yourself,
- VPN/firewall path to the server,
- that the ALM site is actually up (open the URL in a browser).

### "Unable to create TDConnection COM object" when connecting
The ALM Client is not installed on this machine. Install it from your ALM
server's Tools page (ALM Client Launcher / Client Registration), then re-run
`uft-migrate doctor`. `doctor` reports the same condition as a warning,
"TDApiOle80.TDConnection COM ProgID is not registered".

### "The automation object disconnected mid-call"
UFT or the ALM client process crashed or was killed while Phoenix was talking
to it. Close stray `UFT.exe` processes (Task Manager) and re-run the command in
the same run folder.

- **Filesystem runs** resume with `--resume` under the same run id, but only
  while the interrupted run is still marked as running.
- **ALM conversions** do not use `--resume`, and it is refused with exit code 2
  after a run that ended in failure. Re-run with the same `--run-id` and no
  `--resume`: the conversion carries forward every asset an earlier run of that
  run id uploaded and verified, provided the server still holds their Python.
  A carried-forward test still serves as a callee, so a test that calls it is
  converted as usual. The exception is a run folder whose journal an earlier
  version of Phoenix wrote: see *"that callee has no conversion record in this
  run"* below.

During an ALM conversion Phoenix already retries this kind of fault up to twice
per asset, killing UFT between attempts — but only while that test's own
upload has not started, because a retry after a partial upload would re-run a
destructive write.

### The ALM session drops during a conversion
Before retrying an asset, Phoenix checks whether the ALM session is still alive.
If it is not, Phoenix reconnects and retries the asset, and `migration_log.txt`
records `alm-session-reconnect`. If the reconnect fails
(`alm-session-reconnect-failed`), or the test's upload had already started, the
run aborts — reconnecting first, so the rollback of this run's uploads can
still reach the server. Once ALM is reachable again, re-run the conversion with
the same run id and without `--resume`.

### Login succeeds but the domain list is empty
The account authenticated but has no domain visibility. Ask your ALM
administrator to grant the user access to the target domain/project — this is
an ALM permission, not a Phoenix problem.

---

## Conversion problems

### `Access to the path 'C:\Windows\SysWOW64\out\...' is denied` — the whole run fails
The conversion stops on the first test with an error like:

```
AOMError: AOM Test.SaveAs(C:\Windows\SysWOW64\out\<run id>\alm_aom_work\test_<id>_build\<test>) failed:
... 'OpenText Functional Testing', "Access to the path 'C:\Windows\SysWOW64\out\...' is denied"
```

and the Migration Console's failure dialog reads, for example, *"Conversion
failed: 116 of 116 assets did not convert."* followed by one line per status —
*"115 × not-attempted"* (with an example asset) and *"1 × aom-build-failed"*.
The executive summary says the same thing as *"116 of 116 ALM asset(s) did not
convert (115 x not-attempted, 1 x aom-build-failed)"*. ALM conversion is
all-or-nothing, so the first failure stops every remaining asset.

**Cause: Phoenix was launched from `C:\Windows\System32`.** Every run folder —
reports, logs, and the per-test build area `alm_aom_work` — is written to
`out\<run id>\` under **the directory Phoenix was launched from**. An
Administrator PowerShell or Command Prompt window opens in
`C:\Windows\System32`, and because Phoenix runs on 32-bit Python, Windows
redirects that folder to `C:\Windows\SysWOW64`. That location is protected, so
UFT cannot save the first rebuilt test there.

**The same failure, launched from the install folder.** `C:\Program Files
(x86)\Merito\UFT Phoenix` is no more writable than `System32`, so
double-clicking `bin\uft-migrate-gui.cmd` in Explorer produces the same denial
with the install folder in the path. Launch from the Start Menu shortcut or a
writable folder instead.

**Changing Output Root does not fix it.** Output Root only controls where
filesystem conversions write converted tests; the run folder always stays under
the launch directory (see [gui_field_guide.md](gui_field_guide.md)).

**Fix:** launch from the Start Menu shortcut (**Start Menu > Merito > Merito
UFT Phoenix**). It always starts in the profile folder of whoever launches it,
so it cannot hit this problem. If you launch from a console instead, change to
a writable folder *before* launching:

```powershell
cd $env:USERPROFILE
uft-migrate-gui
```

**A warning sign before you start a run:** the Migration Console remembers its
settings in `out\.uft-migrate-gui-cache.json` under the launch directory. If it
opens with your ALM URL, user name and other fields blank, it was launched from
a different directory than last time — close it and relaunch from the right
folder.

### A test converts cleanly but fails at first run in UFT
- **`NameError` on a VBScript function name** (for example `CInt`, `Left`,
  `Trim`): the test was converted with an earlier version of Phoenix.
  Re-convert with the current version, which supplies compatibility helpers for
  the VBScript intrinsic library.
- **`RuntimeError: PhoenixVBRuntime.pfl file not found, or it does not contain
  the helpers this script needs: …`**: the script installs its VBScript
  compatibility helpers from the shared library `PhoenixVBRuntime.pfl` and
  found no copy that has them. UFT reports the failure near the top of an
  action — or of a converted function library (`.pfl`) — inside the generated
  `# _phoenix_vb_runtime` block, which follows the library-binding prelude when
  the script has one, so expect a line number well past 1.
  - **ALM / Test Lab:** check that the test is still related to the resource
    `Resources\UFT Phoenix\PhoenixVBRuntime.pfl` (the test's Test Resources in
    ALM); the relation may have been removed since the conversion. Conversion
    relates the library *before* any script depends on it, so a test that was
    uploaded with this block was related when it was converted — if relating
    fails, Phoenix leaves that test's helpers pasted in the script (recorded as
    `helper runtime RELATION ERROR` in its conversion notes) or fails the asset
    before upload. Then clear `%LOCALAPPDATA%\Temp\TD_80` on the execution host
    in case an older copy is cached, and run again.
  - **Local filesystem:** the file must still be at the absolute path listed in
    the Portability Manifest (`FunctionLibraries\PhoenixVBRuntime.pfl` under the
    output root). If the converted tree was moved, re-run the conversion with
    the final location as the output root.
  - **After a hand edit and a later conversion:** a conversion rewrites the
    shared library only when it lacks a helper the test being converted needs.
    The rewrite keeps every entry you did not edit, but not your edits. An
    edited entry is put back as Phoenix wrote it when this version still ships
    that helper unchanged, and dropped when it does not; anything else you
    added to the file is lost. On ALM the conversion notes then say
    `EXISTING CONTENT REPLACED` and name the saved prior copy. Re-convert the
    tests that name a dropped entry. On ALM, conversion is whole-project, and a
    conversion under an earlier run's ID — including the Migration Console's
    default `Domain-Project` ID — skips every test that run already converted
    and is still Python on the server, which is exactly the tests you need to
    rebuild. Run analysis and then conversion under a **new run ID** (a new
    Analysis Run ID in the Migration Console, `--run-id` on the CLI). On a
    filesystem conversion, convert those tests again with Overwrite Policy
    `backup` or `overwrite`, or into a new output root: the default, `fail`,
    refuses to overwrite what is already there.
- **"unterminated string literal" reported by UFT at line N**: UFT 26.1's
  pre-execution validator synthesizes a malformed error for lines it *thinks*
  call a test-object method without parentheses; because that synthesized
  statement does not compile, any flagged line — with or without quotes in
  it — kills the whole action. The converter works around the known cases
  (FSO methods, `.Value` assignments, `ExpandEnvironmentStrings` calls, bare
  `.Count` reads on collections, assignments to members of UFT's reserved
  objects such as `Setting` and `DataTable`, and parentheses enforced on
  known UFT methods such as `.Activate`). If you hit a new one, report the
  exact line — do not hand-edit the `.pts` on the server.
- **UFT runs an older version of the test** after you re-uploaded or reverted
  it: UFT caches extracted tests under `%LOCALAPPDATA%\Temp\TD_80`. Phoenix
  purges this cache automatically (on by default; `--no-purge-uft-cache` turns
  it off), but only for the Windows user running Phoenix on that machine. On
  every *other* machine that runs the tests — Test Lab execution hosts, other
  engineers' workstations — delete `%LOCALAPPDATA%\Temp\TD_80` before the next
  run. The command is in
  [advanced_troubleshooting.md](advanced_troubleshooting.md) § *Stale UFT test
  cache (TD_80)*.

### A converted test behaves differently with no error reported
- **You changed which function library a test links after it was converted,
  and it now runs the old library's functions** — or the new library's
  functions go missing from the second iteration of a multi-test Test Lab run
  onward. Library links are written into the converted script at conversion
  time, and a later relink does not update them. Change library *content*
  rather than links, or convert again under a new run ID and clear
  `%LOCALAPPDATA%\Temp\TD_80` on every execution host. See
  [limitations.md](limitations.md) § *Library links are fixed when a test is
  converted*.
- **A test takes roughly 6-15 s longer per run than its VBScript baseline**
  when it calls a helper that walks every running process (a
  `GetObject("winmgmts:").InstancesOf("Win32_Process")` loop that reads `.Name`
  on each returned object), about 4-12 s per call. This is expected after
  conversion, and nothing fails. Change the **source** helper to a filtered
  query — `ExecQuery("Select ... from Win32_Process where Name = '<exe>'")` —
  before converting. See [limitations.md](limitations.md) § *A source helper
  that scans every process runs slower after conversion*.

### "Blocked unsupported construct" / status `blocked` in the ALM pipeline
The converter refuses to upload tests with unresolved blockers (fail-closed
policy). The report lists each blocker (construct blockers with their source
line; the others name the action, cross-test reference or error). Options:
1. Remediate the construct in the VBScript source and re-run. A custom mapping
   rule does not clear this blocker: mappings rewrite the converted text after
   the blocker has already been recorded, so remediate the source instead.
2. Expert override (CLI-only): `--allow-blockers` uploads anyway and records
   the override in the run notes. The blocked statement is **replaced by a
   comment** in the uploaded Python (`# BLOCKED: unsupported …`), so whatever
   it did no longer happens — use this only when you have verified the blocked
   lines are unreachable or harmless. The GUI has no override — park deferred
   assets on Step 5 instead.

`--allow-blockers` covers best-effort **construct** blockers only. Two classes
are data-integrity stops that keep `status=blocked` even with the flag set:

- **`converted output is not valid Python`** — the converted text will not
  parse. It would upload and verify clean and then be dead the moment UFT runs
  it. The `--dry-run` analysis path applies the same stop, and the filesystem
  path refuses it as a tier of its own (not overridable by strictness either).
- **A cross-test reusable-action reference that cannot be retargeted** to the
  converted callee's renumbered layout — building anyway would upload a caller
  natively bound to the *wrong* callee action.

For either, remediate the source or the call chain; the flag will not move the
run. The second class has its own entry below for the message *that callee has
no conversion record in this run*.

Constructs that remain intentionally unsupported: `Execute`/`Eval` as a
statement (dynamic code) — at `strict` and at the shipped default `standard`
strictness the converter names these as blockers. At `--strictness permissive`
it records a warning instead and emits a `raise NotImplementedError(...)` stub
in their place; that stub is valid Python, so the syntax gate passes it and the
test fails only when UFT runs that line. ALM conversions are forced to `strict`,
so they always block there.

`GoTo <label>` (including the inline `If … Then GoTo <label>` form), `On Error
GoTo <label>` and VBScript classes (`Class…End Class`, `Property Get/Let/Set`)
are recognised by no construct detector, so no blocker names them and a scan
whose only issue is one of them still reports `go_no_go: go` — but they are
not silent. The converter emits them verbatim (`Class(Cart)`,
`Property(Get Bar)`, `On Error GoTo Handler`), the result is not valid Python,
and the syntax gate refuses the asset with a generic `converted output is not
valid Python` blocker before any AOM build or ALM write — at every strictness
level, and not overridable. The one construct that genuinely reaches UFT is
`Eval` used *inside an expression* (`x = Eval("…")`): it converts to a call to
an undefined `Eval`, which parses cleanly, uploads and verifies clean, and
raises `NameError` only when UFT runs the test. Sweep the source for all of
them before converting; see [limitations.md](limitations.md) § *Not detected
before conversion*.

`ExecuteFile` is refused the same way, and the refusal is decided from the
statement kind alone — dynamic library loading from script has no safe
automatic translation. Phoenix *does* resolve each test's linked ALM Test
Resources, but that lookup plays no part in this decision, so linking the
library in ALM does not clear the blocker. (ALM conversions are forced to
`strict`, so it is always a hard blocker there; a custom mapping rule cannot
clear it either — mappings are applied at emit time, after the blocker is
recorded.) Remediate by deleting the `ExecuteFile` line from the source and
relying on the linked-resource path instead: function libraries linked as ALM
Test Resources are downloaded, converted once to a Python Function Library
(`.pfl`), and linked to each converted test automatically (shared resource —
not inlined into actions), so their functions are already in scope with no
loader line and no `import`.

Action-level parameter definitions (Action Properties → Parameters) and
test-level definitions (File → Settings → Parameters) are both harvested from
the legacy test and re-authored on the converted test. The main flow (Action0)
has no parameter surface of its own, so its `Parameter()` reads are satisfied
by the test-level definitions, and that resolved set is authored onto the
rebuilt test's main flow. Harvesting needs UFT, so a blocker is raised only in
a **Deep** analysis (Analysis Depth = Deep) or a conversion; the default
Standard analysis never opens UFT and only notes that the definitions will be
harvested at conversion time. The blocker is raised only when a referenced name
matches neither an action-level nor a test-level definition (or when the
harvest itself fails) — add the definition in UFT, or replace the read with a
DataTable/Environment lookup. Test-level default *values* are carried, but
test-set runtime overrides do not propagate through the AOM main-flow
indirection.

See [supported_versions.md](supported_versions.md) and
[limitations.md](limitations.md).

### "that callee has no conversion record in this run"
A conversion stops on a test that calls another test's reusable action. The
asset is `blocked` and its error reads *cross-test reference '<action>
[<test>]' targets '<path>', but that callee has no conversion record in this
run*. Phoenix rebuilds each caller against the converted action layout of the
test it calls and will not guess that layout, so the run aborts and rolls back
what it uploaded. `--allow-blockers` does not clear it. There are two causes:

- **The callee was not converted in this run.** Its own conversion failed, it
  is not part of the run, or it was not ordered ahead of its caller — callees
  convert first, in the order the analysis in the same run folder gives. Deal
  with the callee first (its own entry in the report says why), and make sure
  the analysis was run under this run id before you convert.
- **The callee was carried forward from a journal that an earlier version of
  Phoenix wrote.** That journal did not record the converted layout. In
  `alm_aom_results.json` the callee shows `resumed: true` and a note that the
  journal record it was carried forward from carries no conversion maps. Run
  the analysis again under a **new run id** (in the console, enter a new
  Analysis Run ID on Step 5 and run Analysis), then convert in that run folder
  so caller and callee convert together. Keep the old run folder: its
  `alm_rollback` folder holds the pre-conversion originals.

### "Post-upload verification failed" (status `upload-verify-failed`)
After every upload Phoenix re-downloads the test and compares it with the built
payload; files the server did not overwrite are deleted and re-uploaded once,
then verified again. A mismatch that survives that repair stops the whole run:
every later asset is recorded `not-attempted`, and Phoenix restores every asset
this run uploaded — this one included — from its pre-conversion snapshot. On
version-controlled projects the checkout is abandoned as well, which returns the
server to the last checked-in version.

Check each asset's final status:

- **`rolled-back`** — the original VBScript scripts are back on the server,
  but the test's resource relations are not reverted: a test this run had
  already uploaded and verified stays related to the converted `.pfl` instead
  of its original `.qfl`. Re-relate the `.qfl` in ALM before running it from
  Test Lab (see [alm_safety.md](alm_safety.md) § *What a restore does not
  undo*), then fix the cause and re-run the whole conversion.
- **`rollback-failed`** — do **not** run the test. Restore it with
  `uft-migrate restore` (see [alm_safety.md](alm_safety.md) § *Rolling back*),
  or from ALM version history or your own backup, then report the issue and send
  the run folder.

---

## ALM version control and locks

### A locked asset was converted anyway (`entity-lock-not-cleared-proceeding`)
This is by design: a lock never fails a conversion. Phoenix gives the lock a
10-second grace period to clear on its own, tries to release it, and then
converts and overwrites the asset either way. That is safe because an ALM
lock does not block `ExtendedStorage.Save` — the write that carries a test's
payload (`Script.pts`, `Test.tsp`, the `.usr`); it blocks only entity
metadata writes (`SetField`/`Post`), which the upload path already treats as
optional. Failing instead would leave the project half Python and half
VBScript, which breaks cross-test action chains.

`UnLockObject()` releases only *your own* lock — against another session's it
returns cleanly and does nothing — so revoking a foreign lock means deleting
its row from the project's `LOCKS` table through the OTA `Command` object,
which ALM disables by default. Where that is available the run logs
`entity-lock-force-revoked`; where it is not, it logs
`entity-lock-not-cleared-proceeding` and the conversion completes regardless.
Either way the asset carries a note naming the lock holder. When Phoenix can
read the project's `LOCKS` table — the same OTA `Command` access that revoking
a lock needs — the note also gives the holder's machine, ALM session id, lock
time and last-active time. Otherwise it names only the user.

Nothing needs re-running. What it does mean: if someone was still editing
that asset, their work has been overwritten and their ALM client may hold a
stale copy — have them close and reopen the test. Run conversions in an
agreed window with the project empty to avoid this entirely.

### An asset fails as "Version control blocked" (status `vc-blocked`)
On version-controlled projects Phoenix undoes any pre-existing checkout
before converting (the server reverts to the latest checked-in version, which
is what gets converted). Undoing **another user's** checkout requires the
connected ALM user to hold the "Manage checkouts"-equivalent permission.
Grant that permission to the migration account — or have the holder check in
or undo their own checkout — then run the conversion again under the same run
id. Do **not** add `--resume`: it is refused after a run that failed, and a
`vc-blocked` asset aborts the run. The aborted run rolled back what it had
uploaded, so those assets are converted again; any asset an earlier run already
uploaded and verified, and that is still Python on the server, is carried
forward automatically.

### Where to see who holds checkouts and locks
The analysis report's **Version Control & Locks** section (same name in the
markdown summary) lists how many assets are checked out or locked and names the
holder of each — the first 100 of each kind, though the counts always cover
all of them. It is the chase list to clear before a conversion. That section is
written only when the project is version-controlled (at least one analysed asset
reports version control enabled); on a project without version control it is
omitted entirely, and a lock holder is then named only in the per-asset run
note described above. Analysis itself performs no version-control writes, so
it is safe to run at any time.

---

## Runtime errors in converted tests

These appear when a **converted** test executes. Most are runtime issues in the
test's environment or object repository, but check the conversion notes first:
some documented limitations and one open defect show up this way. Two rules
first:

1. **Prefer running converted ALM tests from ALM.** That is how they will be
   run in production — from your existing Test Lab sets in the ALM
   client, or via the CLI-only support lever `--run-via-alm` when the run needs
   to land in the Phoenix report (there is no GUI run-from-ALM option). Opening
   a converted test from ALM in UFT One and pressing Run is a legitimate spot
   check for a single test — it is what the CLI itself recommends, and it is
   the only check available for filesystem conversions. Two caveats when you
   do: purge `%LOCALAPPDATA%\Temp\TD_80` first, because a stale extraction
   makes UFT execute the pre-conversion build (Phoenix purges that cache before
   its own Test Lab runs for the same reason); and a resource-resolution
   failure seen only in a manual run is not automatically a conversion defect —
   reproduce it from Test Lab before filing it as one.
2. When one line fails and you skip past it, treat every later error in the
   same run as suspect until the first failure is fixed — most are
   consequences, not independent defects.

### `SystemUtil.Run(...)` fails with `Error: Exception occurred. (0x-7ffdfff7)`

**Meaning:** the executable path in the call does not exist on this machine.

Legacy tests frequently launch sample or line-of-business applications from
era-specific install paths. Phoenix does not rewrite path literals in your test
scripts — converting VBScript to Python translates the language, not
what the script says. A converted test that carries an `HP\`, `HPE\` or
`Micro Focus\Unified Functional Testing` path will fail `SystemUtil.Run`
exactly as the VBScript original did on that host. If this error appears:

- Read the path in the error dialog literally and check it in File Explorer.
- Correct the path in the source test, or install the application at that
  path. A surviving vendor-era prefix is intended behaviour, not a converter
  gap — do not report it as one. (Phoenix deliberately never rewrites these
  prefixes: a rewrite can collapse a test's own fallback list of install
  locations into one repeated path.)
- The only path literals Phoenix alters are over-escaped backslash runs. On
  the ALM path each one is recorded as a per-asset converter finding naming the
  before and after value, and rendered on the *Convertible Findings*
  drill-down (`analysis_convertible_findings.html`) that `scan_report.html`
  links; `scan_report.html` itself carries only the rollup count. Filesystem
  conversions do not surface it at all — the converter raises the warning but
  nothing carries it into the report, so diff the converted file if you need to
  see which literals changed.

### `Cannot identify the object "X" (of class Y)`

**Meaning:** UFT's object repository could not match the object's recorded
identification properties against anything currently on screen. A test that lost
its shared object repository during conversion reports a different message —
`Cannot find the "<object>" object's parent` — which step 1 below covers.

If this test **passed** under VBScript before conversion, check that baseline
run first. A duration at or just above the object sync timeout that ends in a
`Replay Warning` on a step that is **not** an `OptionalStep` means the
identification failure already existed and was graded as a warning — a
`Replay Warning` from an `OptionalStep` is normal and means nothing here. See
[limitations.md](limitations.md) § *Conversion can surface
object-identification failures your baseline hid*.

Work through, in order:

1. **Check this asset's conversion notes.** Look for `[warning] shared object
   repository NOT carried into the rebuilt test`. If it is there, re-associate
   the repository in UFT (**Resources > Associate Repositories**) — see
   [limitations.md](limitations.md) § *Known defect (ALM path): a shared object
   repository can be dropped on a caller test*. Also review
   [limitations.md](limitations.md) § *Test-level artifacts not carried*:
   Environment variables, externally linked Data Tables and Record-and-Run
   settings do not travel with a conversion, and a test can fail at run time for
   that reason alone.
2. **Was the application actually running?** If an earlier line (for example
   the `SystemUtil.Run` launch) failed, this error is a consequence — fix the
   launch first.
3. **Check the add-ins.** Open the test's properties (in ALM, or File >
   Settings in UFT) and confirm the add-ins the object classes need are
   associated — `UIAWindow`/`UIA*` objects need **UI Automation**,
   `WpfWindow`/`Wpf*` need **WPF**, and so on.
4. **Check the repository and highlight.** Open the Object Repository, locate
   the object named in the error, and — with the application running — use
   **Highlight in Application**. If highlighting fails, the recorded
   identification properties no longer match the live application (window
   titles frequently change across application versions, e.g. an HPE-era
   title on a rebranded build). Update the object's identification properties
   or re-record it.
5. **Verify the script line maps to the repository object.** The name in the
   script line must match a repository object of the same class in that
   action's repository. A mismatch means the repository association (not the
   code) needs repair.

---

## Where to look when a run fails

A run writes its artifacts under `out/<run_id>/`; which files appear depends on
the path it took. The HTML pages follow `--report-format`, except the ALM
drill-down pages (`analysis_*.html`), which are always written.

| File | Contents |
| --- | --- |
| `scan_report.html` | Per-asset blockers and warnings from analysis |
| `executive_summary.html` | Verdict, next steps, links to the detail reports. Written by the `run` command (filesystem or ALM) and by `summarize` — not by `scan`, `convert`, or ALM analysis |
| `analysis_assets_failed.html` | Failed assets with their causes (ALM) |
| `alm_preflight.json` | Why the pre-flight gate refused the run — no ALM writes were made when it did |
| `alm_aom_results.json` | Per-test ALM pipeline results, incl. blockers and upload verification |
| `alm_analysis_results.json` | The analysis the pre-flight gate judged the conversion against |
| `conversion_summary.json` | Machine-readable per-asset outcome of an ALM run — written by ALM analysis as well as by a conversion |
| `resume/alm_test_results.ndjson` | Per-asset journal — the only record left if the run is killed |
| `migration_log.txt` | Structured JSON-lines event log (ALM runs) |
| `convert_report.html` | Per-file conversion status (filesystem only) |
| `validation_report.html` | Post-conversion syntax/UFT checks (filesystem only) |
| `analysis_cli_*.log`, `run_cli_*.log` | Raw CLI output captured by the GUI |

When contacting support, send the whole `out/<run_id>/` folder.
