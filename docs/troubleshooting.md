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
Install UFT One 26.1 or 26.3, or run a repair install. The converter's ALM pipeline
builds tests through UFT's Automation Object Model and cannot run without it.

### IronPython runtime incomplete
`doctor` reports missing files such as `IronPython.Modules.dll` or the `Lib\`
standard library next to `IronPython.dll` under the UFT installation. Expect
this on a fresh install of either supported version: the UFT One 26.1 and
26.3 installers both ship `IronPython.dll` without these files. Converted
Python tests will import-fail at run time until they are present. Copy the
missing files from the NuGet packages **IronPython 3.4.1**, **IronPython.StdLib
3.4.1**, and **DynamicLanguageRuntime 1.3.4** into the folder that contains
`IronPython.dll`, then re-run `doctor`. An upgrade from 26.1 to 26.3 leaves
files you copied in place, so a machine repaired on 26.1 stays repaired.

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
- **ALM conversions** do not need `--resume`. Re-run with the same `--run-id`
  and the same options. If the interrupted conversion's wave is still open,
  the re-run continues it, with or without the flag, and first checks any test
  it may have left half-written (see *Native crashes and interrupted ALM
  conversions* below). After a run that finished — completed, or aborted and
  rolled back — `--resume` is refused with exit code 2, so leave it off. Either way the conversion carries
  forward every asset an earlier run of that run id uploaded and verified,
  provided the server still holds its complete Python payload. A
  carried-forward test still serves as a callee, so a test that calls it is
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

### "ALM discovery failed: …"
The analysis or conversion stopped at its first step, discovery, which logs in
to ALM in a process of its own and lists every test in the project's Test Plan.
It could not finish, so the run stopped instead of going on with a partial
scope. This run analyzed, converted and wrote nothing. When the run continued
an unfinished conversion wave — a relaunch after a crash, or a resume — it
stops the wave instead, with `wave-stopped` and the reason `discovery-failed`
(see *The conversion stopped and stays open* below): the tests the wave
converted earlier stay converted, and one may be half-written, so run the same
command again as soon as you can; it retries discovery.

**Login.** When the message goes on with *ALM login failed during
Login(username, password).*, ALM refused the user name or password. Phoenix
does not try again, so a wrong password costs one failed login, not two, where
your ALM counts them towards locking the account. Check the user name and
password, then run again.

**Everything else** is retried once before you see it. The message says where
discovery stopped:

- *InitConnectionEx failed for …* or *ALM Connect(domain=…, project=…)
  failed.* — discovery could not reach the ALM server, or open the domain and
  project after logging in. Check the ALM URL, the domain and the project, and
  that the server is up.
- *Test Plan folder '<path>': <step> failed: <error>* — listing that folder's
  subfolders or tests, or reading one of them, failed with the error the ALM
  client returned. The message can also name the project's test list, which
  could not be read.
- *the Test Plan walk under 'Subject' missed N test(s) that the project's test
  list places there: <id> in '<folder>', …* — the walk came back without
  them, and nothing reported an error.
- *the Test Plan walk and the project's test list … differ: the walk found N
  test(s) the list does not have* — the two listings disagree. A test created
  or deleted while discovery ran does that too.
- *the discovery process crashed (exit code …) without an answer*, or *did not
  answer within 600 s and was stopped* — the discovery process itself died or
  hung, wherever it was.

For these, Phoenix has already run discovery a second time, a minute later, in
a new process with a new ALM session: `migration_log.txt` holds the warning
`alm-discovery-retried`, whose `reason` says why — for a process that died,
its exit code or the time limit — and a progress line that announced the
wait. What to do:

1. Run the same command again. A short fault in the ALM server or the network
   passes, and each run starts discovery afresh.
2. If it fails again on the same folder or the same tests, open that folder in
   the ALM client with the same account: check that it opens and lists its
   tests, and that the account can read every Test Plan folder. Check the ALM
   server's health and its logs for the time of the failure. If the discovery
   process keeps crashing, Event Viewer (*Windows Logs > Application*, events
   1000 and 1001) names the faulting module
   ([advanced_troubleshooting.md](advanced_troubleshooting.md) §9).
3. If it still fails, collect diagnostics for Merito support (see *Collect
   diagnostics for Merito support* below). The bundle carries the run folder's
   `migration_log.txt`, where each discovery that reached the Test Plan leaves
   one `alm-discovery-walk` line: the folders it walked, the tests it saw in
   each top-level folder, what it skipped, the result of the check against the
   project's test list, and the error. It also carries the discovery process's
   own error in full, with the ALM client's error code, from the process logs.

A conversion also runs discovery a second time when it succeeds but comes back
without tests the signed-off analysis covered; if they are still missing, the
pre-flight gate refuses the run as `analyzed-but-not-selected`
([advanced_troubleshooting.md](advanced_troubleshooting.md) §4).

A warning `alm-discovery-folder-unreadable` in `migration_log.txt` is not a
failure: the project's list holds the tests it names, the walk did not return
them, and reading their folder failed twice, so discovery could not tell
whether they belong in the run. It counted them and carried on, and the
executive summary's Next Steps name them too. Look them up in ALM: a test in
no Test Plan folder (*Unattached*) is never part of the conversion; a test
inside the Test Plan should have been found, so run the analysis again and
check that it is listed.

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
- **"unterminated string literal" reported by UFT at line N** (UFT 26.1 only —
  UFT 26.3's script engine, `ScriptExeEngine.dll`, no longer contains the
  validator's error text, and the converter's workarounds are harmless there): UFT 26.1's
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
  `uft-migrate restore … --wave <wave>`, where `<wave>` is the asset's `wave` in
  `alm_aom_results.json` (see [alm_safety.md](alm_safety.md) § *Rolling
  back*), or from ALM version history or your own backup, then report the issue
  with a diagnostics bundle (see *Collect diagnostics for Merito support*
  below). Until every such test is restored or settled, the
  next conversion in that run folder stops and prints the restore command for
  each one.

---

## Native crashes and interrupted ALM conversions

An ALM upload conversion runs under a *crash supervisor*, and each
all-or-nothing conversion is a *conversion wave* that can span several
attempts. [advanced_troubleshooting.md](advanced_troubleshooting.md) §9
explains both; [alm_safety.md](alm_safety.md) § *Interrupting and resuming*
says what an interruption leaves behind.

Every `uft-migrate restore` command these messages print is complete, and runs
from any folder: it carries the run id and `--output-root` with the full path
of the folder that holds the run folder. A command that writes to ALM reads the
password from `UFT_MIGRATE_ALM_PASSWORD`, and the message says to set it first.
Run several in the order given, which is callers first.

### The conversion process crashed
The Migration Console's status line reads *The conversion process crashed (…)*,
then *Cleaned up after the crash: …* and *Relaunched the conversion (attempt N,
…)*. Windows ended the conversion process (a native crash); the supervisor
recorded it, cleaned up and started the conversion again. The new attempt
checks any test the crash may have left half-written against the copy the wave
froze before changing it, restores it from that copy if it differs, and
carries forward the tests already converted.

- **It recovered.** The run carries on and ends as usual. *Conversion Complete*
  adds how many crashes were recovered. The executive summary's Next Steps say
  how many were relaunched automatically and whether any struck after a
  payload write began, and name the evidence folder `crash_recovery\<wave>\`;
  each affected asset carries a `[crash recovery]` note, listed under **Crash
  Recovery Notes** on the assets page (`analysis_assets.html`) and in
  `scan_report.md`. The assets converted before the crash are reported as
  converted by an earlier attempt of this run, with what their conversion
  recorded, and the report's total time covers every attempt (not the time
  between them). Nothing needs doing, but the evidence does not stay forever:
  Phoenix deletes `crash_recovery\<wave>\` itself once two later conversion
  waves in this run folder that wrote a test have closed (a launch that wrote
  no test, such as one the pre-flight gate refused, does not count, even if it
  replaced a function library: library writes are not recorded in the
  journal), so copy it elsewhere if your records need it. A memory dump is
  never in that folder, because a dump may hold the ALM password: if Windows
  wrote one, it is in the Windows crash-dump folder that the attempt's
  `crash.json` names (`"wer"` > `"dump"`), and Windows replaces the oldest
  dumps there (it keeps 10 by default).
- **Recovery stopped at the crash budget** — the third crash while the same
  test was in flight, the sixth in the wave, or the second in a row outside any
  test. The supervisor aborts the wave: the test that was in flight, if any,
  ends `process-crashed` (report category *Crashed the conversion process
  repeatedly*), and everything the wave wrote is rolled back from its copies,
  callers first; each asset's status says whether its restore worked
  (`rolled-back` or `rollback-failed`). A wave with nothing to roll back — it
  wrote no test, or every test it wrote is already back on its copy — is
  closed without an abort. *Conversion Failed* lists the outcome by status, and
  the executive summary's Next Steps say why the wave was aborted and whether
  its rollback finished. If the test that crashed uses a function library — its
  own or `PhoenixVBRuntime.pfl` — its notes add that its relation to
  `PhoenixVBRuntime.pfl` and the shared `.pfl` libraries its conversion wrote
  are not reverted — exactly which, when the crash came after its upload began,
  otherwise that it may have — and where the copies saved before they were
  replaced are. Every asset the rollback restores says the same in its own
  rollback note. Collect diagnostics for Merito support (see *Collect
  diagnostics for Merito support* below) — the bundle carries
  `crash_recovery\<wave>\`, `crash_breadcrumbs.log`, `migration_log.txt` and
  `resume\`, which matter most, with Windows' crash reports — and re-run the
  whole conversion once the cause is known.
- **It crashed during a rollback.** Finishing an interrupted rollback is not
  automated. The message lists every test still to restore, callers first,
  and up to three numbered `restore --wave` commands; the full list, in order,
  is in `crash_recovery\<wave>\restore_commands.txt`, which the message names.
  Run them, then run the conversion again with the same inputs.
- **It ended without recording its result.** A conversion process that exits —
  even with exit code 0 — without recording its result is never reported as a
  success: the supervisor says what happened and exits with a non-zero code.
  Unless every asset had already finished, the wave stays open, and running the
  conversion again continues it. If every asset had finished, the message says
  so, and running the conversion again carries them all forward and only
  records the result or writes the reports.

### The conversion stopped and stays open (`wave-stopped`)
The conversion exits 2 with a result whose `status` is `wave-stopped` (or
`journal-unwritable`), and its message starts *Conversion stopped (<reason>).
No further ALM change was made after this point.* It found something it must
not guess about, so it wrote nothing more to ALM. Tests the wave had already
converted stay converted — the message lists them — so the project is part
Python and part VBScript until the wave continues. Unlike a failed run, the
wave stays open: the run folder's report set is left as it was, the checkpoint
is not marked failed, and the stop is written to `alm_wave_stop.json` in the
run folder. *Conversion Failed* shows the message in full, first, and names
`alm_wave_stop.json`. The message names the test, the copy to restore it from
and numbered next steps, with every command written out. Take them, then run
the conversion again with the same inputs (in the console: **Convert
Project**, either answer to *Resume Previous Run*): the wave continues.

| Reason | What it means | What to do |
| --- | --- | --- |
| `journal-unwritable` | The conversion journal, `resume\alm_test_results.ndjson`, could not be written (disk full, permissions, a file lock), so the conversion stopped before its next ALM write. A program that holds the file for a moment — a backup or sync agent, an antivirus scanner — is waited out for about 8 seconds first. | Fix the cause and run again. |
| `snapshot-failed` | The copy of a test that the conversion keeps before changing it could not be made in the run folder — the disk is full, for example, or a program holds a file in it. Nothing was written to ALM for that test. | Free disk space (or fix the run folder's permissions, or close that program), then run again with the same inputs: the wave continues where it stopped. |
| `restore-failed` | After a crash, a test that may be half-written differed from the wave's copy, and restoring that copy failed. | Run the `restore --wave` command in the message, then run again. |
| `restore-failed-earlier`, `rollback-interrupted`, `rollback-incomplete` | A restore failed in an earlier attempt; or the process stopped while rolling the wave back; or the rollback ended with tests still not back on the wave's copy. These tests may hold converted or half-written payloads. | Run each `restore --wave` command in the message, in the order given, then run again. For `restore-failed-earlier` the message also gives the `--accept-current-state` command, to settle tests you have inspected as they are. |
| `reconcile-failed` | A test that may be half-written could not be found in ALM, or downloaded, to check it. | If ALM was unavailable, run again once it is back. Otherwise restore the test with the command given, or — when it could not be found — inspect it in ALM and settle it as it is with the `--accept-current-state` command given. |
| `snapshot-invalid` | The copy the wave froze of a test is missing or damaged, so the test cannot be restored automatically. | Inspect the test in ALM; if it is not intact, put it back from your ALM backup or version history. Then settle it with the `--accept-current-state` command in the message — it sets the damaged copy aside, and the wave freezes a new one from what ALM holds — and run again. Until the test is settled the conversion stops here every time. |
| `snapshot-drift` | A test changed on the server after this wave first saw it, and the wave may already have written it, so the wave's copy no longer describes it. When the journal shows the wave never wrote that test — it changed after a Cancel, say, before its upload started — there is no stop: the wave freezes its copy again from what ALM holds, keeps the old copy beside it, notes this on the test and logs `alm-wave-snapshot-refrozen`. | Inspect the test, then either put it back to the wave's copy with the `restore --wave` command in the message and run again, or keep the change: close the wave with the `--abandon-wave` command in the message (refused while any test in the wave may be half-written) and convert again — a new wave starts from what the server holds now. |
| `wave-scope-changed` | The set of tests the conversion finds changed after the wave started. This attempt wrote nothing to ALM; tests the wave converted earlier stay converted. Tests the wave started with that are missing now can come from a transient fault while ALM listed the Test Plan; Phoenix already ran discovery a second time before it stopped (`alm-discovery-retried`). | Run the conversion again with the same inputs: it runs discovery again. Only if the same tests are missing again, check that the path filters and exclusions are the ones the wave started with, and whether those tests were moved or deleted in ALM. When tests were added instead, or to convert the new scope, close the wave with the `--abandon-wave` command in the message, then run the analysis and the conversion again. |
| `discovery-failed` | The wave was continuing — after a crash, or on a resume — and discovery, which lists the project's tests first, failed even after its retry (*ALM discovery failed: …* in the detail line). This attempt wrote nothing to ALM and checked nothing yet; tests the wave converted earlier stay converted, and a test a crash interrupted may still be half-written. | Run the same command again: it retries discovery, then continues the wave, checking that test first. If the detail says the login failed, correct the password first (it is not one of the wave's inputs). Until the wave has continued, do not run its tests. See *"ALM discovery failed: …"* above for the other causes. |
| `legacy-in-flight-unverified` | A test that a Phoenix 1.1.4 or earlier run was converting when it stopped could not be proven unchanged since. | Restore it with the plain `restore` command in the message (no `--wave`), from the first copy this run folder kept of the test — the message says when it was saved; it can be older than the run that stopped, so check it is the version you want — or inspect the test and settle it with the `--accept-current-state` command given; then run again. |

Any other reason is explained the same way in the message itself.

`--accept-current-state` and `--abandon-wave` make **no** change in ALM; they
only update the run's journal. The messages print them in this form:

```
uft-migrate restore --output-root "<folder that holds the run folder>" --from-run "<run id>" --wave <wave> --alm-test-id <id> --accept-current-state
uft-migrate restore --output-root "<folder that holds the run folder>" --from-run "<run id>" --abandon-wave <wave>
```

The first records that you inspected each named test and accept it as it is
now, which settles it; the wave's copy of it is set aside, so the next attempt
takes the accepted state as its starting point. Use it only after checking the
test in ALM. The second closes a wave without converting further. It is refused
while any test in the wave may still be half-written, and the refusal lists the
restores still owed, callers first, and the `--accept-current-state`
alternative. Tests the wave converted stay converted, and the next conversion
carries them forward.

### "Another Phoenix process … is working in the run folder"
A conversion, an analysis or a restore is already running in this run folder,
and only one may work there at a time. Nothing was written. Wait for it to
finish (watch `migration_log.txt` in that folder), or stop it, then run again.
The lock is released when its holder ends, however it ends; the file
`resume\phoenix_run.lock` stays behind and is harmless. If the message says the
lock file could not be opened, check the run folder's permissions. In the
Migration Console the same message appears as *Run Folder In Use* when you
press **Run Analysis** or **Convert Project**, and the console then leaves the
run folder exactly as it was.

### "conversion wave … is not settled" or "… was started with other inputs"
The conversion was refused before anything was written.

- **Not settled.** An earlier conversion wave in this run folder may have left
  the named tests half-written or half-restored, and a new wave would take that
  damage as its starting point. The message gives one numbered `restore
  --wave` command per test, callers first, and the `--accept-current-state`
  command that settles them as they are once you have inspected them in ALM.
  Run those, or run the original conversion again to continue that wave, then
  run your conversion again.
- **Other inputs.** An unfinished wave is open in this run folder, and this
  launch differs from the one that started it: any change to the command line
  other than `--run-id`, `--resume`, `--failed-only` and the value of
  `--password` counts — in the console, any selection that changes the
  command *Review Command* shows. If that wave has not written any test yet —
  it was cancelled before its first upload, for example — it is not refused:
  it is closed (outcome `superseded-no-writes`), the run says so, and the new
  launch starts a new wave. A wave that has written a test is refused: the
  message says which options differ and gives the `--abandon-wave` command
  that closes it. Run the original command again to continue the wave, or
  close it with that command once nothing in it is half-written.

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
| `resume/alm_asset_details/` | What the report shows for each converted asset, kept for a later attempt that carries the asset forward |
| `alm_wave_stop.json` | Why an ALM conversion stopped and stays open, with the next steps — written instead of a report set |
| `crash_recovery/<wave>/` | The crash supervisor's evidence for each conversion attempt, including Windows' crash report when there was a native crash. Deleted automatically once two later conversion waves in the run folder that wrote to ALM have closed (a wave that wrote nothing, such as a launch the pre-flight gate refused, does not count; *nothing* means no test: such a wave may still have replaced a function library, because library writes are not journaled); never holds a memory dump (`crash.json` names where Windows wrote it) |
| `crash_breadcrumbs.log` | One line per ALM call or build step of an upload conversion; the last line of a crashed process names the step it died in |
| `migration_log.txt` | Structured JSON-lines event log (ALM runs) |
| `convert_report.html` | Per-file conversion status (filesystem only) |
| `validation_report.html` | Post-conversion syntax/UFT checks (filesystem only) |
| `analysis_cli_*.log`, `run_cli_*.log` | Raw CLI output captured by the GUI |

Two places outside the run folder:

| Location | Contents |
| --- | --- |
| `%LOCALAPPDATA%\Merito\UFT Phoenix\logs\` | One diagnostics log per Phoenix process, JSON lines: what each process was, the errors it met (with the full traceback and the ALM client's error code) and how its child processes ended. A message that gives a reference such as `E-20261006T101500Z-7720-41` names an error recorded there in full; quote it to support. Kept 30 days. The ALM password is masked before a record is written: by its value when it is 6 characters or longer, and wherever it follows a name such as `password` |
| `out\_support\` | The support bundles *Collect Diagnostics…* and the Start Menu shortcut *Merito UFT Phoenix Collect Diagnostics* write, each a zip with a folder of the same files beside it; when there is no `out\` folder, they go to `%LOCALAPPDATA%\Merito\UFT Phoenix\support\` |

When contacting support, quote the version you are running. The Migration
Console shows it on every step, in the bottom-left corner of the dark panel on
the left (*Version* and the number; see [gui_field_guide.md](gui_field_guide.md)
§ *The version line*), and `uft-migrate --version` prints it. A diagnostics
bundle records it already, in the zip's name, `README.txt` and
`MANIFEST.json`. Do not send the run folder: it holds your test sources
(`alm_aom_work\`) and lacks the process logs, the environment and Windows'
crash reports. Collect diagnostics instead (below).

## Collect diagnostics for Merito support

Phoenix keeps its diagnostics logs all the time: there is nothing to switch
on, and the problem does not have to happen again for you to collect it. You
can collect afterwards, even after closing Phoenix: each way below reaches back
as far as Phoenix keeps its logs, up to 30 days. When Merito support asks for
diagnostics, or a run failed in a way this guide does not explain, collect a
support bundle and send it to Merito support. The simplest way first:

1. **Answer Yes when the failure dialog asks.** *Conversion Failed* ends with
   the question *Collect diagnostics for Merito support now? Phoenix saves a
   zip on this PC and opens its folder. Nothing is sent.* **Yes** collects the
   run that just failed, at once — or, when a collect you started earlier is
   still running, as soon as it ends: its *Diagnostics Saved* then says the
   failed run is collected next, and the zip saved after it is the one to
   send. **No** closes the dialog, and you can still collect later. A
   conversion you stopped with **Cancel** asks nothing. A failed analysis has
   no dialog: its status line names **Collect Diagnostics…** (3 below).
2. **The Start Menu shortcut:** **Start Menu > Merito > Merito UFT Phoenix
   Collect Diagnostics** (type *collect diagnostics* in Start search). It
   collects without opening the Migration Console, so it also works after you
   closed the console and when the console will not start. A small window
   says *Collecting diagnostics for Merito support…* while it works, usually
   under a minute; then the console's own *Diagnostics Saved* message names
   the zip, and its folder opens. It takes the newest run, and saves the
   bundle in your profile's `out\` folder, the one the Migration Console uses
   when started from the Start Menu.
3. **Collect Diagnostics…** in the Migration Console, or the command line
   below. The button sits bottom left beside **Back** on every step, and works
   even while a conversion runs, which is how a hang is collected. It takes
   the run in progress, else the last analysis's, says where the bundle is
   when it is done, and opens its folder.

**From the command line**, in the folder you launch Phoenix from (`uft-migrate`
is on `PATH` when setup added it, its default; otherwise use
`<install folder>\bin\uft-migrate.cmd`):

```
uft-migrate diagnostics collect
```

It includes the newest run, or the one you name with `--run` or `--run-dir`;
`--no-run` collects the logs and the environment only, and `--list` prints
what would be collected and writes no bundle (only the collector's own process
log). When `uft-migrate` itself cannot start,
`"<install folder>\runtime\python.exe" -m uft_migrate.diagnostics collect`
runs the same collector. Every option is in [usage.md](usage.md) §
*Collecting diagnostics*.

With the dialog, the shortcut or the button, if crash dumps, or the scripts of
failed tests, exist for the run, one question asks first whether to save them
as well, to a separate file: **Yes** saves only what it named, **No** the logs
only, and **Cancel** nothing at all. Otherwise nothing is asked. The command
line asks nothing: its `--include-…` options decide (below).

**When none of these works**, zip the logs folder itself and send that zip: in
File Explorer, type `%LOCALAPPDATA%\Merito\UFT Phoenix` in the address bar,
right-click the `logs` folder and choose **Send to > Compressed (zipped)
folder** (on Windows 11, **Compress to ZIP file**). When that folder does not
exist, the logs are in `%TEMP%\Merito UFT Phoenix\logs`. The ALM password is
masked in it, as in every log record (see the table above). Unlike a bundle,
it keeps the ALM server, domain, project, user and test names and your Windows
user name, and it lacks the environment, Windows' crash reports, the run's
journal, logs and results that a bundle takes from the run folder, and
`TRIAGE.md`. Never send the run folder instead: it holds your test sources and
can be gigabytes.

**Where it is saved.** In the output folder:
`out\_support\UFTPhoenix-diagnostics-<version>-<time>.zip`, beside a folder of
the same name that holds the same files unzipped, so you can read every file
before you send it; `MANIFEST.json` lists each file with its SHA-256 hash. The
Start Menu shortcut uses the `out\` folder of your profile,
`%USERPROFILE%\out`. When `out\` does not exist or cannot be written, the
bundle goes to `%LOCALAPPDATA%\Merito\UFT Phoenix\support\`. *Diagnostics
Saved* always names the path.

**Nothing is sent.** Collecting opens no network connection, logs in to
nothing, starts neither UFT nor the ALM client, and writes nothing into a run
folder. You send the zip yourself, by your usual channel.

**What is inside:** the process logs of the last 30 days, as far back as
Phoenix keeps them (on a busy PC the oldest are deleted sooner, once the logs
folder passes 200 MB; when there are more than a bundle holds, the newest come
first); the environment (Windows, Python and pywin32, the UFT One and ALM
client versions, Windows Error Reporting's settings and crash reports,
Application events 1000 and 1001, and `doctor`'s read-only checks); the run's
logs, journal and results, chosen by exact file name; and `TRIAGE.md`, the
first look Merito support takes, which you can read too.

**What is never inside:** your test scripts, data tables, object repositories or
function libraries (`alm_aom_work\`, `converted\`), the Migration Console's
settings file, `.env` files or memory dumps. ALM server, domain, project, user,
test, folder and library names are replaced by tokens such as `project-1` and
`test-3f9a2c`; the file that maps the tokens back, `…KEEP-PRIVATE-names.json`,
stays beside the zip on this PC. Phoenix's own words in its records (event and
step names, exception types, its code lines, COM member names) stay as they
are, even where one equals a name of yours: a test named *Terminal* does not
turn the journal's `terminal` records into tokens. A bundle that cannot be
cleaned is not written at all.

**The ALM password.** A value that follows a name such as `password`,
`--password` or `UFT_MIGRATE_ALM_PASSWORD` is masked in every file. Every file
is also searched for the password itself, in each of its encodings, and a file
that still holds it is left out and listed in `MANIFEST.json` — when the
collector knows the password. *Collect Diagnostics…* passes it, and the
collector also reads the password the Migration Console saved in
`out\.uft-migrate-gui-cache.json` (decrypted in memory, for your Windows account
only) — which is how the Start Menu shortcut, started in your profile, knows
it. From a command line, set `UFT_MIGRATE_ALM_PASSWORD` before
`uft-migrate diagnostics collect`. When no password was available,
`MANIFEST.json` says so under `redaction.limits`: *no ALM password was available
to scan by value*.

**The separate file.** Crash dumps and failed tests' scripts are saved only if
you answer **Yes** to the question about them, and then only the kinds it
named (or when you pass `--include-dumps`, `--include-failed-tests` or
`--include-test`), and only to a second file, `…-EXTRAS-SENSITIVE.zip`. A dump
can hold your ALM password and test data, and the scripts are your test code.
Send that file only if Merito support asks for it, by a secure channel, and
change the ALM password afterwards. Windows writes a dump only where it was set
up to: when a native crash left none, Merito support may ask your
administrator to switch crash dumps on for Phoenix for a while and make the
crash happen again, the one case where a problem must be repeated; support
sends the steps, including the one that switches dumps off again.
