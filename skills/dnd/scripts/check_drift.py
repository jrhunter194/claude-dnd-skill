#!/usr/bin/env python3
"""
check_drift.py — single-source consistency guard for campaign character vitals.

INVARIANT (the whole point of this script):
    A mutable character vital — XP, Level, HP, AC — has exactly ONE home:
    the character sheet `characters/<name>.md`. Every other file (notably
    `state.md`) must carry a POINTER, never a copy. Copies are the only
    source of drift (falling-stars history: XP 450-vs-600 S6; Level 2-vs-3
    and HP 13-vs-21 in state.md while the sheet was correct, S8).

WHAT IT DOES:
    Reads the canonical vitals from each PC sheet, then scans state.md for any
    vital number printed on a line that names that PC and compares them.
      - MISMATCH  -> DRIFT (error; exit 1). state.md disagrees with the sheet.
      - PRESENT but matching -> DUPLICATE (warning). A copy that hasn't drifted
        *yet* — should be a pointer. With --strict these also fail (exit 1).

    The sheet always wins. This script never edits anything; it only reports.

USAGE:
    python3 check_drift.py --campaign <name> [--strict] [--quiet]

    Wired into /dm:dnd load and /dm:dnd save so drift can never sit unnoticed.
"""
from __future__ import annotations
import argparse
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from paths import campaign_dir, find_campaign  # noqa: E402

# Canonical vital patterns on the character sheet (same conventions as xp.py).
_SHEET_PATTERNS = {
    "xp":    re.compile(r"\*\*XP:\*\*\s*(\d+)"),
    "level": re.compile(r"\*\*Level:\*\*\s*(\d+)"),
    "hp":    re.compile(r"\*\*HP:\*\*\s*(\d+)\s*/\s*(\d+)"),
    "ac":    re.compile(r"\*\*AC:\*\*\s*(\d+)"),
    "class": re.compile(r"\*\*Class:\*\*\s*([A-Za-z][A-Za-z /]*?)\s*(?:\||$)", re.M),
    "name":  re.compile(r"^#\s+(.+?)\s*$", re.M),
}


