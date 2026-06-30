# Security Policy

Thank you for taking the time to help keep Punkto safe.

## Reporting a Vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Instead, report privately to:

📧 **fisker@protonmail.ch**

Include as much detail as you reasonably can:

- A clear description of the issue
- Steps to reproduce (or a proof-of-concept)
- The component affected (PWA, relay, CLI tool, spec, etc.)
- Your assessment of impact (e.g., what could an attacker do?)
- Any suggested fix, if you have one
- Whether you would like public credit when the issue is disclosed

We aim to acknowledge reports within **3 days** and to provide a substantive update within **14 days**.

If you do not receive a reply within a week, please feel free to nudge — email can get lost.

## Scope

### In scope

- Vulnerabilities in any code in this repository (`pwa/`, `relay/`, `core/`, `tools/`)
- Issues in the live reference deployment at `punkto.xyz`, `node1.punkto.xyz`, `node2.punkto.xyz`
- Spec ambiguities or design flaws that could lead to security problems if implemented as written
- Cryptographic weaknesses in `punkto.identity.md` (Ed25519 derivation, BIP39 mnemonic, canonical bytes for signing)

### Out of scope

- Vulnerabilities in third-party dependencies (please report those upstream — we will of course update affected versions once disclosed)
- Issues that require physical access to a victim's device or already-compromised credentials
- Denial-of-service via raw traffic volume (the public reference deployment is small and known to be limited)
- Social engineering of node operators or users
- Spam, low-quality content, or abusive atoms posted to the reference deployment — these are content-moderation concerns, not security vulnerabilities

## Disclosure Process

1. You report privately via email.
2. We acknowledge receipt and begin investigation.
3. We work with you to confirm and understand the issue.
4. We develop and test a fix.
5. We coordinate a disclosure timeline with you. By default we aim for **public disclosure within 90 days** of the initial report, or sooner once a fix is widely deployed.
6. We credit you in the changelog and (if you wish) in the disclosure announcement.

If the issue is being actively exploited or affects users today, we may move faster and disclose more concisely.

## What Happens After a Fix

Once a fix is in `main`:

- A new release is tagged (`vX.Y.Z`)
- The relay reference deployment is updated
- The vulnerability is documented in `CHANGELOG.md`
- The reporter is credited (with permission)

## Cryptographic Concerns

Punkto's signature model (see `punkto.identity.md`) uses Ed25519 over canonical UTF-8 bytes of an atom with the `sig` field excluded. If you find:

- A way to make two different atoms produce identical canonical bytes
- A signature that verifies for one atom but matches a different one
- A flaw in the BIP39 → seed → Ed25519 derivation that produces a non-deterministic or weak key
- Any side-channel in the reference implementation (`tools/punkto-key.py`)

…please report it. These are protocol-level issues and matter most.

## Public Acknowledgments

With reporters' permission, we acknowledge security contributions in:

- `CHANGELOG.md` under the relevant release
- The release announcement on the repository

Thank you for helping make Punkto safer.
