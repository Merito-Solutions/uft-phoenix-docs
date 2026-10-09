# UFT Phoenix Console — Complete Field Guide

This guide walks every screen, field, and button of the UFT Phoenix
Migration Console (`uft-migrate-gui`) in wizard order. For each control you
get what it does, when to change it, and a worked example. It is written for
the engineer driving a migration — no CLI knowledge required. Deep failure
diagnosis lives in the companion
[Advanced Troubleshooting Guide](advanced_troubleshooting.md).

Nearly every GUI choice maps to a `uft-migrate` command-line flag; the
**Review Command** button on Step 6 shows the exact command your selections
build, so anything you configure here can be reproduced in a script or
pipeline later. Three things it does not show:

- Review Command always builds the *conversion* command (`uft-migrate run …`).
  Step 5's analysis is a different command made from the same selections:
  `uft-migrate scan` on the UFT FileSystem workflow, and `uft-migrate convert …
  --dry-run` with no `--upload` on the Upgrade ALM Project workflow. Do not use
  the Review Command text to reproduce an analysis — on ALM it uploads.
- Step 5's **Overwrite previous analysis outputs in this run folder** is done by
  the console itself before it launches the CLI, so it has no flag and never
  appears in the generated command.
- If you answer Yes to the **Resume Previous Run** dialog, the launched command
  also carries `--resume`, which the preview does not show.

---

## The navigation row

Along the bottom of every step: **Back**, **Collect Diagnostics…** and
**Next**.

