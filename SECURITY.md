# Security Policy

## Supported versions

Only the latest release of each action receives security fixes; the
floating major tag (`v1`) always points at it.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Use
GitHub's private vulnerability reporting:
[Report a vulnerability](https://github.com/using-system/oddyssey-actions/security/advisories/new).

You can expect an acknowledgement within a few days. Relevant scope
includes what the actions download onto a runner (a coding CLI from its
vendor's release channel, apm-cli from PyPI through `uvx`, the oddyssey
package from GitHub) and the release workflow. Tokens are the caller's:
an action never reads a secret, and a report that involves one names it
by variable only.
