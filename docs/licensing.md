# Free Edition and Licensing

UFT Phoenix comes as a free edition. Its analysis runs at any size, and it
converts an ALM project, or the tests under the source folders of one
filesystem run, of up to 100 test cases. A larger conversion needs a license
from Merito. This guide explains how Phoenix counts test cases, what happens
over the limit, and how to install and check a license.

**Analysis is for assessment only.** Step 5 of the Migration Console, and
`scan`, `analyze` and `convert --alm --dry-run` on the command line, run on a
conversion of any size. When a conversion has more than 100 test cases, a
license that covers it must be installed before any of its tests are
converted or deployed. That includes a pilot of some of them, and any test a
Deep analysis built.

## What the free edition covers

| | Free edition | With a license |
| --- | --- | --- |
| Analysis (Step 5) | Any number of test cases, at Standard or Deep depth | The same |
| Deep analysis builds | Kept for a conversion of up to 100 test cases. Over 100, each build is deleted once it is checked and measured | Kept for a conversion within the license's limit |
| Conversion (Step 6) | Up to 100 test cases per ALM project or filesystem run | Up to the license's limit, or no limit |
| Support | Best effort | As your order form or statement of work says |

The free edition is for assessing and migrating your own organization's
tests. Migrating another organization's tests, as a service provider, needs a
separate written agreement with Merito, whatever the number of test cases.

Phoenix never contacts Merito: there is no online activation and no usage
reporting. See *Nothing leaves your network* below.

## How test cases are counted

The license agreement, `LICENSE` in the install folder, defines a test case:

> "Test Case" means a UFT One GUI test. In an ALM project, a Test Case
> is a test of type QUICKTEST_TEST, including an API test that ALM
> stores under that type; tests of other types are not Test Cases. On a
> file system, a Test Case is a folder that holds both a Test.tsp file
> and a .usr file. A test is a Test Case whether or not the Software
> can analyze or convert it, and whether or not it has already been
> converted to Python. Function libraries, object repositories,
> actions, and other resources are not Test Cases.

Phoenix applies that definition on both conversion paths:

- **A whole ALM project:** every test of type `QUICKTEST_TEST` under the
  Test Plan's *Subject* folder (the license agreement also counts any in
  ALM's *Unattached* folder). Manual, business-process and API
  (`SERVICE-TEST`) tests are other types, and do not count.
- **A folder of tests on disk:** every folder under the run's source folders
  that holds a `Test.tsp` file and a `.usr` file.

A test case counts:

- whether it passes or fails the analysis;
- whether it is still VBScript or already converted to Python;
- whether or not you parked or excluded it. The count is taken before
  *Out-of-scope test IDs* (`--alm-exclude-test-id`), *Out-of-scope tests*
  (`--exclude-test-path`), *Path Exclusions* (`--exclude`) and *Path
  Inclusions* (`--include`), so none of them lowers it;
- when it is an API test that ALM stores with the GUI type `QUICKTEST_TEST`.
  Phoenix tells such a test apart only once it has downloaded it, and never
  converts it, but it counts.

These never count:

- tests inside a folder named `Recycle Bin` or `.TrashCan`, at any level
  within the ALM project or below the run's source folders. They are the tests
  their owners deleted: Phoenix never analyzes or converts them either, on
  either path, and no option brings them back;
- a copy of a test case that Phoenix made itself: a backup it kept beside a
  converted test, or a converted copy in its output folder (the license
  agreement never counts one; Phoenix itself can still count a backup whose
  converted test was moved or deleted: see *Phoenix's count is a guide*
  below);
- function libraries, object repositories, actions, data tables and other
  files. A test case is the test, whatever it links to or calls.

On disk, tests under folders named `out`, `.git` or `__pycache__`, which a
filesystem run's default *Path Exclusions* leave out, count only when the
run's *Path Inclusions* and *Path Exclusions* keep them, for example because
your own *Path Exclusions* replaced those defaults. A test they keep counts
even when you park it with *Out-of-scope tests*. The license agreement counts
a test in one of those folders below the run's source folders only if the run
converts it, so a test you park there can make Phoenix's count higher than
the agreement's.

**What one count covers.** The license agreement calls the set of test cases
one run of Phoenix covers a *Conversion*: every test case in one ALM project,
including any in ALM's *Unattached* folder, or under all the source folders
of one filesystem run, counted before any test is parked, excluded or
filtered out. Phoenix converts an ALM project whole, and counts it whole. The
agreement does not allow dividing a conversion, or otherwise working around a
test-case limit, and whatever the reason, two rules apply (section 2.g):