**Collect Diagnostics…** writes a support bundle for Merito support: the
console's own log and those of the processes it started, the environment
(Windows, Python, the UFT One and ALM client versions, Windows' crash reports)
and the current run's logs and results — with your ALM password and test
content left out and ALM names replaced by tokens. It works on every step,
including after a failed analysis and while a conversion is running, which is
how a hung run is collected. It takes the run folder of the run in progress,
else the last analysis's, else the one the current Run ID names; it has no
field of its own.

- If crash dumps or the scripts of failed tests exist for that run, one
  question asks *Also save N crash dump(s) and the scripts of M failed test(s)
  to a SEPARATE file?*, naming only the kinds it found. **Yes** saves the logs
  and that separate file (`…-EXTRAS-SENSITIVE.zip`) with only what the
  question named, **No** the logs only, **Cancel** nothing. A dump can hold
  your ALM password and test data, and the scripts are your test code: send
  that file only if Merito support asks for it. When there is nothing of
  either kind, there is no question.
- While it runs, the button reads **Collecting…** and is disabled; the rest of
  the console stays usable.
- **Diagnostics Saved** names the zip under `out\_support\` and its size, says
  that nothing was sent, names the separate file when you made one — or, when
  you answered **Yes** and it could not be written, says why — and opens the
  folder. The folder beside the zip holds the same files unzipped, so you
  can read them before you send the zip. **Diagnostics Not Collected** gives
  the collector's reason, which names the rule that stopped it, never a value.

Nothing is sent anywhere: you send the zip yourself. What a bundle holds, and
what it never holds, is in [troubleshooting.md](troubleshooting.md) § *Collect
diagnostics for Merito support*.

The button is one of three ways in. When a conversion fails, its *Conversion
Failed* dialog asks whether to collect at once (see *Run Analysis* in Step 5
below). And **Start Menu > Merito > Merito UFT Phoenix Collect Diagnostics**
collects without the console at all — after you closed it, or when it will not
start — with the same question about crash dumps and test scripts, a small
*Collecting diagnostics for Merito support…* window while it works, and the
same *Diagnostics Saved*.

---

## The version line

The bottom-left corner of the dark panel on the left, the one that lists the
steps, names the version of Phoenix you are running: *Version* and the version
number, the same number `uft-migrate --version` prints. It is the panel's last
line on every step, Step 1 included, and stays at the bottom at any window
size. Quote it when you contact Merito support; a diagnostics bundle records
it for you.

An installed copy shows the number alone. A line that ends *· development
copy* means this console is not running from an installed package — from a
copy of the source code, for example — so the number names the last build,
not necessarily the code that is running. Say so when you quote it.

---

## Step 1 — Welcome

Orientation screen. Apart from the navigation row, it carries exactly one
button, **Get Quote**, which opens
merito.com/get-a-quote in your browser. **Book a migration services
consultation** is not on this screen: it lives in the step header card
("Need Merito Professional Services to lead the migration?"), which is hidden
on Step 1 and shown on Steps 2–6, and it opens a different page,
merito.com/book-consultation. Nothing on this screen affects the migration.

---

## Step 2 — Source Journey (Migration Source)

Pick where your tests live. Phoenix offers exactly two conversion paths, and
this single choice reshapes the rest of the wizard — ALM fields only appear
for the ALM workflow.

| Choice | What it means | Choose it when |
| --- | --- | --- |
| **Upgrade ALM Project** | Convert every UFT GUI test in the ALM project's Test Plan — whole-project, all or nothing. | Migrating an ALM estate. Requires a project backup/snapshot — the run refuses to upload without the backup confirmation. |
| **UFT FileSystem** | Convert tests stored on disk (local folders or UNC shares). | Tests are version-controlled or exported to disk rather than stored in ALM. |

There is no folder- or count-scoped ALM conversion. ALM conversion is
whole-project because a test that calls another test's shareable ("reusable")
action forms a call chain that must run under one script engine — the callee
runs inside the caller's engine, so a mixed VBScript/Python chain fails at
runtime. Converting the whole project keeps every chain uniform Python;
cross-test shareable-action references are rebuilt natively so those actions
stay in their own tests and are consumed by reference.

The **Flow preview** text under the choices summarizes the steps ahead for
the selected workflow.

*Example:* to pilot before committing an estate, use **UFT FileSystem**
against a copy of representative tests, or stand up a dedicated pilot ALM
project seeded with copies and run **Upgrade ALM Project** against it.

---

## Step 3 — Setup and Defaults

### General Settings

**Existing Config File (Optional)** + **Browse** — records the path to a
saved JSON config (the installed product reads JSON only; YAML needs the
PyYAML extra of a source install) and passes it straight through to the
engine as `--config`. It does **not** pre-fill the wizard: no field on this
screen is populated from the file. The wizard's own values are emitted as
explicit CLI flags and merged on top of the file, so any setting that also
has a control here — Output Root, Threads, Max Errors, Strictness, Report
Format, Analysis Depth, Convert Mode, Overwrite Policy, VBS Preservation Mode
— is won by the GUI whenever that control has a value to emit. What the file
does carry is the settings with no control in the wizard: custom mapping
rules (`custom_rule_mappings`, written here by **Edit Custom Mapping
Rules…**), `reserved_word_policy`, `reporting.redaction`, `search_folders`,
and `uft_object_model_path` — plus any setting whose GUI control you leave
blank or unchecked (Custom UFT Methods, filesystem out-of-scope paths, Check
Python Prerequisites).

Leave blank to use the built-in defaults, or a `uft-migrate.json` file in the
folder Phoenix was launched from if one is there — the engine picks that up on
its own (a `uft-migrate.yaml`/`.yml` there is picked up too, and fails the run
unless PyYAML is installed). Clearing a control hands the decision back to
the file: an empty Threads or Max Errors box, and an unticked Verbose
Reporting, Emit Dependency Graph or Parallel Mode, emit nothing, so the file's
value applies. (A blank Output Root is the exception: converted output then
goes to `out/<run id>/converted` rather than to the file's value.) **Edit
Custom Mapping Rules…** reads and writes JSON only, so it cannot open a YAML
config; with this field blank it creates `phoenix_config.json` in the launch
folder and fills the field in for you.

**Output Root** — where **converted tests** are written on the filesystem
path, mirroring the source layout: each test lands at `<output root>/<its
path relative to the source root>`. It does **not** move the reports and
logs: those always go to `out/<run id>/` under the directory Phoenix was
launched from. When you start the console from the Start Menu shortcut, that
directory is your Windows profile folder, so runs land in
`%USERPROFILE%\out\<run id>\`; when you run `uft-migrate-gui` from a command
prompt, it is that prompt's current folder. The GUI's default Output Root is
that same `out` folder, which is why converted output and run folders normally
sit side by side — point it elsewhere when the default drive is small (a
1,000-test project generates gigabytes across runs) or when policy requires
converted tests on a network share. Ignored under Convert Mode `in-place` (the
destination is the source test) and on the ALM path (conversion is in place on
the server).

Converted function libraries, including the shared helper library
`PhoenixVBRuntime.pfl`, are written to `<output root>\FunctionLibraries` —
under the first source root when Convert Mode is `in-place`. Converted tests
link those libraries, and each other's shared actions, by absolute path, so
the converted tree cannot be moved afterwards. Set Output Root to the final
location (a network share, say) before converting, or convert again into the
new location. See [limitations.md](limitations.md).

**Threads** — parallelism for analysis (default: 10). On the UFT FileSystem
workflow it is the size of the scan's thread pool; on the Upgrade ALM Project
workflow it is the number of worker processes **Standard** analysis uses to
screen the project's tests in parallel. Deep analysis and conversion are
strictly serial regardless of this setting.

**Max Errors (no effect)** — the value is accepted and checked (it must be 1
or more), but no stage stops early because of it. An ALM conversion stops at
the first asset that fails; a filesystem conversion converts every test it was
given. To stop a run that is going wrong, use **Cancel**.

**Strictness** — how the converter treats constructs it cannot translate:

| Value | Behavior | Use when |
| --- | --- | --- |
| `strict` | Blocked constructs stop the file with a `# BLOCKED` marker. | Production migrations. Recommended, and forced automatically on the entire ALM path — analysis as well as upload. |
| `standard` | Blocked constructs are skipped with a comment and recorded as blockers. | Analysis passes where you want the full blocker inventory in one run. |
| `permissive` | Blocked constructs become `raise NotImplementedError` stubs. | Exploratory conversions where you want everything else runnable immediately. |

The console starts on `standard` and remembers your last choice after that.
The ALM path forces `strict` regardless. On the UFT FileSystem workflow,
`standard` still builds and publishes a test whose unsupported lines were
replaced by a `# SKIPPED` comment — the construct is dropped from the Python,
not converted — and `permissive` publishes it with `raise NotImplementedError`
stubs. Only `strict` refuses such a test, so choose `strict` before a
production filesystem conversion. A run that publishes any waived blocker this
way ends *Conversion Complete - Approval On Hold*: the test is on disk, but
the Executive Summary withholds approval. An unresolvable reference, or
converted text that is not valid Python, stops its test at every strictness.

**Report Format** — `json`, `md`, `html`, or `both`. Keep `both`: HTML for
humans, JSON for tooling. `json` alone is for CI pipelines that parse
results.

**Verbose Reporting** — on the UFT FileSystem workflow, adds per-file detail
to the scan, convert and validation reports. On the Upgrade ALM Project
workflow it does not change the reports at all: it copies every migration-log
record into the engine's console output, which the console shows in **CLI
Output** on Step 5 when an analysis finishes and saves to `run_cli_stdout.log`
in the run folder for a conversion. Turn it on when investigating; leave it
off for clean executive reports.

**Emit Dependency Graph** — writes `dependency_graph.json` mapping which
tests call which actions/libraries. On the UFT FileSystem workflow, tick it to
get that file from the scan; an ALM analysis always writes it, ticked or not.
You do not need it to order the conversion — Phoenix converts callees before
callers by itself — but it is useful for seeing which tests call which actions
and libraries, for example before narrowing scope with Path Inclusions.

**Check Python Prerequisites** *(UFT FileSystem workflow)* — adds a
Python-environment prerequisite check to the analysis report. Use on a machine
you have not run `uft-migrate doctor` on. It has no effect on the Upgrade ALM
Project workflow; run `uft-migrate doctor` there. (Doctor is the more complete
check — see the troubleshooting guide.)

### Filesystem Source *(UFT FileSystem workflow)*

**Source Roots (one per line)** + **Add Folder** — the folders to scan
recursively for UFT tests. Multiple roots are fine (e.g. two team shares).
UNC paths are supported.

### ALM Source *(Upgrade ALM Project workflow)*

**ALM URL** — the server base, `http://server:8099/qcbin` form. If you enter
just the server root (`http://server:8099`), the tool also tries
`http://server:8099/qcbin` and `http://server:8099/qcbin/`; if you enter the
`/qcbin` form it also tries it with a trailing slash. The scheme and port are
used exactly as typed — an https server needs `https://` entered, and a
non-default port must be included.

**Test Plan Module ID** *(optional)* — ALM's internal id for the Test Plan
module. It is what makes the report's `td://` test links open the right test
in the ALM client. ALM stores it **per project**, in that project's
`COMMON_SETTINGS`, so look it up for the project you are converting and check
it again whenever you switch projects — the console remembers only the last
value you entered. Leave it blank and the report lists each test as plain
text, with no clickable ALM link; fill it in to get `td://` links that open
each test in the ALM client. Two ways to find it:

1. *ALM client (easiest)* — right-click any test in Test Plan → **Copy URL**,
   then take the digits between `TestPlanModule-` and `?`:
   `td://project.domain.host:8099/qcbin/TestPlanModule-00000000123456789?EntityType=ITest&EntityID=143`
2. *Site Administration* → **Database** tab → select the project →
   **Execute SQL**:
   ```sql
   SELECT DISTINCT CSET_CATEGORY FROM COMMON_SETTINGS
   WHERE CSET_CATEGORY LIKE 'TestPlanModule-%'
   ```
   Use the digits after `TestPlanModule-`. Note it is `COMMON_SETTINGS` — the
   desktop client's settings table; `USER_SETTINGS` is web-client-only and will
   not have the row.

You can paste the bare digits, the whole `TestPlanModule-<id>` name, or an
entire copied `td://` URL — all three are accepted. Hover the field for the
same lookup steps in-app.

**Username / Password** — ALM credentials. The password is masked and stored
encrypted (Windows DPAPI, current user) in the console's settings cache under
the launch folder. A non-blank password is never written to the command line:
it reaches the engine through the `UFT_MIGRATE_ALM_PASSWORD` environment
variable. A blank password is legal on servers that allow it, and is passed as
an empty `--password` value.

**Connect** — authenticates and loads the **Domain** and **Project**
dropdowns. The login and the domain listing run on a background thread with a
45-second timeout. Loading a domain's projects and validating the chosen
project run in the foreground, so the console can pause while a slow server
answers those. Do this before anything else ALM-related — the Domain and
Project dropdowns stay disabled until connected. Domain + Project is the
entire ALM scope selection; there is no folder picker. When the login, the
domain's project list or the project check fails, the error dialog (*ALM
Connection Timed Out*, *ALM Authentication Failed*, *ALM Connection Failed*,
*ALM Project Discovery Failed*, *ALM Project Access Failed*) ends with the line
*To send details to Merito support, use Collect Diagnostics (bottom left).
Nothing is sent automatically.*

