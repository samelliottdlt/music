# Copilot instructions

This repo documents Sam's music gear and setup. For any question about the
gear, routing, recording, firmware, or creative ideas, use the `music-setup`
skill in `.github/skills/music-setup/SKILL.md`. `gear/inventory.yaml` is the
source of truth for what gear exists.

Don't rely on training data for gear-specific facts or recommendations: source
them from the official manuals/docs linked in the repo and cite them (see the
"Sourcing rule" in the skill).

Official manuals are registered by URL in `gear/manuals.yaml` (never commit
the files); fetch, search and cite them with
`.github/skills/music-setup/scripts/manuals.py`. Show official pages, crops and
composed diagrams (`manuals.py page`/`sheet`, `diagram.py`) when a picture
helps; generated images go to `out/` and are never committed.
