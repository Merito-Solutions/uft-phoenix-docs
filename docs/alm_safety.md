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
  `out/<RUN_ID>/alm_aom_work/alm_rollback/resources/<test id>/`. That copy is
  best-effort: if the download fails the run records "EXISTING CONTENT
  REPLACED — no pre-conversion copy was kept" against that library, and the
  replaced content is gone. Phoenix refuses to write to a `.qfl`, `.vbs` or
  any other source asset.
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
  Phoenix command-line process and its worker processes. Assets converted
  before the cancel stay Python, so the project is left part converted until
  you run the conversion again or restore those assets. None of the failure
  handling runs either: no rollback, no abandoned checkout, no end-of-run
  cache clear.
- UFT (`UFT.exe`, `QtpAutomationAgent.exe`) runs outside that process tree
  and may keep running after a Cancel. Close it, or end those processes,
  before using UFT on that machine. The next conversion or Deep analysis
  closes it automatically.
- A conversion records every asset as it goes, to
  `resume/alm_test_results.ndjson` in the run folder. Any later conversion
  under the **same run id** skips an asset only when that record shows it was
  uploaded and verified **and** the server still holds a Python-only payload
  for it. That happens whether or not you choose to resume — in the GUI,
  either answer in *Resume Previous Run*; on the CLI, `--resume` is accepted
  only for a run that was interrupted while still running, with identical
  arguments, and is refused after a run that failed or completed. Everything
  else is converted again. A skipped asset is reported `ok` and counted under
  **Carried Forward** in the report's executive summary, so the report does
  not claim this run did that work. To force a full reconversion, run the
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
- If a cancel landed mid-upload, the test that was in flight has a record
  that it started and none that it finished, and its action scripts may
  already have been deleted before the new payload was saved. On a
  version-controlled project the next run undoes that checkout and converts
  the last checked-in version. On a project without version control, restore
  that test first and only then run the conversion again under the same run
  id: a re-run takes whatever the server now holds as its source, which is
  the damaged copy.
- If the ALM session drops during a conversion, Phoenix reconnects in two
  places only — before retrying an asset that failed before its upload
  started (at most two retries), and before an automatic rollback. A drop
  *during* an upload is not retried: that asset fails, the run stops, and
  uploaded assets are rolled back. Analysis does not reconnect; re-run it.
  In `migration_log.txt`, `alm-session-reconnect` marks a dropped session
  Phoenix tried to restore and `alm-session-reconnect-failed` one it could
  not; a reconnect entry with no failure entry after it succeeded. After a
  failed reconnect, check every `rollback-failed` asset in ALM.

## Rolling back

Every conversion run keeps a per-test pre-conversion snapshot, and on
version-controlled projects every conversion checks in a **new** version,
leaving the old one in place.

**Automatic rollback.** A real conversion stops at the first asset whose
status is anything other than `ok`, `skipped-api-test` or
`out-of-scope-test-type` — which includes `blocked`, `vc-blocked`,
`aom-build-failed`, `upload-verify-failed`, `asset-repair-failed` and
`not-found`. Assets after it are recorded `not-attempted`. Every asset this
run had started uploading is then restored from its frozen snapshot, callers
before callees, and on a version-controlled project each restore is checked
in as a new version. Those assets end up reported `rolled-back`, or
`rollback-failed` where the restore could not be verified. Open every
`rollback-failed` asset in ALM; the `alm-rollback-asset` events in
`migration_log.txt` name them. The automatic rollback covers only what *this*
run uploaded: assets carried forward from an earlier run, and anything left
behind by a Cancel, stay converted. It has the same limits as `restore`
below.

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
   of that `out` folder. The restorable tests are the `test_<id>_source`
   folders under `<output-root>/<RUN_ID>/alm_aom_work/alm_rollback/`.
   Assets already reported `rolled-back` need nothing.

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
   output rather than the pre-conversion original.
2. **ALM version history** (version-controlled projects): each conversion is
   checked in as a new version, so the pre-conversion version remains in the
   test's version history — a first-class rollback path.
3. **Project snapshot/backup restore** by the ALM administrator.

**What a restore does not undo.** `restore`, and the automatic rollback that
calls the same code, put back the test's files and re-point its action script
rows. They do **not** undo:

- **The test's resource relations.** A restored VBScript test stays related
  to the converted `.pfl` and to `PhoenixVBRuntime.pfl`, and not to its
  original `.qfl`. ALM delivers only related resources to Test Lab, so
  re-relate the original `.qfl` to the test in ALM before running it from
  Test Lab.
- **`.pfl` content the conversion replaced.** The prior copy is under
  `out/<RUN_ID>/alm_aom_work/alm_rollback/resources/<test id>/` and has to be
  uploaded back by hand if you need it — unless the run recorded that no
  pre-conversion copy was kept, in which case there is nothing to put back.
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
