# Contributing to Punkto

Welcome — and thank you for considering a contribution to Punkto.

Punkto is a minimal protocol for addressing points in 3D space and attaching small, signed data to those locations. The core philosophy is **simple over clever, explicit over implicit, local-first over cloud-first**. Contributions that move the project in that direction are very welcome.

This guide covers everything from a five-minute first contribution to running your own node.

---

## Quick orientation

| Path | What it is |
|---|---|
| `punkto.md`, `punkto.ui.md`, `punkto.sync.md`, `punkto.node.md`, `punkto.relay.md`, `punkto.identity.md`, `punkto.manifest.md`, `punkto.ai.md` | The protocol specs — these are authoritative. Read at least `punkto.md` first. |
| `pwa/` | The reference web app (PWA) — vanilla JS, MapLibre, deck.gl, no build step. |
| `relay/` | The reference relay node (Python, stdlib + `requests`). |
| `core/` | Pure-Python core library (canonical encoding, atom utilities). |
| `tools/` | Small standalone CLI tools (key generation, signing, etc.). |

If you're new, browse `punkto.md` and `README.md`, then poke at `pwa/index.html` in a browser to see what the protocol *feels* like.

---

## Ways to contribute

All contributions are welcome — code is just one form. In rough order of "easy first":

1. **Try it and report what's broken.** Open an issue with a clear repro.
2. **Fix typos, clarify spec wording.** PRs against `*.md` files are gladly merged.
3. **Run a relay node** in your city/country/region. Tell us about it. Punkto is meant to be a public commons.
4. **Build a Punkto client** in another language (Rust, Go, Swift, etc.). The specs are language-neutral.
5. **Improve the PWA** — UX, performance, accessibility, internationalization.
6. **Implement v0.2 features** — see `Roadmap` in `README.md`.
7. **Propose protocol changes.** Open a design issue first; spec changes deserve discussion before code.

---

## Running it locally

### The PWA (web app)

No build step. Just serve the `pwa/` directory.

```bash
git clone https://github.com/Fisker1111/Punkto.git
cd Punkto/pwa
python3 -m http.server 8080
# open http://localhost:8080 in your browser
```

By default the PWA talks to `https://www.punkto.xyz`. To point at a local relay, edit `pwa/app.js` and change the `NODE_URLS` constant.

### A relay node

```bash
cd Punkto/relay
pip install -r requirements.txt
python3 relay.py
# listens on http://127.0.0.1:8000 by default
# POST atoms to /atom, read /latest
```

See `relay/README.md` for full operator docs and `relay/.env.example` for configuration.

### The CLI tools

```bash
cd Punkto
pip install cryptography
python3 tools/punkto-keygen-v0.1.py    # mint a new identity (12-word mnemonic)
python3 tools/punkto-key.py new        # full toolkit: new / import / sign / verify
```

See `punkto.identity.md` for the identity spec.

---

## Submitting a change

### Small fixes (typos, doc clarifications, obvious bugs)

Just open a PR. No issue needed.

1. Fork `Fisker1111/Punkto` on GitHub.
2. Create a branch: `git checkout -b fix/typo-in-punkto-md`
3. Commit with a clear message: `git commit -m 'Fix typo in punkto.md §3'`
4. Push and open a pull request against `main`.
5. Be patient — this is a small project, review may take a few days.

### Larger changes (new features, spec proposals, refactors)

1. **Open an issue first** describing what you want to do and why. This avoids you investing in a PR that doesn't fit the project's direction.
2. Discuss briefly. Spec changes especially deserve a round of conversation before code.
3. Once we agree on the shape, implement and submit a PR.
4. Reference the issue in your PR description.

### Commit messages

Keep them short, imperative, and informative:

- ✅ `Add /latest endpoint to relay`
- ✅ `Fix base32 padding bug in author_id`
- ✅ `Spec: clarify canonical bytes exclude sig`
- ❌ `updates`
- ❌ `WIP fix stuff`

A short subject line (≤72 chars) is usually enough. Add a body if context matters.

---

## Code style

No strict linter rules — readability matters more than uniformity. A few principles:

- **Python**: PEP 8 in spirit. Stdlib over dependencies wherever practical. The relay deliberately uses only `http.server` + `requests`.
- **JavaScript**: Vanilla ES modules in the PWA. No build step, no framework. Keep it readable in a browser DevTools view.
- **Specs (`*.md`)**: Match the existing tone — declarative, sectioned, with concrete examples and test vectors where useful.
- **Comments**: Explain *why*, not *what*. Code shows the what.
- **Functions**: Small. One job each. If a function name needs `_and_`, split it.

---

## What's in scope

**Yes, please** ✅

- Spec clarifications and typo fixes
- New language implementations (Rust, Go, Swift, etc.)
- Performance improvements to the relay or PWA
- Better tests, especially edge-case coverage
- New tools that follow the existing CLI patterns
- Accessibility & i18n improvements to the PWA
- Documentation, examples, tutorials

**Probably no** ❌

- Centralized features (account servers, global indexes, mandatory authentication)
- Heavy framework dependencies in core/PWA/relay
- Adding a database to the relay (it's deliberately a buffer, not a DB)
- Renaming canonical fields (`punkto`, `t`, `f`, `x`, `sig`) — this breaks the network
- Backward-incompatible spec changes without a strong rationale

When in doubt, open an issue and ask.

---

## Reporting bugs

Use [GitHub Issues](https://github.com/Fisker1111/Punkto/issues). Include:

- What you tried
- What you expected
- What happened instead
- Browser/OS/Python version where relevant
- Console logs or curl output if it's a network issue

For security-related issues, see [SECURITY.md](SECURITY.md) — please don't open public issues for vulnerabilities.

---

## Code of conduct

We follow the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md). In short: be kind, be patient, assume good faith. Disagreements about the protocol are fine and welcome; personal attacks are not.

---

## License

By contributing to Punkto, you agree that your contributions will be licensed under the MIT License (see [LICENSE](LICENSE)). You retain copyright to your contributions.

---

## A note on the project's stage

Punkto is small and early. The specs are stable enough to be useful but young enough to evolve. There's no foundation, no Slack, no governance committee — just a Git repository, a set of `.md` files, and people who think a writable 3D coordinate system might be useful. If you bring an idea, it gets a real read.

Thanks for being here.