- test cases you copy or move out of an ALM project or folder still count
  toward any conversion of that project or folder;
- when you run Phoenix separately on two or more folders that share a parent
  folder, the test cases in all of them count as one conversion of that
  parent folder.

**Phoenix's count is a guide.** Phoenix counts test cases to help you stay
within your limit, but the agreement's definitions govern, and Phoenix
letting a conversion run does not mean the agreement allows it (section 1.g).
Where they can differ:

- Phoenix does not count tests in ALM's *Unattached* folder, which the
  agreement counts;
- on a folder of tests, Phoenix accepts any valid license, even one that
  names ALM projects, which the agreement limits to those projects' tests
  (see *Getting a license* below);
- Phoenix can count a test the agreement does not, such as a backup it made
  whose converted test was moved or deleted. You may delete that backup, or
  move it out of the run's source folders, and run Phoenix again; it may be
  your only copy of the original VBScript test, so delete it only if you
  have another.

**Merito may ask for the count.** No more than once in any twelve months,
unless it has reasonable grounds to believe a limit was exceeded, Merito may
ask you to confirm in writing the test-case count of a conversion you
converted and, for a filesystem run under a license that names ALM projects,
which ALM project its tests came from. You answer within 30 days, in writing,
signed by someone authorized to bind your organization, with reasonable
supporting records, such as that conversion's scoping summary. Not answering,
or giving a materially inaccurate count or source, is a breach of the
agreement (section 2, its last paragraph).

**The limit.** Up to 100 test cases convert in the free edition, so 100 is
allowed. 101 or more need a license.

**The count is not *Assets in Scope*.** That figure in the analysis report
leaves out the tests you parked or excluded and the API tests Phoenix set
apart. The test-case count includes them, so it can be higher.

## Over the limit

### At Step 5

- The analysis runs to the end at any size, and its verdict does not change.
  GO or NO-GO says whether the tests are fit to convert, not whether the free
  edition may convert them, so a clean conversion of 150 test cases still
  reads **GO**. The verdict card's line reads *Scoping required: 150 test
  cases, over the free edition limit of 100.*
- The status line, the analysis report (under *Scoping required*) and the
  command-line output carry the over-limit notice, quoted below.
  `scan_report.json` carries the same figures in its `licensing` block.
- A Deep analysis keeps every measurement, the Technical Conversion Breakdown
  included, but deletes each test's converted build once it is checked and
  measured. *Compare Converted Output…* then has no build to open.
- The step header card names the count, and its button **Scope this
  conversion with Merito** opens Merito's consultation request form.
- **Next** stops with *Scoping Required*, so Step 6 cannot be opened. See
  [gui_field_guide.md](gui_field_guide.md) § *Over the free-edition limit*.

The over-limit notice begins:

> This conversion includes 150 test cases, by UFT Phoenix's count. The free
> edition of UFT Phoenix covers conversions of up to 100 test cases. Until a
> UFT Phoenix license covers this conversion, use these results for
> assessment only, and don't convert or deploy any of its tests, including
> tests built during analysis.

It then gives the address of Merito's consultation request form, points at
the scoping summary, and ends by saying that it summarizes section 1.d of the
license agreement, which governs. Over a license's own limit it names the
license file's licensee and limit, and the ALM projects the license names, if
it names any: *The UFT Phoenix License File for Contoso Ltd covers
conversions of up to 500 test cases in ALM projects SALES/CRM and
SALES/ERP.*

### At Step 6 and on the command line

Every conversion counts the test cases again when it starts, from ALM or from
the disk, and never takes the count from the analysis reports. Over the
limit, with no installed license that covers the conversion, it stops before
it converts anything:

- **Run Conversion** and **Convert Project** refuse, with *Conversion Blocked
  — Scoping Required*;
- `convert` and `run` on a folder of tests refuse;
- every `convert --alm` and `run --alm` that is not the analysis refuses: the
  upload, the build-only run without `--upload`, and the `--upload --dry-run`
  rehearsal.

A refused command ends with status `license-limit`: it prints
`"status": "license-limit"` and exits 2. Its `message` begins *Conversion
refused. No test was converted, backed up or changed.* and says what to do,
and its `licensing` block gives the count and the limit that applied. A
refused run converts no test, backs none up and changes none of your tests,
and it writes nothing to ALM; an ALM refusal leaves the analysis in the run
folder as it was. Phoenix still updates its own files, its run records and
its logs; on ALM it also signs in and reads the Test Plan, to count the test
cases. On a folder of tests, a
conversion that is refused only once it has started — its source folders
gained tests since it was checked, or since the interrupted conversion it
resumes started, or a license lapsed — has already rescanned them: its scan
reports and scoping summary are new, and the run can no longer be resumed.
See [usage.md](usage.md) § *The free-edition limit*.

