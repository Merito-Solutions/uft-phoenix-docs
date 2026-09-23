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
| OpenText UFT One 26.1 | Required on the conversion machine for **both** conversion paths (filesystem and ALM — both are AOM-canonical) and on every machine that executes converted tests. Install the Python scripting component. |
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
   Declining ends setup without installing anything, with exit code `2`.
3. If a 1.0.x per-user installation is found, a **Previous version found** page
   lists what it found and offers to remove it, checked by default.
4. Choose the install folder. The default is
   `C:\Program Files (x86)\Merito\UFT Phoenix`.
5. Choose the optional tasks:

| Task | Default | Effect |
| --- | --- | --- |
| Create a Start Menu shortcut | **Checked** | Adds **Start Menu > Merito**, holding *Merito UFT Phoenix* (the GUI), *Merito UFT Phoenix Documentation* (opens `<install folder>\docs`) and *Uninstall Merito UFT Phoenix*. |
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
when you contact support. `LICENSE` and `THIRD-PARTY-NOTICES.txt` are installed
beside it.

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
| `/ACCEPTEULA` | Accepts the agreement in `LICENSE` without prompting; the acceptance is recorded in `<install folder>\eula_accepted.txt`. **Required for a silent install** — a silent run without it installs nothing and exits `2`. Deploying with it constitutes acceptance by your organization. |
| `/DIR="<path>"` | Install somewhere other than `C:\Program Files (x86)\Merito\UFT Phoenix`. |
| `/MERGETASKS="..."` | Task selection, merged with the defaults in the table above: name a task to select it, prefix it with `!` to clear it. The task names are `startmenu`, `desktopicon` and `addtopath`. |
| `/LOG="<path>"` | Write a verbose install log. Worth setting: the log is where a silent run reports the legacy 1.0.x installations it found but could not remove. |
| `/RUNDOCTOR` | Run the environment preflight after installing and record its findings. It does **not** change the installer's exit code; to gate a deployment on a ready machine, run doctor as a separate step (below). |
| `/REMOVELEGACY=no` | Leave any 1.0.x per-user installation in place. The default is `yes`, remove it. |

#### Exit codes

These are Inno Setup's codes, **not** the `0`/`1`/`2` set that 1.0.x returned.
Only `0` is success; every other code means the product is not installed.
Re-check any deployment that maps codes to success or failure before you roll
this out.

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | Setup failed to initialise. |
| `2` | Cancelled before the install started: the license was declined, the wizard was cancelled, or a silent run omitted `/ACCEPTEULA`. |
| `3` | Fatal error while preparing to install. |
| `4` | Fatal error during the install — including a failed post-install verification, which rolls the installation back. |
| `5` | Cancelled during the install, or *Abort* at an Abort-Retry-Ignore prompt. |
| `6` | Setup was forcibly terminated. |
| `7` | Setup determined it cannot proceed while preparing to install. |
| `8` | Setup determined it cannot proceed until the machine is restarted. Restart, then run it again — this is a code to retry, not a success. |

To gate a deployment on a ready machine rather than a successful copy, run the
environment check as its own step and read *its* exit code (`1` = at least one
check failed):

```
"C:\Program Files (x86)\Merito\UFT Phoenix\bin\uft-migrate.cmd" doctor
```

Use the full path — the process that ran the installer does not see the new
PATH entry — and run it from a writable folder, because `doctor` also checks
that it can write `out\` under the folder it starts in.

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
you launch Phoenix from.

## Where to launch Phoenix from

Phoenix writes each run into `out\<run id>` **under the directory it was
launched from**. `--output-root` moves converted output, not the run folder.

- Launch from a folder you can write to. The Start Menu shortcut starts in the
  profile folder of whoever launches it, so its run folders land in that
  user's `%USERPROFILE%\out` — each user of the machine gets their own run
  folders and their own saved Migration Console settings.
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
[troubleshooting.md](troubleshooting.md)), the ALM client registration, and
write access to `out\` under the folder you run it from, or to the folder
given with `--output-root`. Add `--alm-url`/`--username` to test a live ALM
login, with the password in the `UFT_MIGRATE_ALM_PASSWORD` environment
variable.

Two results are expected rather than problems: the ALM client row is a
`[WARN]` when the client is not installed, which is fine if you only convert
filesystem tests, and the offline-package row is skipped (`[ -- ]`) because it
only applies to machines that build packages.

`doctor` confirms that UFT One is registered for COM automation, and reports
the version it finds in the registry. It does not verify that the version is
26.1.

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

Uninstalling removes the install folder, the Start Menu and desktop shortcuts,
the machine PATH entry, the recorded license acceptance and the Apps &
Features entry. It does **not** remove your run output — `out\` folders live
under whatever folder each user launched Phoenix from — and it does not touch
UFT One or the ALM client. The Migration Console keeps its saved settings in
that same `out\` folder (`.uft-migrate-gui-cache.json`), including any ALM
password you entered, encrypted with Windows DPAPI for your account. Delete
those folders yourself when a machine is decommissioned.

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