**Domain / Project** — pick after Connect. Single-domain accounts
auto-select. The chosen project is converted whole — every UFT GUI test in
its Test Plan — so pick the project you intend to migrate in full.

**I confirm the ALM project database and repository backups are complete** —
a checkbox at the bottom of the ALM Source frame. Step 3 will not advance
until it is ticked; **Next** raises *Backup Confirmation Required*. Tick it
only once the ALM project database and repository backup/snapshot really
exists — Phoenix does not verify it.

The tick is not remembered: it is left out of the console's settings cache
on purpose, so every launch of the console starts with it clear and the
approver confirms again. Within one session it stays ticked while you move
between steps or switch projects, so untick it and confirm again for each
project and each conversion window.

### Advanced Filters (Optional)

**Path Exclusions (one pattern per line)** *(both workflows)* — glob patterns
applied to test paths/names/ids. Each workflow ships default exclusions, but
they behave differently. On the **Upgrade ALM Project** workflow the two
defaults `Subject/**/.TrashCan/**` and `Subject/**/Recycle Bin/**` are
pre-seeded into the box and re-merged on every run, so they hold whatever else
you type. On the **UFT FileSystem** workflow the defaults `**/.git/**`,
`**/out/**` and `**/__pycache__/**` apply only while the box is empty — the
moment you type a pattern the box *replaces* them rather than adding to them,
so re-add any of the three you still want.
*Example:* exclude `**/Archive/**` to skip a graveyard folder.

**Path Inclusions (one pattern per line)** *(UFT FileSystem workflow)* —
convert only the tests matching these globs. The box is hidden on the
**Upgrade ALM Project** workflow, and an ALM run never carries an include list
even if you filled the box in before switching workflows: ALM conversion is
whole-project, so the console does not offer an include filter there.
*Example:* include only `Flight_*` to convert one application's tests out of a
shared folder.

**Custom UFT Methods (one per line)** — extra method names the converter
must treat as UFT test-object methods (parentheses enforced). Add entries when
your framework wraps UFT objects in custom methods. On the UFT FileSystem
workflow the scan report lists such calls as *Unrecognized object member …
(method-call-no-parentheses)* warnings. Once a method is listed here, the
converter adds the parentheses and the validation report checks them.
*Example:* your framework calls `.ClickAndVerify` on wrapped objects — add
`ClickAndVerify` here.

**Edit Custom Mapping Rules…** — opens the mapping-rule editor: a table of
regex → replacement rewrites, saved into the config file. The rules run on
each line of **converted Python**, not on the original VBScript, so write the
pattern against the converted form. This is the escape hatch for
customer-specific VBScript idioms the converter does not know.
*Example:* your suite calls a home-grown `WaitSeconds 5` global. The converter
emits that as `WaitSeconds(5)`, so the rule is pattern
`\bWaitSeconds\((\d+)\)` → replacement `Wait(\1)`. Rules are validated as
regular expressions when you add them; re-run analysis for rules to take
effect. The editor reads and writes JSON only, and the rules run *after*
blockers are recorded, so a rule can never clear a blocker.

---

## Step 4 — Conversion Strategy

### Filesystem Conversion Options *(UFT FileSystem workflow)*

**Convert Mode** — `new` writes converted output under the Output Root,
leaving sources untouched (default; always start here). `in-place` converts
inside the source tree — only for version-controlled sources where rollback
is `git revert`.

**Overwrite Policy** — what happens when output already exists: `fail`
(stop rather than touch existing output), `backup` (set the existing output
aside, then write), or `overwrite` (replace it). Use `backup` when iterating
on a suite you have already converted once and want to diff generations.

Under Convert Mode `in-place` the policy you pick is overridden: Phoenix
always uses `backup`, because the destination is the original test. `fail`
would refuse every test, and `overwrite` would delete the only copy of the
VBScript. The run log and the test's notes say when that happened.

Read "existing output" literally: under Convert Mode `in-place` the
destination *is* the source test, so `backup` renames the customer's
original VBScript test to `<name>.bak` and the live `<name>` directory then
holds the Python. That `.bak` is the only pre-conversion copy left on disk,
and Phoenix does not re-discover it by name — so a second in-place run finds
only the already-converted `<name>` and cannot re-apply a converter fix or a
changed VBS Preservation Mode to it. To re-convert from VBScript, rename
`<name>.bak` back first. Every later generation (`.bak1`, `.bak2`, …) is a
full copy of an already-converted tree and is safe to prune; `<name>.bak` is
not.

