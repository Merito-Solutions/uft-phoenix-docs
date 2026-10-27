# Installation Guide (Windows)

Three things to settle before you start:

- **Installing requires administrator rights.** Merito UFT Phoenix installs
  per-machine, into `C:\Program Files (x86)\Merito\UFT Phoenix`, and setup
  will not continue without elevation. One install then serves every user of
  the machine.
- **The install is still fully offline.** Nothing is downloaded, and no Python
  already on the machine is used or needed.
- **Windows may warn before setup runs.** The installer does not carry a
  code signature, so an `.exe` that reaches the machine through a browser or
  email triggers SmartScreen's *Windows protected your PC*, and some endpoint
  protection suites quarantine it without asking. Verify the published SHA256
  before you run it — see [Verify the download](#verify-the-download).

Phoenix installs as the free edition. Its analysis runs at any size, for
assessment only, and it converts an ALM project, or a filesystem run, of up
to 100 test cases. A license file from Merito lifts the limit: see
[Installing a license](#installing-a-license) and
[licensing.md](licensing.md).

If version 1.0.x is already on the machine it was installed **per-user**, to a
different folder and under a different Apps & Features identity, so this
installer does not replace it. It detects it and offers to remove it; see
[Removing a 1.0.x per-user installation](#removing-a-10x-per-user-installation).

## Prerequisites

| Requirement | Notes |
| --- | --- |
| Administrator rights | Required. The install is per-machine: Program Files, `HKLM`, the machine PATH and All-Users shortcuts. |
| Windows 10/11 or Windows Server 2019+ | Phoenix is Windows-native; UFT/ALM COM automation requires Windows. |
| Python | **None.** The package installs and runs on its own sealed 32-bit Python 3.14.0 runtime. Nothing is downloaded, and no Python already on the machine is used. |
| OpenText UFT One 26.1 or 26.3 | Required on the conversion machine for **both** conversion paths (filesystem and ALM — both are AOM-canonical) and on every machine that executes converted tests. Install the Python scripting component, then add the IronPython files neither installer ships — `doctor` names them; see [troubleshooting.md](troubleshooting.md). |
| ALM Client registration | Required for ALM workflows only — install from your ALM server's Tools page (ALM Client Launcher / ALM Connectivity add-in). The supported servers are OpenText Application Quality Management (formerly Application Lifecycle Management) 24.1, 25.1 and 26.1; older versions are not supported, though backward compatibility may still carry one — see [supported_versions.md](supported_versions.md). Filesystem conversions work without it. |
| Internet access | **None**, for the install or for a conversion. |

ALM's OTA client and UFT's AOM are 32-bit COM servers, which is why the
runtime is 32-bit and why the default folder is the 32-bit
`Program Files (x86)` tree; `uft-migrate doctor` fails on a 64-bit
interpreter.

## Verify the download

The installer is unsigned, so Windows cannot tell you where it came from. The
SHA256 published with the download can:

```powershell
Get-FileHash .\MeritoUFTPhoenix-<version>-Setup.exe -Algorithm SHA256
```

Compare the hash with the one published alongside the download. If they
differ, do not run the file. `README-INSTALL.txt`, which ships beside the
installer, carries the same check plus the deployment notes for the team that
pushes it out.

## Install

1. Run `MeritoUFTPhoenix-<version>-Setup.exe` and accept the UAC prompt.
2. Read and accept the license agreement on the **License Agreement** page.
   Setup shows it on every install and upgrade. Declining ends setup without
   installing anything, with exit code `2`.
3. If a 1.0.x per-user installation is found, a **Previous version found** page
   lists what it found and offers to remove it, checked by default.
4. Choose the install folder. The default is
   `C:\Program Files (x86)\Merito\UFT Phoenix`.
5. Choose the optional tasks:

| Task | Default | Effect |
| --- | --- | --- |
| Create a Start Menu shortcut | **Checked** | Adds **Start Menu > Merito**, holding *Merito UFT Phoenix* (the GUI), *Merito UFT Phoenix Collect Diagnostics* (saves a support bundle for Merito support on this PC without opening the Migration Console, so it also works after the console was closed or when it will not start; nothing is sent), *Merito UFT Phoenix Documentation* (opens `<install folder>\docs`) and *Uninstall Merito UFT Phoenix*. |
| Create a desktop shortcut | Unchecked | Adds an All-Users desktop shortcut to the Migration Console. |
| Add Merito UFT Phoenix to the system PATH | **Checked** | Adds `<install folder>\bin` to the machine PATH, which puts `uft-migrate` and `uft-migrate-gui` on **new** terminals for every user. Terminals already open keep the old PATH. |

After copying, setup verifies what it installed by running the product's
`--version` on its own runtime. If that does not exit cleanly the install is
**rolled back** and setup tells you to re-download — a corrupt or partially
written payload is caught here rather than on the customer's first conversion. It also registers Merito UFT Phoenix in Apps & Features and records
who accepted the license, when (UTC), the product version and whether the
install was interactive or silent, in `<install folder>\eula_accepted.txt`.

`<install folder>\VERSION.txt` identifies the exact build: product version, the
sealed Python runtime, the commit the build sealed, the build date and a
SHA-256 for the sealed runtime and for each bundled component wheel. Quote it
when you contact support, or send a diagnostics bundle, which records it with
the rest of the environment (*Collect Diagnostics…* in the Migration Console,
or **Start Menu > Merito > Merito UFT Phoenix Collect Diagnostics**; see
[troubleshooting.md](troubleshooting.md) § *Collect diagnostics for Merito
support*). `LICENSE` and `THIRD-PARTY-NOTICES.txt` are installed beside it.

### Which version is installed

Start the Migration Console: the bottom-left corner of the dark panel on the
left, the one that lists the steps, reads *Version* and the version number on
every step, and an installed copy shows the number alone; the line under it
names the edition, *Free edition · up to 100 tests* or the license in use
(see [gui_field_guide.md](gui_field_guide.md) § *The version line*). Without
the console, `uft-migrate --version` prints the same number, and
`uft-migrate doctor` names it on its second line with the commit the build
sealed, and the edition in its `license` row (see [Verify the
environment](#verify-the-environment)). `VERSION.txt`, above, records the
exact build.

### Silent install

For SCCM, Intune or any unattended deployment. **Deploy it in the system
context** — ConfigMgr *Installation behavior = Install for system*, Intune
*Install behavior = System*. This is the opposite of the 1.0.x setting: that
release was per-user and had to run as the signed-in user. One per-machine
install now serves everyone on the machine.

```
MeritoUFTPhoenix-<version>-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /ACCEPTEULA
```

```
MeritoUFTPhoenix-<version>-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /ACCEPTEULA /DIR="D:\Apps\Merito\UFT Phoenix" /MERGETASKS="startmenu,addtopath,!desktopicon" /LOG="C:\Windows\Temp\phoenix-install.log" /RUNDOCTOR
```

| Switch | Effect |
| --- | --- |
| `/VERYSILENT` | No wizard and no progress window. |
| `/SUPPRESSMSGBOXES` | Suppress the message boxes a silent run can still raise. Without it, an error box can hang a deployment on a machine nobody is watching. |
| `/NORESTART` | Never restart the machine on setup's own initiative. Nothing this installer does is expected to need a restart — it unpacks files and sets the machine PATH — but pass it anyway so an unattended deployment can never reboot a machine out from under whoever is using it. |
| `/ACCEPTEULA` | Accepts the agreement in `LICENSE` without prompting; the acceptance is recorded in `<install folder>\eula_accepted.txt`. **Required for a silent install** — a silent run without it installs nothing and exits `2`. Deploying with it constitutes acceptance by your organization. Accepting it does not change a signed order form or statement of work with Merito; where they differ, the signed document prevails. |
| `/DIR="<path>"` | Install somewhere other than `C:\Program Files (x86)\Merito\UFT Phoenix`. |
| `/MERGETASKS="..."` | Task selection, merged with the defaults in the table above: name a task to select it, prefix it with `!` to clear it. The task names are `startmenu`, `desktopicon` and `addtopath`. |
| `/LOG="<path>"` | Write a verbose install log. Worth setting: the log is where a silent run reports the legacy 1.0.x installations it found but could not remove. |
| `/RUNDOCTOR` | Run the environment preflight after installing and record its findings. It does **not** change the installer's exit code; to gate a deployment on a ready machine, run doctor as a separate step (below). |
| `/REMOVELEGACY=no` | Leave any 1.0.x per-user installation in place. The default is `yes`, remove it. |
| `/LICENSEFILE="<path>"` | Install the Merito license file at `<path>` for every user of the machine, once the files are copied and the installed product has passed its self-test (see [Installing a license](#installing-a-license)). A relative path is read from the folder Setup is in. A path that names no file, or a file that is not there, stops Setup before anything is installed, with exit code `2`. A file Phoenix refuses leaves the product installed and makes Setup exit `10`. Write it with the `=`: `/LICENSEFILE "<path>"` is refused with exit code `2` too. |

#### Exit codes

These are Inno Setup's codes, **not** the `0`/`1`/`2` set that 1.0.x returned,
plus one of Phoenix's own, `10`. Only `0` is complete success; `10` means the
product is installed without its license file; every other code means the
product is not installed. Re-check any deployment that maps codes to success
or failure before you roll this out.

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | Setup failed to initialise. |
| `2` | Cancelled before the install started: the license agreement was declined, the wizard was cancelled, a silent run omitted `/ACCEPTEULA`, or `/LICENSEFILE` named no file, a file that is not there, or was written without its `=`. |
| `3` | Fatal error while preparing to install. |
| `4` | Fatal error during the install — including a failed post-install verification, which rolls the installation back. |
| `5` | Cancelled during the install, or *Abort* at an Abort-Retry-Ignore prompt. |
| `6` | Setup was forcibly terminated. |
| `7` | Setup determined it cannot proceed while preparing to install. |
| `8` | Setup determined it cannot proceed until the machine is restarted. Restart, then run it again — this is a code to retry, not a success. |
| `10` | The product is installed, but the license file named with `/LICENSEFILE` was not. If a license was installed earlier, it still applies. If not, the free edition is active. The log says why the file was not installed. Not worth a retry: the same file is refused again. Fix the file, then install it as [Installing a license](#installing-a-license) shows. |

To gate a deployment on a ready machine rather than a successful copy, run the
environment check as its own step and read *its* exit code (`1` = at least one
check failed):

```
"C:\Program Files (x86)\Merito\UFT Phoenix\bin\uft-migrate.cmd" doctor
```

Use the full path — the process that ran the installer does not see the new
PATH entry — and run it from a writable folder, because `doctor` also checks
that it can write `out\` under the folder it starts in.

### Installing a license

**Setup installs Phoenix even when the license file cannot be installed;
it then exits with code `10`.** Phoenix installs as the free edition: its
analysis runs at any size, and it converts an ALM project, or a filesystem
run, of up to 100 test cases ([licensing.md](licensing.md)). A license file
from Merito lifts the limit. Phoenix reads license files from two folders:
`<install folder>\licenses\`, for every user of the machine, and
`%LOCALAPPDATA%\Merito\UFT Phoenix\licenses\`, for one user. The Migration
Console has no license field.

To deploy a license with the product, name it with `/LICENSEFILE=`, and pass
`/LOG` so the log records what happened to it:

```
MeritoUFTPhoenix-<version>-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /ACCEPTEULA /LICENSEFILE="C:\Deploy\PHX-20261012-3F9A2C.license.json" /LOG="C:\Windows\Temp\phoenix-install.log"
```

Once the files are copied and the installed product has passed its
self-test, Setup installs the license for every user of the machine, with the
product's own `uft-migrate license install "<path>" --all-users`, and writes
that command's output to the log. It does this before `/RUNDOCTOR`, so
doctor's `license` row reports the outcome.

- A license that installs is in force at once, and the log says
  `license: installed for all users from` and the path.
- A file Phoenix refuses — changed or not issued by Merito, expired, or for a
  newer Phoenix — leaves the product installed and makes Setup exit `10`. The
  log says why, then *If a license was installed earlier, it still applies.
  If not, the free edition is active.* Without `/SUPPRESSMSGBOXES` a message
  box says the same. Do not retry: the same file is refused again. Fix the
  file, then install it as below.
- A path that names no file, or a file that is not there, and the switch
  written without its `=` (`/LICENSEFILE "<path>"`, `/LICENSEFILE:<path>`),
  stop Setup before anything is installed, with exit code `2`.

Give the full path to a file the account Setup runs as can read — under SCCM
or Intune, the computer's SYSTEM account — or a path relative to the folder
Setup is in, so a deployment package can carry the license file beside the
installer.

To install a license afterwards, or for one user only, run the command
yourself and read its exit code: `0` when the license is installed, `2` when
it refused the file and installed nothing. For every user, from a Command
Prompt opened with **Run as administrator**:

```
"C:\Program Files (x86)\Merito\UFT Phoenix\bin\uft-migrate.cmd" license install "C:\Deploy\PHX-20261012-3F9A2C.license.json" --all-users
```

Leave out `--all-users` to install it for yourself only, with no
administrator rights. Afterwards `uft-migrate license`, `doctor`'s `license`
row and the Migration Console's version line name the license. An upgrade
keeps installed licenses, and so does uninstalling; to remove one, run
`uft-migrate license remove <license id> --all-users` from an administrator
prompt ([usage.md](usage.md) § *Installing a license*).

### Removing a 1.0.x per-user installation

1.0.x installed to `%LOCALAPPDATA%\Programs\UFT Phoenix` under an `HKCU`
Apps & Features entry and a **UFT Phoenix** Start Menu group. Both the folder
and the Apps & Features identity have changed, so Windows treats this release
as a different product and an upgrade does not supersede it: left alone, the
machine carries two copies and two Start Menu groups.

Setup looks for 1.0.x in the current user's `HKCU`, in the other user hives
loaded on the machine, and by scanning
`C:\Users\*\AppData\Local\Programs\UFT Phoenix`. It offers to remove what it
finds, checked by default; a silent install removes it unless you pass
`/REMOVELEGACY=no`.

**On a shared machine it cannot finish the job for everyone.** It removes the
installing user's 1.0.x folder, `HKCU` entry, Start Menu group and user PATH
entry. Another user's copy is *reported* — on the wizard page and in the
install log — and left in place, because an elevated installer cannot safely
rewrite another user's PATH or delete their Start Menu group, and a half-done
removal leaves a broken PATH behind. Those users remove 1.0.x themselves from
their own **Settings > Apps > UFT Phoenix**.

### Upgrading

**An upgrade deletes before it copies, and a failed upgrade does not put the
old version back.** Setup clears `runtime\`, `bin\` and `docs\` under the
install folder before copying the new payload — otherwise a module dropped
between releases lingers inside the sealed runtime and shadows its
replacement, which presents as "the fix did not take". Setup's rollback does
not restore those three trees, so an upgrade that fails or is cancelled
part-way leaves neither version working, and the way out is to run the
installer again. Do not start one on a machine that is mid-engagement without
the time to see it finish.

With that understood: run the newer `MeritoUFTPhoenix-<version>-Setup.exe`
over the existing installation. It upgrades in place and keeps the Start Menu
entries, the PATH entry and the Apps & Features registration; uninstalling
first is neither necessary nor helpful. If you installed to a folder other
than the default, pass the same `/DIR` again — without it the upgrade installs
a second copy in the default location and leaves the first one behind.

Anything of your own under `runtime\`, `bin\` or `docs\` goes with the
upgrade. Keep nothing of your own there; run folders belong under the folder
you launch Phoenix from. Installed licenses are kept: they live in
`licenses\`, which an upgrade does not touch, and in each user's
`%LOCALAPPDATA%\Merito\UFT Phoenix\licenses\`.

**After upgrading, run the analysis again before converting a project in which
you parked tests** (*Out-of-scope test IDs* in the Migration Console,
`--alm-exclude-test-id` on the command line). This build reads, during the
analysis, which tests each parked test calls, so that a conversion never
turns into Python a test that a parked VBScript test still calls. An analysis
made by an earlier build did not read that, so a conversion judged on it
refuses each parked test with the reason `parked-references-unread` (*made by
an earlier Phoenix build*) and writes nothing. *Refresh Report* does not read
ALM and cannot clear this: press **Run Analysis**. A run folder whose analysis
parked nothing needs nothing.

## Where to launch Phoenix from

Phoenix writes each run into `out\<run id>` **under the directory it was
launched from**. `--output-root` moves converted output, not the run folder.

- Launch from a folder you can write to. The Start Menu shortcut starts in the
  profile folder of whoever launches it, so its run folders land in that
  user's `%USERPROFILE%\out` — each user of the machine gets their own run
  folders and their own saved Migration Console settings. The Collect
  Diagnostics shortcut starts there too, so it finds those runs and writes
  its bundle to `%USERPROFILE%\out\_support\` (or, when that `out\` does not
  exist yet, to `%LOCALAPPDATA%\Merito\UFT Phoenix\support\`).
- **Do not launch from the install folder.** `C:\Program Files (x86)` is not
  writable, so the run fails at once; and upgrading and uninstalling clear
  that folder.
- Do not launch from `C:\Windows\System32`, the directory an elevated prompt
  opens in. Run folders do not belong there and every run fails; see
  [troubleshooting.md](troubleshooting.md).

## Verify the environment

```
uft-migrate --version
uft-migrate doctor
```

`doctor` checks, in one pass: platform, Python version and bitness, pywin32,
the UFT One installation and its **IronPython runtime completeness** (some UFT
installs ship the Python engine missing DLLs or the standard library — doctor
names exactly what to copy where; see
[troubleshooting.md](troubleshooting.md)), the ALM client registration, the
license in use, and write access to `out\` under the folder you run it from,
or to the folder given with `--output-root`. Add `--alm-url`/`--username` to
test a live ALM login, with the password in the `UFT_MIGRATE_ALM_PASSWORD`
environment variable.

Its `license` row names the edition: *Free edition · up to 100 tests* with
*No license file is installed.*, or the license in use with its id, its expiry
and the ALM projects it covers. It never fails. It warns when, in the free
edition, an installed license file cannot be used, saying why; when the
license in use expires within 30 days; and when Phoenix's own license key is
damaged, which reinstalling Phoenix repairs. With a license in use, a file
that cannot be used does not make the row warn: the row names it after
*Other license files:* ([licensing.md](licensing.md) § *Checking the
edition*).

Two results are expected rather than problems: the ALM client row is a
`[WARN]` when the client is not installed, which is fine if you only convert
filesystem tests, and the offline-package row is skipped (`[ -- ]`) because it
only applies to machines that build packages.

`doctor` confirms that UFT One is registered for COM automation, and reports
the version it finds in the registry — on UFT One 26.3, for example,
`2026.3.0 build 298 (UFT One 26.3)`. It does not verify that the version is
26.1 or 26.3.

Run `doctor` on **every** machine involved in the migration — the machine
driving conversions *and* every host that will execute converted tests.

## Uninstall

Uninstalling needs administrator rights, like the install.

**Settings > Apps > Merito UFT Phoenix**, or **Start Menu > Merito > Uninstall
Merito UFT Phoenix**. For a scripted removal, use the `QuietUninstallString`
from the product's Apps & Features registry key — on 64-bit Windows,
`HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{844C27F4-84D9-4D20-BC97-63A5FFD6A8FF}_is1`,
because setup is a 32-bit process and writes to the 32-bit registry view. The
generated uninstaller accepts `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`.

Uninstalling removes the install folder, the Start Menu shortcuts (*Merito
UFT Phoenix Collect Diagnostics* among them) and the desktop shortcut, the
machine PATH entry, the recorded license acceptance and the Apps &
Features entry — except for installed license files. A license is a paid
entitlement, and uninstalling and reinstalling is a standard repair, so
`<install folder>\licenses\` is kept, and with it the install folder, while a
license file is in it; each user's `%LOCALAPPDATA%\Merito\UFT Phoenix\licenses\`
stays too. To remove a license, run
`uft-migrate license remove <license id> --all-users` from an administrator
prompt before you uninstall.

Uninstalling does **not** remove your run output — `out\` folders live
under whatever folder each user launched Phoenix from — and it does not touch
UFT One or the ALM client. The Migration Console keeps its saved settings in
that same `out\` folder (`.uft-migrate-gui-cache.json`), including any ALM
password you entered, encrypted with Windows DPAPI for your account, and the
support bundles *Collect Diagnostics…* and its shortcut wrote, in
`out\_support\`. Each user's `%LOCALAPPDATA%\Merito\UFT Phoenix\` folder stays
too: its `logs\` holds that user's diagnostics logs (the ALM password is
masked in them, see [alm_safety.md](alm_safety.md) § *Credentials*; Phoenix
itself deletes logs older than 30 days), and its `support\` the bundles
written when there was no `out\` folder — with their `…KEEP-PRIVATE-names.json`
maps of your real ALM names and any `…-EXTRAS-SENSITIVE.zip`, whose crash
dumps can hold the ALM password — and the collector output the Migration
Console keeps. Delete those folders yourself when a machine is decommissioned.

## Optional configuration

- **ALM connection values.** Server URL, user name, domain and project are
  entered in the Migration Console, or passed on the command line with
  `--alm-url`, `--username`, `--domain` and `--project`; supply the password
  through the `UFT_MIGRATE_ALM_PASSWORD` environment variable. The config file
  does not supply connection values — see [usage.md](usage.md).
- **Config file.** A `uft-migrate.json` in the folder you launch from is read
  automatically, with no `--config`. The installed product reads JSON only:
  `.yaml`/`.yml` config files need PyYAML, which the offline package does not
  include.
- **Extra UFT methods.** To have Phoenix recognise framework methods of your
  own, use *Custom UFT Methods* in the Migration Console, or
  `--custom-uft-method` (repeatable) / `custom_uft_methods` in the config file.
- **The UFT object model.** The full object model ships with the product; you
  do not need to supply one. A file at
  `resources\uft\uft_full_object_model.json` under the folder you launch from,
  or one named with `--uft-object-model` / `uft_object_model_path`,
  **replaces** the shipped model rather than extending it — so supply a
  complete registry or none at all. A file at that default path which parses to
  fewer than 100 members stops the run with an error.

These are read from the folder you launch Phoenix from, not from the install
folder, so they need no administrator rights to change.

## Installing from source

`MeritoUFTPhoenix-<version>-Setup.exe` is the supported way to install Merito
UFT Phoenix. `UFTPhoenix-<version>-win32-offline.zip`, which the build
produces beside it, is an internal build artifact — the payload the installer
is compiled from — not a second way to install.
