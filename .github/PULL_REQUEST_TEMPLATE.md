# What does this PR do?

<!-- One or two sentences. Link the issue it addresses, if there is one. -->

## Checklist

These mirror the non-negotiables in [CONTRIBUTING.md](https://github.com/ceparadise168/markwell/blob/main/CONTRIBUTING.md):

- [ ] Runtime stays **standard-library only** — no new third-party runtime dependency
- [ ] Markwell still **never writes to the device**
- [ ] **No network** connections at runtime
- [ ] `reader.py` remains the **only schema-aware** module — no Kobo SQL anywhere else
- [ ] Renderers stay **pure** — `render(books, meta)` returns `{filename: content}`, no I/O
- [ ] Tests added or updated for the behavior I changed
- [ ] If UI strings changed: **all four locales** (`en`, `zh-TW`, `ja`, `ko`) updated — key-parity test green
- [ ] `pytest` green locally