**Parallel Mode (no effect)** — **has no effect today; do not rely on it.**
The label used to promise that the VBScript and Python versions were kept
side by side in the output for a transition window. Nothing in the conversion
reads the setting and Phoenix never writes a VBScript copy beside a converted
test, so it is not a rollback path and not a substitute for your own backup.
To keep the originals, leave **Convert Mode** on `new` (the default —
converted output goes under the Output Root and the source tree is never
touched); to carry the original lines *inside* the converted files, use
**VBS Preservation Mode** `interleave` or `comment-block` (below).

### ALM Conversion *(Upgrade ALM Project workflow)*

The ALM Conversion frame has no fields; the only Step 4 choice on the ALM
workflow is **VBS Preservation Mode** (see *Script Preservation* below). The
whole-project workflow forces every other conversion setting, so this frame
only states the policy:

> Project upgrades always convert in-place, process the full ALM project
> scope, and upload upgraded assets back to ALM. Converted tests keep their
> existing Test Lab instances and execution history; nothing is executed
> from here. In version-controlled projects each asset is checked out,
> converted, and checked back in as a new version — assets left checked out
> are reverted to their latest checked-in state first. An asset locked by
> another user's session is converted and OVERWRITTEN rather than failed, so
> run the conversion with the project empty: the holder loses unsaved work
> and their ALM client may keep a stale copy. Every overwrite is named in
> the run log.

What that policy means in practice:

- **Conversion always uploads, in place.** There is no upload switch and no
  dry-run switch: Step 5's **Analysis** is the read-only dry run (zero ALM
  writes), and Step 6's **Convert Project** — the same primary button that
  reads **Run Conversion** on the filesystem workflow — converts and uploads
  the project (with stale-file cleanup, ownership repair, and byte-level
  post-upload verification). The backup confirmation is still required
  before a run. Cross-test callers have their external "call to existing
  action" references reconstructed natively, so shareable actions stay in
  their own tests and are consumed by reference.
- **Blockers are fail-closed, with no GUI override.** One test with unresolved
  conversion blockers stops the whole conversion before any ALM write, so
  nothing is uploaded — not even the clean tests. The console refuses
  **Convert Project** with *Conversion Blocked — Unresolved Assets*, and the
  engine's pre-flight gate refuses the run as well (*NO ALM WRITES WERE
  PERFORMED*). Defer such tests by parking them on Step 5 instead (see
  *Parking failed assets*).
- **UFT's test-extraction cache is purged automatically.** Phoenix clears
  TD_80 before every run and after any run that wrote to ALM, so UFT reads
  what the server actually holds; there is no checkbox for it. The purge
  covers only the machine Phoenix runs on and the account it runs as — every
  other execution host needs `%LOCALAPPDATA%\Temp\TD_80` cleared by hand.
- **A lock never fails an asset — locked assets are overwritten.** Per
  asset, Phoenix allows a 10-second grace period for the lock to clear,
  attempts to release it, and then converts and overwrites either way: an
  ALM lock does not block the payload write (`ExtendedStorage.Save`), only
  entity metadata. The run records `entity-lock-force-revoked` or
  `entity-lock-not-cleared-proceeding` and the asset's note names the
  holder. Anyone still editing a locked asset loses that work and may hold a
  stale copy in their ALM client, so run conversions in an agreed window
  with the project empty (see *The safety model* in
  [alm_safety.md](alm_safety.md)).
