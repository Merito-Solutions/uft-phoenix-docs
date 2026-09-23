---
title: UFT Phoenix — VBScript to Python migration for OpenText UFT One
description: Merito UFT Phoenix converts OpenText UFT One VBScript tests to Python, from a local folder or a whole ALM project, with a safety model built for production estates.
hide:
  - navigation
  - toc
---

<p align="center">
  <img src="assets/hero.webp" alt="Merito UFT Phoenix — Migration Assistant for OpenText Functional Testing (UFT)" width="720">
</p>

# Move your UFT One tests from VBScript to Python { .phoenix-headline }

VBScript is on Microsoft's deprecation path, and OpenText UFT One now runs
tests written in Python. **Merito UFT Phoenix** does the conversion for you:
it reads your existing VBScript GUI tests and rebuilds them as UFT Python
tests, so years of automation investment carries forward instead of being
rewritten by hand.

Phoenix is **free to use**. Request access and we will send you the
installer.

[Request access](https://www.merito.com/resources/downloads/merito-uft-phoenix-vbs-to-python-utility?utm_source=other&utm_medium=referral&utm_campaign=merito-uft-phoenix-vbs-to-python-utility-5100009){ .md-button .md-button--primary }
[Talk to Merito](https://www.merito.com/book-consultation?utm_source=other&utm_medium=referral&utm_campaign=merito-uft-phoenix-vbs-to-python-utility-5100009){ .md-button }

---

## Why migrate now

- **VBScript has a shelf life.** Microsoft is retiring VBScript from Windows.
  Test estates that depend on it carry a growing platform risk.
- **Python opens the door.** Python is one of the most widely used languages
  in test automation, with a vast library ecosystem and a deep hiring pool.
- **Hand conversion does not scale.** An enterprise estate holds thousands
  of tests and shared actions. Rewriting them by hand is slow, costly and
  error-prone; Phoenix converts them consistently, and tells you exactly
  where a person is still needed.

## What Phoenix does

Phoenix offers two ways to convert, and runs on the Windows machine where
UFT One is installed.

| | **A folder of tests** | **A whole ALM project** |
| --- | --- | --- |
| Source | UFT tests stored on disk or a network share | An entire OpenText Application Quality Management (ALM) project |
| Result | Converted Python tests in a new output folder; your originals are untouched | The project converted in place, with calls between tests preserved |
| Best for | Pilots, smaller estates, tests kept in source control | Enterprise estates managed in ALM |

Every test is rebuilt through UFT One itself, so what Phoenix produces is a
genuine UFT Python test, not a text translation. Tests that call each other's
shared actions are converted together, so they keep working as one unit.

The **Migration Console** walks you through a migration step by step. For
automation and pipelines, everything is also available from the command
line.

## Safety first

Your test estate is valuable, so Phoenix is built to be careful with it:

- **Look before you leap.** An analysis run screens the whole project and
  reports what will convert, and what will not, without changing anything
  in ALM.
- **All or nothing.** If any test in scope is not ready, the conversion
  refuses to start. Your project is never left half VBScript and half
  Python.
- **A backup first, every time.** Nothing is written to ALM until you confirm
  a backup of the project exists.
- **History is kept.** On version-controlled ALM projects, each converted
  test gets a new version, and the original stays in version history.
- **Fully offline.** Installation and conversion need no internet access,
  and nothing leaves your network.

Read the full [ALM Safety](alm_safety.md) guide for the complete list of what
a conversion writes, and how to roll it back.

## How a migration runs

Phoenix follows a phased engagement, described in the
[Migration Playbook](playbook.md):

1. **Readiness.** Check the conversion machine, UFT One and the ALM
   connection.
2. **Discovery.** Analyze the estate and see what converts automatically.
3. **Pilot.** Convert a representative sample and prove the results.
4. **Hardening.** Resolve the blockers the pilot uncovers.
5. **Migration window.** Convert, verify and sign off.
6. **Rollout and governance.** Extend to the whole estate, and keep new
   tests in Python.

## Supported platforms

| Component | Supported |
| --- | --- |
| OpenText UFT One | 26.1, with Python test support installed |
| OpenText Application Quality Management (ALM) | 24.1, 25.1 and 26.1 |
| Windows | 10 and 11, Server 2019 and later |
| Source tests | UFT / QTP 11+ GUI tests written in VBScript |

The complete conversion coverage matrix is in
[Supported Versions](supported_versions.md).

## Guides

The guides below are the same documentation that installs with Phoenix.
They are written for the engineers who run the migration.

**Getting Started**

| Guide | What it covers |
| --- | --- |
| [Installation](install.md) | Prerequisites, the Windows installer (interactive and silent) and the environment check. |
| [Usage](usage.md) | Both conversion paths — a local folder of tests or a whole ALM project — end to end. |
| [Supported Versions](supported_versions.md) | Supported Windows, UFT One and ALM versions, and exactly what converts. |

**Using the Console**

| Guide | What it covers |
| --- | --- |
| [Console Field Guide](gui_field_guide.md) | Every screen, field and button of the Migration Console, in wizard order. |
| [Migration Playbook](playbook.md) | The enterprise engagement sequence, phase by phase, with exit criteria. |
| [Acceptance Test Plan](acceptance_test_plan.md) | A hands-on validation walkthrough with a sign-off matrix. |

**Safety & Operations**

| Guide | What it covers |
| --- | --- |
| [ALM Safety](alm_safety.md) | The write-safety model, everything a conversion writes to ALM, and how rollback works. |
| [Blocker Remediation](remediation.md) | How to fix each blocker that keeps a test from converting. |
| [Troubleshooting](troubleshooting.md) | Diagnosing environment, conversion and upload problems. |
| [Advanced Troubleshooting](advanced_troubleshooting.md) | Deep diagnostics for support engineers and migration leads. |
| [Known Limitations](limitations.md) | What Phoenix does not do, and the constructs that need a human. |

## Let Merito lead your migration

Phoenix is built by [Merito](https://www.merito.com), specialists in OpenText
functional testing and quality management. Our consultants can lead a
UFT migration end to end: planning, pilots, blocker remediation,
rollout and team enablement. If you would rather have experts lead the way,
we would be glad to help.

[Book a consultation](https://www.merito.com/book-consultation?utm_source=other&utm_medium=referral&utm_campaign=merito-uft-phoenix-vbs-to-python-utility-5100009){ .md-button .md-button--primary }
[Get a quote](https://www.merito.com/get-a-quote?utm_source=other&utm_medium=referral&utm_campaign=merito-uft-phoenix-vbs-to-python-utility-5100009){ .md-button }
