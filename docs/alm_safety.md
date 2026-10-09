# ALM Safety Playbook

Phoenix writes into your ALM project's **Test Plan** and **Resources** modules
when uploads are enabled, and into **Test Lab** only when the CLI
`--run-via-alm` lever is used. This playbook is the order of operations that
keeps a customer project safe, and **What a conversion writes** below is the
complete inventory of those writes.

## The safety model

1. **Nothing writes to ALM without explicit opt-in.** On the CLI, conversion
   runs are read-only unless `--upload` is set. In the GUI, **Analysis**
   (Step 5) is always the read-only dry run, and **Convert Project** (Step 6)
   on an ALM project always uploads — gated by the backup confirmation below.
2. **Dry-run first.** `--dry-run` (GUI: the **Analysis** step) screens the
   project for go/no-go with **zero ALM writes** and zero version-control
   writes. At the default *Standard* depth it downloads each test, converts
   the VBScript statically, and reports per asset the go/no-go status,
   converter blockers, unresolved cross-test references and
   missing/unresolvable resources — without launching UFT. At *Deep* depth
   (`--analysis-depth deep`, or the **Deep** radio on Step 5) it additionally
   AOM-builds each test locally in UFT to prove it converts, still uploading
   nothing. Neither depth prints a list of the files that would be uploaded
   or of the stale server files that would be deleted. On the CLI a dry run
   does not require `--confirm-alm-backup`; the GUI takes the backup
   confirmation earlier — the checkbox is on Step 3 and the ALM workflow will
   not advance past Step 3 without it, so Analysis (Step 5) is unreachable
   until it is ticked.
3. **Backup before the first real upload.** Live uploads require
   `--confirm-alm-backup`, which asserts you have backed up the ALM project
   database and repository (or hold a snapshot you can restore). Do not check
   the box to make the error go away — take the backup. The Migration Console
   does not remember the tick: every launch starts unticked and Step 3 asks
   for it again. Within one session it is not re-asked if you switch domain or
   project, so before continuing, confirm a backup exists for the project and
   the run you are about to start.
4. **Pre-flight gate: the whole project, or none of it.** A conversion is judged
   against a completed analysis **in its own run folder**. The GUI reuses the
   analysis run id automatically; on the CLI, pass the same `--run-id` to the
   analysis and to the conversion. Before Phoenix opens the connection it writes
   through, it checks every in-scope asset against that analysis, and if one
   asset is disqualified it refuses the run and writes nothing. An asset is
   disqualified when it has no analysis record, when its analysis failed, when
   it still has unresolved blockers, when a cross-test action reference is
   unresolved, ambiguous, self-referencing or part of a reference cycle, when a
   test it calls is itself disqualified, or when it was analyzed but this run's
   discovery no longer returns it. Every reason is written to
   `alm_preflight.json` in the run folder. A conversion started under a fresh
   run id has no analysis to be judged against, so every asset reads
   `not-analyzed` and the run is refused (`preflight-failed`). A rehearsal
   (`--upload --dry-run`) writes no report set and no executive summary of its
   own, so the analysis reports in that run folder — and the frozen
   `alm_analysis_results.json` the gate judges against — are left as they are.
   It republishes that folder's verdict and prints a `report_set` line
   explaining why it wrote no reports of its own — unless the rehearsal itself
   failed an in-scope asset, in which case it publishes no verdict at all; treat
   that absence, like any other missing verdict, as `no-go`.

   Discovery, which decides what the run covers, fails closed as well. It
   reads the whole Test Plan, and a fault while it lists a folder or reads a
   test stops the run (*ALM discovery failed: …*) instead of shrinking its
   scope; it then checks what it found against the project's own list of
   tests. A discovery that fails, whose process dies without an answer, or
   that comes back without assets the analysis covered, runs once more, a
   minute later, in a new process with a new ALM session
   (`alm-discovery-retried` in `migration_log.txt`). The gate judges the
   second answer, never a union of the two, so assets still missing are
   refused with nothing written. Only a refused Login is not retried, so a
   wrong password costs one failed login, not two.

   The CLI-only `--allow-partial-conversion` override converts the eligible
   assets anyway. It knowingly leaves the project half Python and half
   VBScript — which breaks cross-test action chains and poisons later
   conversion attempts — and the assets it skipped stay reported as
   `preflight-disqualified` failures. Do not use it on a production project.
   A foreign checkout is only a *warning* at this gate: the conversion undoes
   it during the upload, and only a checkout Phoenix lacks the permission to
   undo becomes `vc-blocked` and stops the run (item 8).