### What is never blocked

- The analysis, at any size.
- Finishing a conversion that is already under way. On ALM: a conversion that
  continues an unfinished conversion wave (the relaunch after a crash, the
  relaunch after the conversion process restarted itself to free memory —
  [advanced_troubleshooting.md](advanced_troubleshooting.md) §9 — or the same
  command run again) and its rollback, whichever version of Phoenix started it.
  On disk: resuming an interrupted conversion, unless its source folders now
  hold more test cases than when it started; one an earlier version of Phoenix
  started always finishes. A resumed conversion refused for the tests it gained
  cannot be resumed again: run it again, without `--resume`, once the count is
  within the limit that applies — remove those tests, or install a license that
  covers the conversion.
- `uft-migrate restore`, including for tests an earlier version of Phoenix
  converted.
- `uft-migrate doctor`, `license`, `validate`, `summarize` and `diagnostics`.

## The scoping summary and the consultation request form

Every analysis writes a scoping summary into its run folder:
`scoping_summary.html`, with the same figures in `scoping_summary.json`. It
holds counts and summary figures, with no names, paths, identifiers or test
code:

- the test cases counted, the limit, the edition, and the tests by type;
- how many are in scope, parked, excluded by a path pattern or in a
  deleted-test folder;
- how many passed the analysis, and the blockers by category;
- the cross-test call chains, and the number of function libraries.

It holds no code, no test or folder names, no file paths, no run id, no
licensee, and no ALM server, domain or project names. Open it with **Open
Scoping Summary** on Step 5, or from the run folder; the analysis report links
it too.

To have a conversion over your edition's limit scoped, request a consultation
on Merito's consultation request form:

<https://www.merito.com/solutions/uft-phoenix/scope?utm_source=other&utm_medium=referral&utm_campaign=uft-phoenix-product-links-5100003>

Sending Merito anything is your choice, and you are not obliged to send
anything. Read the scoping summary before you send it. If you send it, or any
other output of Phoenix, so that Merito can scope or quote a license or
services, Merito keeps it confidential for three years after it receives it
(a trade secret for as long as it remains one), uses it only for that scoping
and quoting, and deletes it within 30 days after you ask (license agreement,
section 3.d). Merito may keep copies in routine backups until they are
overwritten, copies the law or a legal hold requires it to keep, and the
quotes, orders and records it creates, including the test-case counts and
other figures in them; what it keeps stays under the same terms. These terms
do not cover information that is or becomes public through no fault of
Merito, that Merito already knew or develops independently, or that it
receives from a third party without a duty of confidentiality, and Merito may
disclose what you sent where the law requires it, after telling you promptly
where the law allows. The other
reports in a run folder can hold test names, paths and lines of your test
code: send them only if you mean to.

## Getting a license

Merito's sales team arranges a license under an order form or statement of
work, and Merito sends you the license file, named
`<license id>.license.json`. A license states:

- the licensee: the organization it is issued to;
- the test-case limit: a number, or no limit;
- the expiry date, or none;
- optionally, the ALM projects it covers, each as a server, domain and
  project.

A license that names ALM projects lifts the limit for those projects only.
Each server is named the way the license lists it, so a server you reach by
another name, such as a short name or an alias, is another server to Phoenix:
ask Merito to add the name you use. Phoenix cannot tell which ALM project a
folder of tests came from, so a filesystem run accepts any valid license; the
license agreement still limits a license that names ALM projects to those
projects' tests, on disk too, and does not allow using it to convert tests
from any other ALM project (sections 1.c and 2.i).

Merito signs every license file. Phoenix checks the signature on your
machine, with a public key built into Phoenix, and a file whose details were
changed fails that check, so keep the file exactly as Merito sent it.

## Installing a license

The Migration Console has no license field: install a license from the
command line or with the installer. Phoenix reads license files from two
folders:

