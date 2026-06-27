# Adventures

Bundled, ready-to-import adventure modules for the `dm` skill. Each is a self-contained
source document you can drop straight into a campaign with `/dm:dnd import`.

These are original works written for this skill — not reprints of any published module — and
are licensed under the same terms as the rest of the repository (AGPL-3.0-or-later).

## Available modules

| Module | Levels | Length | Hook |
|---|---|---|---|
| [`falling-stars/`](falling-stars/falling-stars.md) | 1–5 | Mini-campaign, 3 acts | Stars are falling on a frontier marsh-town, and where they land the dead don't rest. A doomsday cult is racing to gather the pieces of a dead god. |

## How to play one

From a Claude Code session with the `dm` plugin installed:

```
/dm:dnd import <path-to>/adventures/falling-stars/falling-stars.md falling-stars
```

The import procedure extracts the source, maps it into campaign files
(`world.md`, `arc.md`, `npcs-full.md`, a lazy `source/` corpus, and `state.md`), runs a
short gap-fill wizard for anything the module leaves to the table (starting level, party
size, in-world date), and leaves you a playable campaign. Then:

```
/dm:dnd character new      # make a character
/dm:dnd load falling-stars # start playing
```

## How a module is written

Each module is a plain Markdown document structured so the importer's chapter segmentation
maps it cleanly:

- An `# H1` title and a short front-matter block (system, structure, tone, pillars).
- A **Background** section that is explicitly DM-only — the truth the players discover in
  fragments rather than as exposition.
- The **Three Truths** (settlement / threat / mystery), a **Threat Escalation Arc** table,
  and a **Factions** list — these map directly onto `world.md`.
- `# Act` / `## Chapter X.Y` headings, each with read-aloud boxed text, keyed locations,
  NPCs (referencing SRD stat blocks by name rather than reprinting them), and explicit
  **beats** the DM marks complete as they land — these map onto `arc.md` and the `source/`
  corpus.
- Appendices: an NPC roster table, any new items or creatures, and a beats quick-reference.

If you write your own, follow that shape and it will import without hand-editing.