def _read_sheet(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    v: dict = {"file": path.name}
    nm = _SHEET_PATTERNS["name"].search(text)
    v["name"] = (nm.group(1).strip() if nm else path.stem).strip()
    xp = _SHEET_PATTERNS["xp"].search(text)
    lv = _SHEET_PATTERNS["level"].search(text)
    hp = _SHEET_PATTERNS["hp"].search(text)
    ac = _SHEET_PATTERNS["ac"].search(text)
    cl = _SHEET_PATTERNS["class"].search(text)
    v["xp"]     = int(xp.group(1)) if xp else None
    v["level"]  = int(lv.group(1)) if lv else None
    v["hp_cur"] = int(hp.group(1)) if hp else None
    v["hp_max"] = int(hp.group(2)) if hp else None
    v["ac"]     = int(ac.group(1)) if ac else None
    v["class"]  = cl.group(1).strip() if cl else None
    return v


def _vitals_on_line(line: str, sheet: dict) -> list[tuple[str, str, object, object]]:
    """Return (vital, snippet, found, canonical) for any vital printed on a
    state.md line that names this PC. Only **structured stat lines** (pipe-
    delimited, the template's `| HP X/X | AC X |` party/resources format) are
    enforced — that's where live current-state vitals live and where drift
    actually happens. Free-text/past-tense prose (historical recaps, combat
    snapshots, calibration notes) uses commas/parens, not pipes, so it's left
    alone: a guard that nags about history is a guard people learn to ignore."""
    if "|" not in line:
        return []
    found = []

    m = re.search(r"\bHP\s*(\d+)\s*/\s*(\d+)", line, re.I)
    if m and sheet["hp_cur"] is not None:
        if (int(m.group(1)), int(m.group(2))) != (sheet["hp_cur"], sheet["hp_max"]):
            found.append(("HP", m.group(0), f"{m.group(1)}/{m.group(2)}",
                          f"{sheet['hp_cur']}/{sheet['hp_max']}"))
        else:
            found.append(("HP", m.group(0), "ok", "ok"))

    # Level via "Level N" or "<Class> N" (e.g. "Bard 3")
    lvl_found = None
    m = re.search(r"\bLevel\s*(\d+)", line, re.I)
    if m:
        lvl_found = (int(m.group(1)), m.group(0))
    elif sheet["class"]:
        m = re.search(rf"\b{re.escape(sheet['class'])}\s*(\d+)", line, re.I)
        if m:
            lvl_found = (int(m.group(1)), m.group(0))
    if lvl_found and sheet["level"] is not None:
        n, snip = lvl_found
        if n != sheet["level"]:
            found.append(("Level", snip, n, sheet["level"]))
        else:
            found.append(("Level", snip, "ok", "ok"))

    m = re.search(r"\bAC\s*(\d+)", line, re.I)
    if m and sheet["ac"] is not None:
        if int(m.group(1)) != sheet["ac"]:
            found.append(("AC", m.group(0), int(m.group(1)), sheet["ac"]))
        else:
            found.append(("AC", m.group(0), "ok", "ok"))

    # XP should never be a bare number in state.md (pointer only)
    m = re.search(r"\bXP[:\s]+(\d{2,})\b", line, re.I)
    if m:
        n = int(m.group(1))
        canon = sheet["xp"]
        if canon is not None and n != canon:
            found.append(("XP", m.group(0), n, canon))
        else:
            found.append(("XP", m.group(0), "ok", "ok"))

    return found


def main() -> int:
    ap = argparse.ArgumentParser(description="Single-source vitals drift guard.")
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--strict", action="store_true",
                    help="Also fail on duplicate-but-matching vitals (enforce pointers).")
    ap.add_argument("--quiet", action="store_true",
                    help="Print nothing on a clean pass (for hook use).")
    args = ap.parse_args()

    try:
        cdir = find_campaign(args.campaign)
    except Exception:
        cdir = campaign_dir(args.campaign)
    if not cdir.exists():
        print(f"check_drift: campaign not found: {args.campaign}", file=sys.stderr)
        return 2

    char_dir = cdir / "characters"
    state_md = cdir / "state.md"
    sheets = [_read_sheet(p) for p in sorted(char_dir.glob("*.md"))] if char_dir.exists() else []
    if not state_md.exists() or not sheets:
        if not args.quiet:
            print("check_drift: nothing to check (no state.md or no sheets).")
        return 0

    state_lines = state_md.read_text(encoding="utf-8").splitlines()

    drift: list[str] = []
    dupes: list[str] = []
    for sheet in sheets:
        name = sheet["name"]
        # Match the PC name as a word; party/resources lines are name-prefixed.
        name_re = re.compile(re.escape(name), re.I)
        for i, line in enumerate(state_lines, 1):
            if not name_re.search(line):
                continue
            for vital, snip, got, want in _vitals_on_line(line, sheet):
                if got == "ok":
                    dupes.append(f"  state.md:{i}  {name}: {vital} duplicated ('{snip.strip()}') — should be a pointer to the sheet")
                else:
                    drift.append(f"  state.md:{i}  {name}: {vital} DRIFT — state.md says {got}, sheet says {want}  ('{snip.strip()}')")

    if drift:
        print("✗ VITALS DRIFT — state.md disagrees with the character sheet (the sheet wins; fix state.md):")
        print("\n".join(drift))
    if dupes and (args.strict or not args.quiet):
        print("⚠ Duplicated vitals (no drift yet, but they're copies that will drift — convert to pointers):")
        print("\n".join(dupes))

    if drift:
        return 1
    if dupes and args.strict:
        return 1
    if not args.quiet:
        print(f"✓ vitals single-source OK — {len(sheets)} sheet(s) checked, no drift in state.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