- **Version-controlled projects are handled automatically.** Per asset,
  Phoenix clears the entity lock as above, undoes any pre-existing checkout
  (another user's or a stale one of your own — the server reverts to the
  latest checked-in version, which is exactly what gets converted), checks
  out fresh, converts, uploads, verifies, and checks in only after
  post-upload verification passes (check-in comment "UFT Phoenix migration:
  AOM-canonical Python conversion (verified)"). Any failure after checkout
  abandons the checkout, so the server keeps its last checked-in version.
  `.pfl` function-library resources get the same checkout/check-in
  treatment. Each successful conversion is a new checked-in version, so the
  pre-conversion version stays in ALM version history — a first-class
  rollback path. Undoing another user's checkout requires the "Manage
  checkouts"-equivalent ALM permission; without it that asset fails as
  **Version control blocked** (see the remediation guide).
- **A shared helper library is added to the project.** The first conversion
  that needs it creates the Resources folder `UFT Phoenix` and writes
  `PhoenixVBRuntime.pfl` there; later conversions merge new entries into it
  and never drop existing ones. Each converted test whose scripts use those
  helpers is linked and related to it. Analysis writes nothing. Restoring a
  test to VBScript does not remove this library or its relation — see
  [alm_safety.md](alm_safety.md) and [limitations.md](limitations.md).

**The console never runs a converted test.** The wizard's **Run Analysis** and
**Convert Project** / **Run Conversion** buttons run the *migration pipeline*,
not your tests, and there is no execution setting anywhere in the wizard —
conversion and verification of the *uploaded bytes* are all it does. Proving
a converted test still passes is a deliberate, separate, manual step you take
after the migration:

- Open the converted test in UFT One and run it, or
- Run it from its existing ALM Test Lab set in the ALM client, on a machine
  whose desktop session is active and unlocked.

A support engineer can also drive a Test Lab run from the command line with
`--run-via-alm` (plus `--alm-test-lab-folder`, `--alm-test-set-name`,
`--alm-host`, `--uft-timeout`) so the run lands in the Phoenix report; the
expert `--allow-blockers` override is likewise command-line-only. None of
these appear in the console, by design. `--run-uft` — local UFT execution —
no longer exists at all: it fails the command if passed, on any path.

### Script Preservation *(both workflows)*

**VBS Preservation Mode** — how much of the original VBScript rides along in
the converted file: `python-only` (clean output, default),
`comment-block` (full original as a comment block on top), `interleave`
(each VBS line commented above its Python translation). Use `interleave`
during review-heavy phases — reviewers see source and translation together;
switch to `python-only` for final deliverables.

The two retention modes preserve different things, and the difference
matters when a test uses the ordinary UFT layout of driver statements first
and helper `Sub`s at the bottom. `comment-block` reproduces the original
file **in its original order**, in one block. `interleave` guarantees the
*pairing* — every retained VB line sits directly above the Python it
produced — but not the order: Phoenix hoists procedure definitions above
their call sites, so the retained lines follow the converted program's
order, not the source file's. A converted file whose lines were reordered
says so in a banner at the top. If a reviewer needs to read the script as
its author wrote it, give them `comment-block`.

---

## Step 5 — Analysis and Reports (Risk Analysis)

**Analysis Verdict** — the card at the top right of the step, where the
console states the answer. It reads **NOT RUN** before an analysis,
**ANALYZING** while one is running, then **GO** or **NO-GO**, and **STALE**
once an input changed after the analysis. An analysis that failed to finish
also shows NO-GO; in that case the card's "resolve or park" hint does not
apply — read the status line under the controls and the **CLI Output** box
instead. The sidebar's three cards say the same things in words: **Workflow**
(which migration flow you are on), **Approval State** (the verdict as a
sentence, "Analysis needs attention…" for a run that failed) and **Context**.
A card is shown only where it fits whole, so a short window shows fewer of
them; make the window taller to see the rest.

**Analysis Run ID** — folder name for this analysis under `out/` in the
directory Phoenix was launched from (the run folder is always there; the
Output Root does not move it). Started from the Start Menu shortcut, that is
your Windows profile folder. Auto-derived from domain/project/folder; override
it to keep engagements tidy (`WAVE1_ANALYSIS`).

Three things follow from this one field:

- **Step 6 converts into this same folder.** The conversion rewrites the
  folder's scan report set and Executive Summary with its own, so copy the
  analysis reports aside first if you need them as approval evidence. After a
  conversion, going **Back** to Step 5 shows the verdict the conversion
  started from, and **Next** returns to the conversion's reports on Step 6
  without re-analyzing. If the conversion was interrupted before writing its
  reports, Step 6 says so and warns that anything listed there may be from an
  earlier run. Once you reopen the console, Step 6 requires a fresh analysis
  before it will convert again.
- **On the ALM workflow the folder keeps a per-asset conversion journal.** A
  later conversion in the same folder carries forward — does not reconvert —
  every test an earlier conversion there uploaded and verified that is still
  Python on the server. To reconvert those tests, for example after relinking
  a library, enter a new Analysis Run ID, run the analysis, then convert.
  Ticking *Overwrite previous analysis outputs* does not clear the journal.
- **A custom ID is not remembered.** Reopen the console, or click a Step 2
  choice again (even the one already selected), and the field returns to the
  derived name. Re-enter your ID before using **Re-analyze Failed Assets**,
  resuming, or converting — otherwise you are working in a different run
  folder, and an ALM conversion there cannot skip assets an earlier run
  already converted.

**Overwrite previous analysis outputs in this run folder** — checked (the
default every time the console starts), the run first deletes these files from
the run folder: `scan_report.html`, `.md` and `.json`, `dependency_graph.json`,
`file_manifest.txt`, `analysis_cli_output.log`, `conversion_summary.json`,
`observability_metrics.json` and `migration_log.txt`. Unchecked, they are left
in place.

Because a conversion writes into this same folder, those last three are a
conversion's own record once one has run there — including `migration_log.txt`,
the run log that names every overwritten lock. Phoenix now keeps them: when the
last run in the folder was a conversion, only the analysis report set is
cleared, and the status line says so. To keep the whole conversion record
intact, copy the run folder somewhere safe or use a new Analysis Run ID before
re-analyzing.

This box has nothing to do with resuming. Resuming is offered separately: if an
interrupted run for the same Analysis Run ID with the same inputs is found (a
checkpoint still marked *running* whose command and arguments match), a
**Resume Previous Run** dialog asks whether to continue from the saved
checkpoint or start fresh. That dialog appears whether or not this box is
ticked, and choosing Resume makes the box moot — nothing is deleted. On the UFT
FileSystem workflow a resumed run then skips the files already scanned; an ALM
analysis always re-analyzes every asset, resumed or not. For a *conversion*
(Step 6) the dialog says No runs without the checkpoint, and that an
unfinished ALM conversion wave is continued either way: for an ALM conversion
the answer does not change what is converted. The box also does not apply to
**Re-analyze Failed Assets**, which always builds on the previous run.

**Run Folder In Use.** If another Phoenix process — a conversion, an analysis
or a restore, from a second console or a command prompt — is working in the
run folder, **Run Analysis** and **Convert Project** stop with *Run Folder In
Use*, which names that process. Nothing in the run folder is touched. Wait for
it to finish, or stop it, then try again.

**Analysis Depth (ALM only)** — `Standard` screens every test in parallel
without building it in UFT: a fast go/no-go filter. `Deep` opens and rebuilds
each test in UFT via the AOM (no upload), so a passing asset is one that
actually converts. Deep runs serially and is roughly 10x slower. **Only a
Deep analysis report carries the Technical Conversion Breakdown** — counts
measured by the same converter the real conversion runs (source/Python
lines, lines needing parentheses added for Python calls, VBScript intrinsic
replacements, descriptive-programming lines split static vs dynamic), per
asset and overall. Use it as the per-construct evidence behind a go
decision. The filesystem path's analysis has no depth choice and always
includes the breakdown.

**Out-of-scope test IDs** *(ALM)* — the parking field: ALM test IDs listed
here (comma-, space-, or newline-separated; text after `#` is ignored) leave
the scope entirely for this wave — not analyzed, not converted, not counted
as failures, left untouched in ALM. Fill it from the report's **Park the
Failed Assets** list (see *Parking failed assets* below).

**Out-of-scope tests** *(filesystem)* — the same parking idea for on-disk
tests: one entry per line (or comma-separated) — a test folder name, a
path, or a glob (e.g. `*Debug*`). Listed tests are skipped this wave and
their files left untouched on disk.

**Run Analysis** — executes the scan: discovers tests, inventories every
blocker/warning per file, builds the dependency graph, and produces the
readiness reports. **Always analyze before converting** — the conversion
step refuses to run without a current analysis (*Analysis Required*), and
refuses again if an input changed since.

What happens next depends on the verdict and the workflow:

- **Upgrade ALM Project.** A NO-GO blocks **Convert Project** with
  *Conversion Blocked — Unresolved Assets* until you resolve or park the
  failures and re-analyze.
- **UFT FileSystem.** The analysis is not a conversion gate. When it reports
  findings, **Run Conversion** asks *Proceed With Findings*, and if you
  continue every discovered test is converted: flagged constructs are
  converted best-effort and must be reviewed. A test is still refused if it is
  missing a linked function library, has an unresolvable cross-test callee, or
  produces Python that cannot be parsed — at any strictness — and, under
  `strict`, if its converted body carries a converter blocker. Refused tests
  are named in the conversion report.
- **Either workflow.** An empty scope stops the conversion with *Conversion
  Blocked — Nothing In Scope*.

After a run the console reports *Conversion Complete*, *Conversion Complete -
Approval On Hold* (the run finished, but the Executive Summary is not ready
for sign-off) or *Conversion Failed*, which shows the failure detail and the
process's exit code. On an ALM conversion that recovered from native crashes
of the conversion process, both *Conversion Complete* dialogs add how many
crashes were recovered, and how many of them the crash-recovery test switch
caused on purpose. When the run gives instructions of its own, *Conversion
Failed* shows them first and in full: a stopped conversion wave's message,
with its numbered restore commands, followed by the path of
`alm_wave_stop.json`; or, when the crash supervisor ends the conversion itself
— after a crash it could not recover from, when the conversion process ended
without a result, or when it refuses to start one — the supervisor's
explanation and next step. When the crash budget ran out and the wave was
rolled back, the dialog lists the outcome by status instead, with the
`process-crashed` asset among them.

The run folder is reused by every run with the same Run ID, so it can hold an
earlier run's reports. The console only shows reports the current run wrote:
if the conversion process ends without writing any — a crash nothing recovered
from, for instance — *Conversion Failed* says so (and, when the exit code is a
Windows exception, where Windows recorded the crash: Event Viewer, events 1000
and 1001), and the Run Outputs rows for the missing reports stay empty rather
than pointing at an earlier run's.

*Conversion Failed* ends with a question: *Collect diagnostics for Merito
support now? Phoenix saves a zip on this PC and opens its folder. Nothing is
sent.* **Yes** runs **Collect Diagnostics…** (see *The navigation row* above)
on the run that just failed, its question about crash dumps and test scripts
included; **No** only closes the dialog, and the button still works later.
One collect runs at a time: when you pressed **Collect Diagnostics…** during
the conversion and that collect is still running, **Yes** waits for it. That
collect's *Diagnostics Saved* (or *Diagnostics Not Collected*) then ends:
*Next, Phoenix collects the conversion that failed meanwhile: send the zip it
saves then, which includes the failure.* The failed run is collected straight
after, and the folder opens once its zip is saved.

A conversion you stopped with **Cancel** is not asked about: its *Conversion
Failed* ends with the line *To send details to Merito support, use Collect
Diagnostics (bottom left). Nothing is sent automatically.* instead. So does the
status line of a failed analysis, and of an analysis or conversion that could
not start, which have no dialog.

**Re-analyze Failed Assets** — after fixing source scripts, re-scans only
the assets that failed, under the same Analysis Run ID. Much faster than a
full re-scan of a large estate. Works on both migration paths and, for ALM,
at both analysis depths. The refreshed report still covers the whole scope:
the re-analyzed assets get their new result, and every asset that already
passed keeps the result from the previous analysis of that Run ID (on the ALM
path, the report states how many of each). "Overwrite previous analysis
outputs" does not apply to this action — a failed-only refresh builds on the
previous run.

If you park every remaining failed asset instead of fixing them (see *Parking
failed assets* below), this button becomes **Refresh Report (N parked)** the
next time Step 5 refreshes — when you leave and return to the step, for
example. The label does not change while you are pasting, but the button
always acts on the IDs currently in the field. There is nothing left to
re-measure, so the run just rewrites the report over the assets that remain in
scope; that needs no ALM work and is near-instant. Park only some of them and
the button stays **Re-analyze Failed Assets (M)** and re-measures the rest.

**Cancel** — stops the running analysis (the whole process tree). On the UFT
FileSystem workflow, re-running with the same Analysis Run ID offers to resume
and skips the files already scanned. An ALM analysis cannot pick up where it
stopped: re-running it analyzes every asset again, even if you choose Resume.

**Analysis Reports** — links to the run folder's artifacts: Scan
HTML/Markdown/JSON, Dependency Graph JSON, File Manifest and the raw CLI
Output Log, plus — on the Upgrade ALM Project workflow only — Conversion
Summary, Migration Log and Observability Metrics. Those last three stay blank
on a UFT FileSystem analysis, which does not write them. They are cleared when
a run starts and filled in when it finishes (and whenever you return to Step
5); they do not light up file by file. Start with **Scan HTML** — it carries
the go/no-go verdict and per-file drill-down.

**CLI Output** — the engine output for this analysis, shown when the analysis
finishes and kept on screen for troubleshooting.

### Version Control & Locks (in the analysis report)

Analysis performs no version-control writes. For **version-controlled** ALM
projects — at least one analysed asset reports version control enabled — the
scan report (and the markdown summary) carries a **Version Control & Locks**
section: counts plus who holds each checkout and entity lock, up to 100 rows
per list. Treat it as the pre-migration chase list — before running the
conversion, have those users check in or log off (or have an ALM admin
disconnect their sessions), and confirm the connected ALM user holds the
"Manage checkouts"-equivalent permission so stale checkouts can be undone. An
asset still **locked** at conversion time does not fail: it is converted and
overwritten, which is why the chase list matters — the holder loses whatever
they were editing.

On a project without version control the section is omitted. Locked assets are
still overwritten, and holders are named only per asset: in
`vc_state.locked_by` in that run folder's `conversion_summary.json`, as
`locked` warnings in `alm_preflight.json` when the conversion starts, and in
that asset's conversion note in the run log. Clear the project by agreement
before the window.

An asset whose pre-existing checkout cannot be undone (*Version control
blocked*) stops the conversion. No later asset is converted, and the assets
this run already uploaded are rolled back to VBScript. Once the permission is
in place, run **Convert Project** again with the same Analysis Run ID (after
reopening the console, re-run Analysis first). There is no failed-only
conversion, so every in-scope asset is converted again — with one exception:
an asset an earlier, finished conversion in that folder uploaded and verified
that is still Python on the server is skipped and counted on the Executive
Summary's **Carried Forward** card. If the rollback failed for any asset, the
conversion stops instead and names each such asset with its `restore --wave`
command; restore them first. A carried-forward
test still serves as a callee: its journal record carries the converted action
layout its callers need. Only a journal written by an earlier version of
Phoenix, before that layout was recorded, differs: a test that calls a test
carried forward from it is refused because the called test has no conversion
record in this run, which stops the run again. If that happens, enter a new
Analysis Run ID, run Analysis there, then convert — a fresh run folder carries
nothing forward, so caller and callee convert together. Use *Re-analyze Failed
Assets* to refresh the report.

### Parking failed assets

Not every failure is worth fixing in this wave. When you decide to defer some,
park them rather than converting them:

1. Open **Scan HTML** and find **Park the Failed Assets** (also on the Failed
   Assets drill-down page). It lists every failed asset that is *safe to
   park*, one ALM test ID per line with the asset name and its failure
   category as a `#` comment. Assets the failed-assets page marks *do not
   park* are withheld from the block, so it — and the **Copy all N failed
   IDs** count on it — can be shorter than the failed-asset count.
2. Press **Copy all N failed IDs**.
3. Paste into **Out-of-scope test IDs**, right here on Step 5 (Risk
   Analysis). The field keeps the IDs and ignores the comments, so you can
   read back what you are parking.
4. Press **Refresh Report (N parked)** / **Re-analyze Failed Assets**, or
   **Run Analysis** for a full re-run.

Parked assets leave the scope entirely — they are not analyzed, not converted,
not counted as failures, and are left untouched in ALM. If at least one asset
survives and nothing a survivor calls was parked, the refreshed report comes
back **go**. Parking cannot clear the gate in three shapes. The product
refuses the first two rather than letting you paste your way into them; the
third it does not refuse — it simply does not clear the gate:

- **Every in-scope asset failed.** Parking them all leaves 0 assets in scope,
  which the report badges *Nothing in scope — nothing to approve* (still
  **no-go**) and which the GUI hard-blocks with *Parking more assets cannot
  clear this: un-park at least one asset*. The report withholds the **Copy all
  N failed IDs** button here and says *All N in-scope assets failed — parking
  them cannot clear the gate*: fix the failure cause for at least one asset
  (see the **Recommended Remediation Queue**), or use the per-asset **Exclude**
  checkboxes on the failed-assets page to park only the subset you are
  deferring.
- **The no-go comes from the cross-test dependency graph.** Parking a failed
  test that a surviving test calls turns that call into an unresolved
  cross-test reference, so the refreshed report is **no-go** with 0 failed
  assets (*Hold conversion approval — cross-test dependency graph*). A
  shareable-action chain converts as one unit — park the whole chain or none of
  it, and restore the missing callee if you have already parked it.
- **A failed asset the report marks *do not park*.** Assets whose status is
  `shared-assets`, `rolled-back` or `rollback-failed` are withheld from the
  **Park the Failed Assets** block, and the failed-assets page shows *do not
  park* where the **Exclude** checkbox would be. Nothing refuses the paste
  here — it just does not clear the gate: those assets stay in scope, stay
  failed, so the refreshed report is still **no-go** and Step 6 stops with
  *Conversion Blocked — Unresolved Assets*. The cause has to be fixed instead.
  `rolled-back` had its scripts restored to VBScript, but its resource
  relations were not reverted (re-relate its original `.qfl` in ALM before
  running it from Test Lab): fix the asset that aborted the run — named in the
  run summary — and re-run the whole conversion. `rollback-failed` is still
  sitting converted in ALM and is the one asset a human must open.
  `shared-assets` means the test's actions are owned by another test, so it has
  nothing of its own to convert: re-create it in ALM so it owns its actions.
  Converting the owning test does not clear it — the ownership check runs at
  download time. Never park a `shared-assets` caller on its own — its owner
  converts in any run that proceeds, leaving a VBScript test loading Python
  actions, a chain that resolves but does not execute. If every failure is a
  *do not park* status, the block is not rendered at all.

This parking flow is **ALM-only**. The filesystem workflow's **Out-of-scope
tests** field takes tests out of the *conversion* wave — those tests are not
converted and their files are left untouched — but the analysis still
discovers and measures them, so their blockers still appear in the scan report
and the go/no-go verdict does not change. On the filesystem path, judge scope
from the conversion narrative (see
[usage.md](usage.md#taking-tests-out-of-scope-and-where-the-drops-are-reported)),
which names every test the wave dropped and the pattern that dropped it.

---

## Step 6 — Review and Run

**Review Command** — opens the exact `uft-migrate` *conversion* command your
selections produce, with a **Copy Command** button. A non-blank password never
appears (it travels via environment variable). Use it to hand a reviewed
configuration to a scheduler or CI job. It is not the analysis command — see
the note at the top of this guide.

**Run Conversion** / **Convert Project** — the primary button, labelled **Run
Conversion** on the UFT FileSystem workflow and **Convert Project** on the
Upgrade ALM Project workflow (the screen title changes to match). It executes
the full pipeline for your workflow: scan → convert → validate, and for ALM
upload → verify (with version-control checkout/check-in handled automatically
per asset). On the Upgrade ALM Project workflow the progress bar shows
per-asset progress read live from the engine; on UFT FileSystem it only shows
that the run is active, and the outcome appears when the run finishes.

An ALM conversion runs under a crash supervisor. If Windows ends the conversion
process (a native crash), the supervisor records the crash, cleans up and
starts the conversion again. From then on the progress label and the status
line under the controls show the supervisor's latest message — that the
conversion process crashed and on which asset, what was cleaned up, and the
relaunch, with the count of crashes the wave allows. They also show when an
unfinished conversion wave that had written no test was closed because the
selections changed, and when the conversion process could not be placed in
the supervisor's kill-on-close job, so closing the window may leave it
running. See
[advanced_troubleshooting.md](advanced_troubleshooting.md) §9.

**Cancel** — asks *Stop the running conversion?* first; on Yes it stops the
Phoenix command-line process immediately, and then any of its worker
processes still running. For an ALM conversion that process is the crash
supervisor: it goes first, and it takes the conversion process and its
children down with it, so nothing is relaunched. UFT (`UFT.exe`,
`QtpAutomationAgent.exe`) runs outside that process tree and may keep running;
close it, or end those processes, before using UFT on that machine — the next
conversion or Deep analysis closes it automatically. Cancel does not wait for
the asset in progress — that asset is interrupted mid-conversion. Nothing is
rolled back, no checkout is abandoned, and the end-of-run cache purge does not
happen. Assets converted before the cancel stay Python, so an ALM project is
left part Python and part VBScript. The *Conversion Failed* dialog that follows
does not ask to collect diagnostics, since you stopped the run; its last line
names **Collect Diagnostics…** for when you want them.

Treat a cancelled ALM run as an incident, not a pause: the test that was in
flight may be half-written. Do not let anyone run it until you have restarted
the conversion as below — before it converts anything, the restart compares
that test with the copy the conversion wave froze before changing it, and
restores it if they differ — or restored it yourself with `restore --wave`
(see [alm_safety.md](alm_safety.md) for the command).

Restarting afterwards differs by workflow:

- **UFT FileSystem.** Running **Run Conversion** again with the same Analysis
  Run ID offers **Resume Previous Run**. Resuming skips only phases that
  finished, such as the scan; the convert phase runs again for every test.
  Under Overwrite Policy `fail`, any test the interrupted run already wrote
  under the Output Root is then refused (*Target exists and overwrite policy
  is 'fail'*). So before re-running, delete what the interrupted run wrote, or
  choose `backup` or `overwrite` — changing the policy starts a fresh run
  instead of a resume. This does not apply under Convert Mode `in-place`,
  where `fail` acts as `backup`. **Re-analyze Failed Assets** only refreshes
  the analysis report; it converts nothing.
- **Upgrade ALM Project.** Run **Convert Project** again with the same
  Analysis Run ID (after reopening the console, re-run Analysis first) and the
  same selections, and answer *Resume Previous Run* either way: the conversion
  continues the interrupted conversion wave. If the asset that was in flight
  had started uploading, it is first compared with the wave's copy and
  restored from it if they differ. Assets an earlier run uploaded and verified
  that are still Python on the server are skipped and shown as **Carried
  Forward**; the asset that was in flight, and everything after it, is
  converted. Change a selection first, and a wave that has not written any
  test — cancelled before its first upload, say — is closed and a new one
  starts; a wave that has is refused, and *Conversion Failed* names what differs and
  the command that closes the wave (see [troubleshooting.md](troubleshooting.md)
  § *Native crashes and interrupted ALM conversions*). A carried-forward test
  still serves as a callee: its journal record carries the converted action
  layout its callers need. The one exception is a journal written by an earlier version of
  Phoenix, before that layout was recorded — a test that calls such a
  carried-forward test is refused because the called test has no conversion
  record in this run, and the run stops. If that happens, enter a **new**
  Analysis Run ID, run Analysis there, then convert — a fresh run folder
  carries nothing forward, so caller and callee convert together.

**Compare Converted Output…** — side-by-side diff viewer: original VBScript
on the left, converted Python on the right, changes shaded. Pick the
converted file; the original is paired automatically when possible. Use it
during review to show a QA owner exactly what happened to their test.

**Run Outputs** — links to this run's reports, filled in when the run
finishes. Both paths produce the **Executive Summary** (HTML / Markdown / JSON
— verdict, next steps, drill-downs). Beyond that the set depends on the path:

- **Filesystem runs**: Convert HTML/JSON and Validation HTML/JSON.
- **ALM runs**: Conversion Summary JSON (per-test results, including upload
  verification status), Observability Metrics JSON, and Pre-flight Report
  JSON. There are no Convert or Validation reports on the ALM path — that pair
  is filesystem-only. **Pre-flight Report JSON** (`alm_preflight.json`) matters
  most when the pre-flight gate aborts the run: no conversion report set is
  written in that case (the Executive Summary and `migration_log.txt` still
  are), and it is the report that lists every disqualified asset and its reason
  in one place (the run log records the same one line per asset). The Executive
  Summary and the console's **Conversion Failed** dialog each give only a count
  per reason code with one example.

  The ALM Executive Summary also carries a **Carried Forward** card. It reads
  0 unless this applies: assets an earlier conversion in the same run folder
  had already uploaded and verified, and that are still Python on the server,
  are skipped rather than converted again. When the count is not zero, a Next
  Steps note explains it, and tells two cases apart: assets an earlier
  *attempt of this same conversion* converted — before a crash relaunch, or
  before you resumed it — are this run's own work; assets an earlier *run*
  converted are not. These assets count as converted, not failed, and do
  not change the verdict. The reports show what their conversion recorded —
  findings, structure check, the shared libraries an earlier attempt of the
  same conversion replaced, and duration. A journal written by Phoenix 1.1.5
  or earlier recorded none of that: the summary and the scan report then say
  how many carried-forward assets the figures leave out. They carry the same
  exception as the restart above:
  if the journal record was written by an earlier version of Phoenix, a test
  that calls a carried-forward test is refused because the called test has no
  conversion record in this run, and the run stops. Enter a new Analysis Run
  ID, run Analysis there, and convert there if it happens.

  When the conversion process crashed natively during the run, a Next Steps
  note says how many times and what became of the crashes — how many were
  relaunched automatically, how many needed a manual re-run, and whether any
  struck after a payload write began — and names the conversion wave and the
  run folder's `crash_recovery\<wave>\` evidence folder. What crash recovery
  did around each affected asset is listed under **Crash Recovery Notes** on
  the assets page (`analysis_assets.html`) and in `scan_report.md`. Phoenix
  deletes the evidence folder itself once two later conversion waves in the
  same run folder that wrote to ALM have closed (a wave that wrote nothing,
  such as a launch the pre-flight gate refused, does not count), so copy it
  elsewhere if you must keep it. *Wrote nothing* means wrote no test — no
  test upload, restore or rollback: a wave can still have written shared
  libraries before its first test upload began, because library writes are
  not journaled. A memory dump is never copied into the evidence folder,
  because a dump may hold the ALM password — it stays in the Windows
  crash-dump folder that the attempt's `crash.json` names, where Windows keeps
  only its newest dumps. Crashes the crash-recovery test switch caused on
  purpose are counted separately, with a reminder to unset it. When the crash
  budget ran out, the note says why the wave was aborted and whether its
  rollback finished. Like Carried Forward, it does not change the verdict.
  The report's total time covers every attempt
  of the conversion, the crashed one included, but not the time between
  attempts, and says how many there were.

---

## Recommended first-engagement sequence

1. `uft-migrate doctor` on the migration machine (filesystem pilots can also
   tick Check Python Prerequisites).
2. Pilot first on a small representative set — **UFT FileSystem** against a
   copy of tests, or a dedicated pilot ALM project seeded with copies (ALM
   conversion is whole-project, so you cannot target a subset of the
   production project).
3. Step 3: Connect, pick domain/project, and tick the backup confirmation
   (Next is blocked without it). Leave the other defaults.
4. Step 5: **Run Analysis** — this is the read-only dry run (zero ALM
   writes). Read the Scan HTML, including the **Version Control & Locks**
   chase list on version-controlled projects; fix or map blockers; re-analyze
   failed assets; park anything you are deferring.
5. Step 6: **Convert Project** — ALM conversion always uploads in place,
   verified per test.
6. Once the pilot is at parity, run **Upgrade ALM Project** against the full
   project.