5. **Fail-closed blockers.** Tests whose conversion produced unresolved
   blockers are refused (status `blocked`) before any test payload,
   function-library resource or resource relation is written. On an upload
   run the asset is prepared before that point, as items 8 and 9 describe:
   Phoenix clears its lock where it can and, on a version-controlled project,
   undoes any pre-existing checkout and checks the asset out. A refused
   asset's checkout is abandoned, but the revoked lock and the undone
   checkout stand. During a conversion a `blocked` asset stops the whole run,
   and every asset already uploaded is rolled back (see **Rolling back**).

   The `--allow-blockers` override is CLI-only, exists for experts, and is
   recorded in the run notes; the GUI has no override — park deferred assets
   on Step 5 instead. The override waives ordinary converter blockers only.
   Two classes are non-overridable data-integrity stops and leave the asset
   `blocked` even with `--allow-blockers` set: converted Python that does not
   parse (it uploads clean, verifies clean, and is dead at run time), and
   cross-test shareable-action references that could not be retargeted to the
   converted callee layout (building one uploads a caller natively bound to
   the wrong callee). The unparseable-Python rule applies to the read-only
   analysis verdict too, so the override cannot talk a dry run into a green
   verdict over it either. These assets have to be remediated at source.
6. **Stale-file cleanup uses the server listing.** Before upload, Phoenix
   deletes only test-definition artifacts (`*.usr`, `Script.mts/.pts`,
   `Test.tsp`) that exist on the server but are not part of the new payload.
   After the save it removes any `Action*\Script.mts` still present, so UFT
   cannot fall back to a stale VBScript sidecar and execute nothing. Unknown
   server-side files are never touched.
7. **Every upload is verified.** After `Save`, Phoenix repairs the ALM asset
   model so UFT runs the converted `Script.pts`: the action script rows are
   re-pointed and any missing action owner is created. The test is then
   re-downloaded and compared byte-for-byte with the built payload. A payload
   file the server did not overwrite (most often an action's object
   repository) is deleted, uploaded again and compared again. A repair that
   fails (`asset-repair-failed`), or a mismatch that survives that retry
   (`upload-verify-failed`), stops the run and rolls it back — so the asset's
   **final** reported status is `rolled-back`, or `rollback-failed` where the
   restore did not verify. The original failure is recorded in
   `migration_log.txt` (`alm-conversion-aborted`) and in the run's per-asset
   journal. Do not run a `rollback-failed` test until you have inspected it
   in ALM.
