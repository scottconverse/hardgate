# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in hardgate, please report it
privately via GitHub Security Advisories:

https://github.com/scottconverse/hardgate/security/advisories/new

Please do **not** open a public issue for security reports. Public
disclosure before a fix is available puts users at risk.

When reporting, include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce, or a proof-of-concept if available.
- The version (or commit SHA) where you observed the issue.
- Your environment (OS, Python version, shell).

## Response SLA

We aim to respond to security reports on the following timeline:

- **Acknowledgement:** within 7 days of receipt.
- **Initial assessment / triage:** within 14 days.
- **Fix or mitigation released:** within 30 days for confirmed
  vulnerabilities, or a documented mitigation plan if a longer fix
  window is required.

## Supported Versions

Only the latest minor release line receives security fixes. Older
minor versions are end-of-life on the day a new minor ships. Users
on older versions should upgrade to receive security patches.

| Version       | Supported          |
| ------------- | ------------------ |
| latest minor  | yes                |
| older minors  | no                 |

## Scope

In scope:

- The hardgate installer (`install.sh`, `install.ps1`).
- The gate hook scripts under `templates/` and `dist/`.
- The build pipeline (`scripts/build-installer.py`).

Out of scope:

- Vulnerabilities in third-party dependencies (report upstream).
- Issues that require already-compromised local machine access.

Thank you for helping keep hardgate and its users safe.