- **for you only:** `%LOCALAPPDATA%\Merito\UFT Phoenix\licenses\`, which needs
  no administrator rights;
- **for every user of the PC:** `<install folder>\licenses\`, which needs an
  administrator prompt.

When more than one installed license applies, the one that allows the most is
used: no limit before a limit, a higher limit before a lower one, then the
later expiry.

### With the command line

```
uft-migrate license install "C:\Licenses\PHX-20261012-3F9A2C.license.json"
uft-migrate license install "C:\Licenses\PHX-20261012-3F9A2C.license.json" --all-users
```

The first command installs the license for you only. The second, run from a
Command Prompt opened with **Run as administrator**, installs it for every
user of the PC. Either checks the file's signature and its expiry, copies it
into the license folder as `<license id>.license.json`, and prints what it
installed and the edition now in use. It exits **0** when the license is
installed, or was already, and **2** when it refused the file and installed
nothing: a file that is not a UFT Phoenix license, a file Merito did not issue
or that was changed, a license that has already expired, a file that needs a
newer version of Phoenix, or `--all-users` without administrator rights.

`uft-migrate license` shows the edition in use, the license behind it, and
why any other license file is not used.
`uft-migrate license remove <license id>` removes a license, with
`--all-users` for one installed for every user. Like `doctor`, these commands
create no run folder. See [usage.md](usage.md) § *Installing a license*.

Nothing needs restarting, and nothing needs analyzing again. Every conversion
reads the installed licenses when it starts. The Migration Console reads them
again when you enter Step 5, at **Next**, at **Run Conversion** or **Convert
Project**, and after a refusal, so its edition line and its over-limit checks
follow at once. Only the reports an analysis already wrote keep the notice
they were written with, until the next analysis.

### With the installer

**Setup installs Phoenix even when the license file cannot be installed.**
For an unattended deployment, name the license file with
`/LICENSEFILE="<path>"`, and pass `/LOG` too:

```
MeritoUFTPhoenix-<version>-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /ACCEPTEULA /LICENSEFILE="C:\Deploy\PHX-20261012-3F9A2C.license.json" /LOG="C:\Windows\Temp\phoenix-install.log"
```

Setup installs the license for every user of the PC once the files are copied
and the installed product has passed its self-test. A relative path is read
from the folder Setup itself is in, so a deployment package can carry the
license file beside the installer.

- A switch that names no file, or a file that is not there, stops Setup before
  anything is installed, with exit code `2`. So does the switch written
  without its `=`, as in `/LICENSEFILE "<path>"`.
- A file Phoenix refuses leaves Phoenix installed, and Setup exits with code
  `10`. The log says why the file was not installed: *If a license was
  installed earlier, it still applies. If not, the free edition is active.*
  Code 10 is not worth a retry, because the same file is refused again. Fix
  the file, then run `uft-migrate license install "<file>" --all-users`.

See [install.md](install.md) § *Installing a license*.

### Upgrades and uninstall

An upgrade keeps installed licenses, in both folders, and so does
uninstalling: a license is a paid entitlement, and uninstalling and
reinstalling is a standard repair. To remove a license, run
`uft-migrate license remove <license id> --all-users` from an administrator
prompt before you uninstall.

## Checking the edition

- **Migration Console:** the version line, bottom left on every step, names
  the edition on its second line: *Free edition · up to 100 tests*, or
  *Licensed to* and the licensee, then the limit, then the ALM projects the
  license names, if it names any (two at most there; its tooltip lists them
  all). `uft-migrate license`, `doctor` and the reports always list them all.
  On the Upgrade ALM Project
  workflow it is the edition for the project you chose. See
  [gui_field_guide.md](gui_field_guide.md) § *The version line*.
- **`uft-migrate license`:** the edition in use, and every license file
  Phoenix found, with the reason each unused one is not used.
- **`uft-migrate doctor`:** its `license` row names the edition, and for a
  license its id, its expiry and the ALM projects it covers. In the free
  edition it reads `[WARN]` when an installed license file cannot be used,
  for example because it expired or was changed, and says why. With a
  license in use, such a file does not make the row warn: the row names it
  after *Other license files:*. The row reads `[WARN]` when the license in
  use expires within 30 days; its `fix:` line says what to do and what
  applies after that date. It also warns, and asks you to reinstall Phoenix,
  if Phoenix's own license key is damaged. The free edition never fails
  `doctor`.
- **Reports:** the analysis report and the executive summary name the edition.
  `scan_report.json`, and the output of `scan`, `analyze`, `convert` and
  `run`, carry it in their `licensing` block.

## When a license expires or does not apply

A license with an expiry date applies through the end of that day. After
that, and for any ALM project a license does not name, the free edition
applies again:

- the analysis still runs at any size;
- a conversion of more than 100 test cases is refused;
- a conversion already under way can still be finished, rolled back or
  restored.

When no other installed license applies, `uft-migrate license`, `doctor`,
the console's *Scoping Required* dialogs and a refused conversion say so in
these words:

> The UFT Phoenix License File for Contoso Ltd expired on 2026-09-30. The
> free edition now applies, covering conversions of up to 100 test cases. If
> this differs from your order with Merito, contact Merito at
> \<consultation request form\>.

Ask your Merito contact for a renewed license file. It has a license id of
its own: install it the same way, and, if you like, remove the old one with
`uft-migrate license remove` and the old license's id. An expired file is
ignored.

## Nothing leaves your network

- Phoenix connects only to the ALM server and the UFT One installation you
  point it at.
- Phoenix checks a license file on your machine, with a public key built into
  Phoenix. There is no online activation and no usage reporting: nothing is
  sent to Merito.
- The scoping summary stays on your machine until you send it.
- The links to Merito open in your browser only when you click them: the
  consultation request form in the over-limit notice, in the reports and on
  **Scope this conversion with Merito**, and the console's **Get Quote** and
  **Book a migration services consultation**. Each address carries a campaign
  tag that tells Merito the visit came from UFT Phoenix, and no test names,
  counts or other data about your tests or your environment. Following the
  link a conversion over its limit shows does tell Merito that a conversion
  was over its limit. Your visit to Merito's website is governed by Merito's
  Privacy Policy,
  <https://www.merito.com/legal-docs/commercial-privacy-policy.pdf>, and its
  Cookie Policy, <https://www.merito.com/legal/cookie-policy> (license
  agreement, section 3.c).
- A support bundle replaces the licensee's name with a token, `licensee-1`,
  as it does your ALM names. See [troubleshooting.md](troubleshooting.md)
  § *Collect diagnostics for Merito support*. If you send Merito a bundle, or
  other information for support, Merito keeps it confidential for three
  years (a trade secret for as long as it remains one), uses it only to
  provide that support and deletes it within 30 days after you ask. It may
  keep backup copies, copies the law or a legal hold requires and its own
  support records under the same terms, and the exceptions that apply to a
  scoping summary apply here too (section 6.c).

## The license agreement

The installer shows the license agreement and installs a copy as `LICENSE`
in the install folder. The agreement sets the terms; this guide explains how
Phoenix applies them. In particular:

- The reports, the scoping summary, the Technical Conversion Breakdown and
  any test a Deep analysis builds are for assessment only (section 1.d).
  Once you may convert a conversion's tests, under the free edition (100 test
  cases or fewer) or a license that covers it, a test a Deep analysis built
  for that conversion becomes a *Converted Asset* (section 5).
- Tests converted or deployed without the license the agreement requires are
  not Converted Assets, and the agreement's license to Phoenix's helper code
  does not reach them: stop using them until a license covers their
  conversion (section 1.d).
- You may share the analysis output and your own evaluation of Phoenix with
  your employees, and with the contractors and professional advisers who
  help you evaluate, plan or carry out the migration of your own tests and
  are bound to confidentiality at least as protective as the agreement's.
  Publishing benchmark or evaluation results, or disclosing them to anyone
  else, needs Merito's written consent, and that restriction lasts for two
  years after the agreement ends (sections 2.f and 7.a).
- Restoring tests from Phoenix's backups, rolling back tests it converted,
  and finishing or undoing an interrupted run that was permitted when it
  started are allowed whatever your edition (section 1.f).
- Removing, disabling, bypassing or interfering with Phoenix's count, its
  limit or its license check (section 2.h), or forging, misusing or sharing a
  license file (section 2.i), ends the agreement at once. Merito may end it
  by notice for any other breach. A breach of the edition terms (sections 1.b
  to 1.d), of the rule against dividing a conversion or otherwise working
  around a test-case limit (section 2.g), or of a request for a conversion's
  count ends it only if you do not cure the breach, as section 1.d allows,
  within 30 days after Merito's notice (section 7.a).
- Merito may change or end the free edition. To end it for every version,
  Merito gives at least 30 days' notice, by email to the address used to
  request Phoenix and on its website (section 7.b).
- An order form or statement of work signed with Merito prevails over the
  agreement the installer shows where the two conflict, and over a license
  file that differs from it; Merito then promptly issues a corrected license
  file (sections 1.e and 10).
- Support for the free edition is best effort (section 6.b). A license or
  services agreement sets its own support terms.

Where this guide and the agreement differ, the agreement governs.