8. **Version-controlled projects are handled conservatively.** Per asset,
   the conversion probes the session lock, **undoes** any pre-existing
   checkout — another user's or a stale one of your own; the server reverts
   to the latest checked-in version, which is exactly what gets converted —
   then checks out fresh, converts, uploads, verifies, and **checks in only
   after post-upload verification passes** (check-in comment "UFT Phoenix
   migration: AOM-canonical Python conversion (verified)"). Any failure
   after checkout **abandons the checkout**, so the server keeps its last
   checked-in version. Undoing another user's checkout requires the "Manage
   checkouts"-equivalent permission — without it that asset fails with report
   category *Version control blocked* (status `vc-blocked`), which stops the
   run.

   **Converted `.pfl` function libraries are handled differently, and more
   eagerly.** Each one is checked out, uploaded and checked in straight away
   (check-in comment "UFT Phoenix migration: Python function library (.pfl)
   content"), with the content read back from the server to prove it landed
   and one retry if it did not — all of this **before** the test that links
   it is built, uploaded or verified. A later failure of that test abandons
   only the test's checkout; the library keeps its new content and its new
   version. If a foreign checkout on a converted library cannot be undone,
   the asset fails with status `error`. The one exception is the shared
   helper runtime: a test that cannot write or reach it keeps its helper code
   pasted into its own scripts and converts as it otherwise would — unless a
   library it links already installs its helpers from the runtime on the
   server, in which case no pasted copy exists, the asset fails, and the run
   rolls back.
9. **A lock never fails a conversion — locked assets are overwritten.** ALM
   entity locks are session-scoped and routinely outlive the client that took
   them (a crashed or force-killed UFT/ALM client leaves its lock behind
   until the server times the session out). Nobody should be working in the
   project during a conversion window, so a lock found there is treated as
   something to get past, not a reason to stop.

   The pipeline gives a lock a short grace period (10 seconds) to clear on
   its own, tries to release it, and then **converts the asset either way**.
   That is safe because of how ALM enforces locks (measured against a live
   ALM server): a lock blocks entity *metadata* writes (`SetField`/`Post`)
   but does **not** block `ExtendedStorage.Save`, which is how a test's
   payload — `Script.pts`, `Test.tsp`, the `.usr` — is written. The
   conversion therefore overwrites the locked test's content and only skips
   the optional metadata write.

   Why never fail: a whole-project ALM conversion is **all or nothing**. A
   run that stops partway has to roll back, and a run whose rollback fails —
   or that is cancelled — leaves the project half Python and half VBScript,
   which breaks cross-test action chains (a Python caller cannot execute a
   VBScript callee) and poisons every later conversion attempt. One
   stranger's stale edit lock is not worth that.

   Release mechanics, because the obvious call does not work: `UnLockObject()`
   releases only *your own* lock — against another session's it returns
   cleanly and silently does nothing, so the pipeline never trusts it and
   re-probes after every attempt. Revoking a *foreign* lock means deleting
   its row from the project's `LOCKS` table through the OTA `Command`
   object, which **ALM disables by default**; where a site has enabled it for
   the migration account, the lock is removed outright and the run records
   `entity-lock-force-revoked` at warning level with the holder, machine,
   session id, lock time and last-active time. Where it is unavailable the
   run records `entity-lock-not-cleared-proceeding` instead and carries a
   per-asset note naming the holder — the conversion still completes. On a
   version-controlled project the analysis report's **Version Control &
   Locks** section remains the pre-migration chase list of who to get out of
   the project first.

   > **Operator note.** This overwrites the work of anyone still editing a
   > locked asset, and their ALM client may hold a stale copy afterwards.
   > Run conversions in an agreed window with the project empty, exactly as
   > the checkout policy assumes.
10. **Every test write is announced first, and a native crash is recovered.**
    Before an upload conversion makes the first write to a test's payload,
    restores a test, or starts a rollback, it writes a record of that to the
    run's journal (`resume/alm_test_results.ndjson`) and flushes it to disk.
    If the record cannot be written — a program that holds the file for a
    moment is waited out for about 8 seconds first — the write does not happen
    and the conversion stops (`journal-unwritable`). It also stops
    (`snapshot-failed`) before changing a test whose pre-conversion copy
    cannot be made in the run folder, on a full disk for example. So after any
    interruption the journal says exactly which tests may be half-written. The
    conversion runs under a crash supervisor: when Windows ends the conversion
    process (a native crash), the supervisor records the crash, keeps the
    evidence and starts the conversion again. Before the new attempt converts
    anything, it compares each test that may be half-written with the copy
    this conversion wave froze before changing it, and restores it from that
    copy if they differ. Three crashes on one test, six in the wave, or two in
    a row outside any test end automatic recovery: the wave is aborted and
    rolled back (see **Rolling back**). Function-library writes are not part of this:
    see [limitations.md](limitations.md) § *Crash recovery (ALM upload
    conversions)*, and [advanced_troubleshooting.md](advanced_troubleshooting.md)
    §9 for the details.

## What a conversion writes

This is the complete list, and it is longer than "the test". Everything here
happens only on a real upload conversion; analysis at either depth writes
nothing to ALM.

**Test Plan.** Each converted test's action scripts, actions and settings are
replaced in place, keeping the test's id, links and history. Phoenix then
rewrites that test's action asset rows — the script path on each row and the
owner name that has to match it — and creates an action owner where one is
missing, because UFT follows those rows to find the script it runs.

**Resources.** Two kinds of write, both in the Resources module:

- Every VBScript function library a converted test links becomes a Python
  `.pfl` function-library resource **in the same Resources folder**. If no
  resource of that name is there, one is created. If one is already there,
  **its content is replaced** — locks cleared, any foreign checkout undone,
  new content uploaded and checked in — after the prior copy is downloaded to
  `out/<RUN_ID>/alm_aom_work/alm_rollback/resources/<wave>/<test id>/`, a
  folder of the conversion wave's own. The first copy the wave saves of a
  library is kept; when a later attempt of the same wave — after a crash, say
  — replaces bytes that differ from it, those bytes are kept beside it in a
  `replaced_<UTC time>_…` folder. That first copy is kept by file name: when a
  test's libraries include two of the same name in different folders, the
  second one's copy is in a `replaced_…` folder beside the first one's, so go
  by the path each note names, never by the folder. The note "EXISTING
  CONTENT REPLACED — prior copy saved to <path>" names the copy of exactly
  the bytes that write replaced. That copy is best-effort: if the download
  fails the run records
  "EXISTING CONTENT REPLACED — no pre-conversion copy was kept" against that
  library, and the replaced content is gone. Phoenix refuses to write to a `.qfl`,
  `.vbs` or any other source asset.
- The VBScript compatibility helpers the converted Python needs live in one
  shared library, `PhoenixVBRuntime.pfl`, inside a Resources child folder
  named `UFT Phoenix` that the first conversion needing it creates. Helper
  entries are **merged** into that file: entries already there are kept. A
  file of that name that is not a Phoenix helper runtime is refused rather
  than overwritten, and a test that cannot reach the runtime keeps its helper
  code pasted into its own scripts instead — unless a library it links
  already installs its helpers from the runtime on the server, in which case
  there is no pasted copy to fall back to and the asset fails (item 8).

**Resource relations.** ALM delivers only *related* resources to a Test Lab
run, so the relations have to move with the content:

- The test's relation to each original `.qfl` is removed and a relation to
  the converted `.pfl` is added. This happens only after that test's upload
  has verified.
- A relation to `PhoenixVBRuntime.pfl` is added to every test that uses it.
  That one is written **before** the test is built, so nothing the build
  produces can end up depending on a library the test cannot reach.
- A relation is added for each shared object repository the test uses.

**Test Lab.** Nothing, unless the CLI `--run-via-alm` lever is used; see the
note under the engagement sequence below.

**Version control and locks.** On a version-controlled project each converted
test and each converted library is checked out and checked in, creating new
versions (items 8 and 9 above). Pre-existing checkouts are undone and entity
locks are revoked where the server permits it; every overwrite of that kind
is named in `migration_log.txt`.

**Ordering, and what it costs you.** The library and helper-runtime writes
above land after the blocker gate but **before** the test itself is built and
uploaded. Three checks still come after them — the UFT build, the carry-over
check and the structure check — so an asset that fails one of those can
already have changed a shared library. Neither the automatic rollback nor
`restore` undoes those writes. Each asset's record in `alm_aom_results.json`
lists what it wrote, under `alm_resource_writes`, and `migration_log.txt`
carries the same lines.

## Recommended first-engagement sequence

ALM conversion is whole-project (all or nothing). Pilot on a small,
dedicated ALM project seeded with copies before running the production
project:

```text
1. uft-migrate doctor                         # environment green?
2. ALM admin: project backup / snapshot       # required before the GUI advances past Step 3
3. GUI: Analysis on the project (Step 5)      # the read-only dry run: scan report,
                                              # blockers; on version-controlled projects,
                                              # the Version Control & Locks chase list
4. GUI: Convert Project (Step 6), backup confirmed
                                              # always uploads in place, verified per test
   → run first against a small pilot project (copies), not production
5. Run the converted pilot tests from Test Lab in the ALM client
                                              # your existing test sets
6. Once at parity, run Upgrade ALM Project against the full project
```

`--run-via-alm` is CLI support tooling, not a way to run one test. It acts
only inside an upload conversion, it runs every test that conversion
converted (never an asset skipped because an earlier run had already
converted it), and it writes to Test Lab: it creates the folder named by
`--alm-test-lab-folder` (default `Root\UFT Phoenix`), a test set named
`AOM Verification <timestamp>` unless `--alm-test-set-name` says otherwise,
one test instance per converted test, and then launches the runs.

## Interrupting and resuming

- **Cancel rolls nothing back.** The GUI's **Cancel** buttons stop the
  Phoenix command-line process and its worker processes; for a conversion
  that is the crash supervisor first, which takes the conversion process down
  with it. Assets converted before the cancel stay Python, so the project is
  left part converted until you run the conversion again or restore those
  assets. None of the failure handling runs either: no rollback, no abandoned
  checkout, no end-of-run cache clear.
- UFT (`UFT.exe`, `QtpAutomationAgent.exe`) runs outside that process tree
  and may keep running after a Cancel. Close it, or end those processes,
  before using UFT on that machine. The next conversion or Deep analysis
  closes it automatically.
- **Every upload conversion is a conversion wave.** A wave is one
  all-or-nothing conversion of the project, recorded in
  `resume/alm_test_results.ndjson` in the run folder as it goes. It lasts
  until the conversion finishes or the wave is rolled back, across every
  attempt it takes: a relaunch after a native crash, and a launch after a
  cancel, a stop or a crash recovery could not get past. A launch with the
  **same inputs** — the same command line apart from `--run-id`, `--resume`,
  `--failed-only` and the value of `--password`; in the console, the same
  selections — continues an unfinished wave, whether or not you choose to
  resume: in the GUI either answer in *Resume Previous Run*, on the CLI with or
  without `--resume`. A continued wave keeps the scope it started with and does
  not run the pre-flight gate again; it puts the gate report it started under
  back in `alm_preflight.json`. Its discovery must find that scope again: when
  tests the wave started with are missing, discovery runs once more, and if
  they are still missing the conversion stops (`wave-scope-changed`) before it
  writes anything. A transient fault while ALM lists the Test Plan can cause
  that, so run the conversion again first; check the scope, and ALM, only if
  the same tests are missing again. A discovery that fails outright stops the
  wave too (`discovery-failed`), with nothing written: run the same command
  again, which retries discovery and then checks any test a crash left
  half-written. A launch with **other inputs** closes an open
  wave that has not written any test yet — one cancelled before its first
  upload, for example — and starts a new one. Once the open wave has written a
  test, such a launch is refused, with the options that differ and the command
  that closes the wave; and no new wave starts while any wave in the run
  folder may still hold a half-written or half-restored test. A refusal writes
  nothing.
  [troubleshooting.md](troubleshooting.md) § *Native crashes and interrupted
  ALM conversions* covers each refusal, and how to close a wave you do not
  want to continue.
- **Before a continued wave converts anything**, it settles what the earlier
  attempt left. A test whose upload had started is compared with the copy this
  wave froze before changing it: identical, it is left alone; different, it is
  restored from that copy and verified (on a version-controlled project a
  checkout the dead process left is undone first). Either way it is then
  converted again. A test that a Phoenix 1.1.4 run was converting when it
  stopped is compared too, with the first copy the run folder kept of it,
  before a 1.1.5 conversion in the folder converts anything. Later, when the
  wave reaches a test that changed in ALM after the wave first saw it but
  before the wave wrote it — after a Cancel, say — it freezes its copy of that
  test again from what ALM holds and notes this on the test. If a test cannot
  be checked or restored, or anything else is not safe to guess, the
  conversion **stops**: it writes nothing more, leaves the report set alone,
  writes `alm_wave_stop.json` with the reason and the next steps, exits 2, and
  the wave stays open until you have taken them.
- **What is skipped.** Any later conversion under the **same run id** skips
  an asset only when the journal shows it was uploaded and verified, nothing
  recorded after that touched it again, **and** the server still holds its
  complete Python payload. That happens whether or not you choose to resume.
  On the CLI, `--resume` with identical arguments is accepted while the run is
  still marked running or its wave is unfinished, and refused (exit 2)
  otherwise. Everything else is converted again. A skipped asset is reported
  `ok` and counted under **Carried Forward** in the report's executive
  summary, so the report does not claim this run did that work. To force a full reconversion, run the
  analysis again under a new run id and convert in that same run folder — a
  conversion started in a run folder that holds no analysis is refused
  outright (item 4).
- ALM analysis keeps no per-asset checkpoint, so an interrupted analysis runs
  again in full. **Re-analyze Failed Assets** (`--failed-only`) needs a
  *completed* analysis in that run folder.
- A carried-forward test still serves as a callee. Its journal record holds
  the converted action layout that its callers are retargeted against, so a
  test that calls a shareable action in it is converted as usual in the same
  run. The one exception is a run folder whose journal an earlier version of
  Phoenix wrote, before that layout was recorded: a caller of a test carried
  forward from it is refused with "that callee has no conversion record in
  this run", and the run aborts and rolls back what it uploaded. Run the
  analysis again under a **new run id** and convert in that run folder, so
  caller and callee convert together, and keep the old run folder for its
  `alm_rollback` snapshots.
- If a cancel or a crash landed mid-upload, the test that was in flight has an
  `upload-started` record and none that it finished, and its action scripts
  may already have been deleted before the new payload was saved. Do not run
  that test until the conversion has been run again with the same inputs —
  which compares it with the wave's copy and restores it if needed, as above —
  or until you have restored it yourself with `uft-migrate restore … --wave`
  (see **Rolling back**).
- If the ALM session drops during a conversion, Phoenix reconnects in three
  places only — before retrying an asset that failed before its upload
  started (at most two retries), before an automatic rollback, and before
  crash recovery looks up a test that may be half-written. A drop *during* an
  upload is not retried: that asset fails, the run stops, and uploaded assets
  are rolled back. Analysis does not reconnect; re-run it.
  In `migration_log.txt`, `alm-session-reconnect` marks a dropped session
  Phoenix tried to restore and `alm-session-reconnect-failed` one it could
  not; a reconnect entry with no failure entry after it succeeded. After a
  failed reconnect, check every `rollback-failed` asset in ALM.

## Rolling back

Every conversion run keeps a per-test pre-conversion snapshot — and each
conversion wave its own copy of every test it changes — and on
version-controlled projects every conversion checks in a **new** version,
leaving the old one in place.

**Automatic rollback.** A real conversion stops at the first asset whose
status is anything other than `ok`, `skipped-api-test` or
`out-of-scope-test-type` — which includes `blocked`, `vc-blocked`,
`aom-build-failed`, `upload-verify-failed`, `asset-repair-failed`,
`not-found`, and `process-crashed` when the crash budget runs out. Assets
after it are recorded `not-attempted`. Everything the conversion wave wrote is
then restored, callers before callees: every asset it started uploading, in
this attempt or an earlier one, including assets an earlier attempt converted
that this one carried forward. Each is restored from the copy the wave froze
before changing it, never from an older copy, and on a version-controlled
project each restore is checked in as a new version. Every restore is verified
like an upload — downloaded again and compared byte for byte with the copy it
put back — with two exceptions: lock files (`*.lck`, such as
`Default.xls.lck`), which come and go from one download of a test to the next,
are left out, and `Download.xml` may come back with other content, though a
restore that does not put it back fails when the frozen copy has one. Those assets end up
reported `rolled-back` (the asset whose crashes ran the budget out keeps
`process-crashed`), or `rollback-failed` where the restore could not be
verified or the wave's copy is missing or damaged. Open every
`rollback-failed` asset in ALM; the `alm-rollback-asset` events in
`migration_log.txt` name them. While any of them is not restored, the wave
stays open, and the next conversion in that run folder stops and names each
one with its `restore --wave` command. The automatic rollback covers only the
wave's own writes: assets carried forward from an earlier, finished wave or
from Phoenix 1.1.4 or earlier stay converted, and a Cancel itself rolls
nothing back. It has the same limits as `restore` below.

Rollback paths, in order of preference:

1. **The `restore` subcommand** (primary): `uft-migrate restore` puts ALM
   tests back to their pre-conversion payloads from a prior run's snapshots.
   It works per test, not per run, so name every test to revert in one
   command:

   ```text
   uft-migrate restore --alm-url http://<server>:<port>/qcbin --username <user> --domain <domain> --project <project> --from-run <RUN_ID> --output-root <output-root> --alm-test-id <id> --alm-test-id <id> --confirm-alm-backup
   ```

   Set `UFT_MIGRATE_ALM_PASSWORD` in that shell first (see **Credentials**);
   `restore` reads it in place of `--password`.

   `--output-root` is the folder that holds the run folders. That is always
   `out` in the folder Phoenix was launched from; the Output Root set for a
   conversion never moves a run folder. Run `restore` from that same folder
   and the default, `out`, is right; from anywhere else, pass the full path
   of that `out` folder. Every `restore` command Phoenix prints already
   carries that full path. The restorable tests are the `test_<id>_source`
   folders under `<output-root>/<RUN_ID>/alm_aom_work/alm_rollback/`.
   Assets already reported `rolled-back` need nothing. `restore` is refused
   while another Phoenix process — a conversion, an analysis or another
   restore — is working in that run folder.

   The snapshot is the pre-upload download of a test, frozen once per run
   folder by the first run that builds that test — a real conversion **or a
   Deep analysis**. A Standard analysis and an `--upload --dry-run`
   rehearsal freeze nothing. It is never refreshed, not even by re-running
   the analysis under the same Analysis ID. Because the GUI converts into the
   analysis run folder, after a Deep analysis the snapshot holds what ALM had
   at *analysis* time; if tests may have changed in ALM since then, run the
   analysis again under a new Analysis ID before converting. The sibling
   `alm_aom_work/test_<id>_source/` is the transient staging tree (it is
   deleted and re-downloaded on every attempt, so a later attempt in the same
   run folder replaces the original VBScript with the converted payload); it
   is accepted only as a legacy fallback, and `restore` refuses any candidate
   holding `Script.pts` with no `Script.mts`, because that is conversion
   output rather than the pre-conversion original. It also refuses an
   incomplete copy — one without exactly one `.usr`, a `Test.tsp` and every
   local action script that `.usr` names — because a restore deletes the
   server's scripts before it saves the copy.

   **A test a conversion wave may have left half-written** — one whose write
   or restore the wave did not finish, or, in a wave that was aborted, any test
   it wrote that the rollback has not put back — is restored only from that
   wave's own copy: add `--wave <wave>`. The wave id is in the stop
   message, in `alm_wave_stop.json` and in each asset's `wave` in
   `alm_aom_results.json`; the commands Phoenix prints carry it already.
   Without `--wave`, `restore` refuses such a test, because the first-sight
   copy can be older than the wave and restoring it would undo changes made
   since; the refusal prints the `--wave` command for each such test, callers
   first. For the same reason `--wave` refuses a wave that has finished when a
   later wave has written the test since, and prints the command for the later
   wave's copy instead. With `--wave`, `restore` checks the copy under
   `alm_rollback/waves/<wave>/test_<id>/` against its manifest — an
   incomplete or changed copy is never restored — restores it, and records
   the restore in the run's journal before the first write and after the
   last, which is what lets the wave continue or close. Two forms write
   nothing to ALM and need no ALM arguments: `--accept-current-state` settles
   named tests you have inspected and accept as they are, and
   `--abandon-wave <wave>` closes a settled wave without converting further
   ([troubleshooting.md](troubleshooting.md) § *Native crashes and
   interrupted ALM conversions*).
2. **ALM version history** (version-controlled projects): each conversion is
   checked in as a new version, so the pre-conversion version remains in the
   test's version history — a first-class rollback path.
3. **Project snapshot/backup restore** by the ALM administrator.

**What a restore does not undo.** `restore`, and the automatic rollback and
crash recovery's restores, which call the same code, put back the test's files
and re-point its action script rows. They do **not** undo:

- **The test's resource relations.** A restored VBScript test stays related
  to the converted `.pfl` and to `PhoenixVBRuntime.pfl`, and not to its
  original `.qfl`. ALM delivers only related resources to Test Lab, so
  re-relate the original `.qfl` to the test in ALM before running it from
  Test Lab.
- **`.pfl` content the conversion replaced.** The prior copy is the one the
  asset's note "EXISTING CONTENT REPLACED — prior copy saved to <path>" names,
  under `out/<RUN_ID>/alm_aom_work/alm_rollback/resources/<wave>/<test id>/`,
  and has to be uploaded back by hand if you need it — unless the run recorded
  that no pre-conversion copy was kept, in which case there is nothing to put
  back. That copy holds the bytes THAT write replaced: when the wave wrote the
  same library more than once, the later copies hold the wave's own output.
  The library as it was before the wave is the one the scan report's
  shared-library section lists, per library, under *Pre-wave originals*: the
  copy the wave's first recorded write of that library kept. A library left
  out there has no copy the run can tie to that first write — an attempt
  interrupted while converting the test that wrote it first, for example,
  recorded nothing of what it wrote — so check it against your ALM backup. One
  case the run cannot detect: if you cancelled a conversion after it CREATED a
  new library, the next conversion's copy of that library holds the cancelled
  attempt's output, and the table may list it as the original although the
  library did not exist before the wave. Check the library's history in ALM
  before putting a listed copy back. A new
  wave deletes these copies for every older finished wave except the newest
  one that wrote a test (a wave that wrote no test, such as a launch the
  pre-flight gate refused, does not count; library writes are not recorded in
  the journal, so a wave that only replaced libraries does not count either,
  and its own copies stay until a newer wave that wrote a test has finished),
  so take what you need first.
- **The `PhoenixVBRuntime.pfl` resource, or its `UFT Phoenix` folder.**
- **Action owners the conversion created, or the owner names it changed.**
- **Test Lab test sets, instances and runs** created by `--run-via-alm`.

Open and run a restored test once before relying on it.

After any rollback to VBScript, clear the UFT client cache
(`%LOCALAPPDATA%\Temp\TD_80`) on every runner machine, or UFT may execute the
cached Python build. `restore` clears it nowhere.

On the machine running Phoenix the tool clears that cache itself, and closes
UFT to do it: a conversion or a Deep analysis force-closes UFT (`UFT.exe`,
`QtpAutomationAgent.exe`) without saving and then deletes that Windows user's
TD_80, so save your work in UFT before starting either. A conversion that
wrote to ALM clears it again at the end, including after an automatic
rollback. A Standard analysis clears it without closing UFT. Clearing is
best-effort, and each asset's notes record whether it succeeded. No other
machine is ever cleared.

## Credentials

- The GUI stores the ALM password DPAPI-encrypted (current Windows user) in
  its cache file; it is never written in plaintext.
- The GUI passes the password to the CLI through the
  `UFT_MIGRATE_ALM_PASSWORD` environment variable, never on a command line,
  so it does not appear in Task Manager or in the Review Command dialog. It
  is not written to disk, and the isolated build steps pass it to their own
  child processes the same way.
- For scripted CLI use, set `UFT_MIGRATE_ALM_PASSWORD` rather than passing
  `--password`. The analysis, conversion and `restore` commands all fall back
  to that variable, and a command line is visible to other processes on the
  machine.
- An installed package takes its ALM connection values only from the
  Migration Console (which keeps a saved password DPAPI-encrypted in its
  settings cache) and from the command-line flags. The password can also
  come from the `UFT_MIGRATE_ALM_PASSWORD` environment variable, and
  `doctor` also accepts `UFT_MIGRATE_ALM_URL` and `UFT_MIGRATE_ALM_USERNAME`.
- The diagnostics logs each Phoenix process keeps under
  `%LOCALAPPDATA%\Merito\UFT Phoenix\logs\` record what the process did: its
  steps, its errors with their tracebacks and the ALM client's error codes and
  messages, the server, domain, project and test names it worked on, and how
  its child processes ended. The ALM password is masked before a record is
  written: by its value when it is 6 characters or longer (a shorter value
  cannot be masked by value without garbling other text), and so is any value
  that follows a name such as `password`, `--password` or
  `UFT_MIGRATE_ALM_PASSWORD`. They stay on the machine, for the user who ran
  Phoenix, and are deleted after 30 days.
- A support bundle (*Collect Diagnostics…*, the Start Menu shortcut *Merito
  UFT Phoenix Collect Diagnostics*, `uft-migrate diagnostics collect`)
  never contains test scripts, data tables, object repositories, function
  libraries, the settings cache, `.env` files or memory dumps. A value that
  follows a name such as `password` or `--password` is masked in every file.
  Every file is also searched for the ALM password itself (4 characters or
  more), in each of its encodings, and a file that still holds it is left out —
  when the collector knows the password: *Collect Diagnostics…* passes it, and
  the collector decrypts, in memory only, the password the Migration Console
  saved under the output folder — which is how the Start Menu shortcut, started
  in the user's profile, has it. A command-line collect has a password that
  was not saved only when `UFT_MIGRATE_ALM_PASSWORD` is set; `MANIFEST.json`
  records when no password was available to search for. Server, domain,
  project, user, test, folder and library names are replaced by tokens unless
  `--keep-names` is passed; Phoenix's own words in its records (event and step
  names, exception types, its code lines, COM member names) stay as they are
  even where one equals such a name.
  Nothing is uploaded: the customer sends the zip. Crash dumps and failed
  tests' scripts, which can hold the password and test data, go only to a
  separate `…-EXTRAS-SENSITIVE.zip`, and only the kinds the operator agreed to.
