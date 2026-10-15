#!/usr/bin/env python3
"""Génère data/employees.csv et data/events.csv à partir de config/simulation.json."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from phishcamp.simulate import simulate, write  # noqa: E402

camps = json.loads((ROOT / "campaigns" / "campaigns.json").read_text(encoding="utf-8"))
cfg = json.loads((ROOT / "config" / "simulation.json").read_text(encoding="utf-8"))
emp, ev = simulate(camps, cfg)
write(emp, ev, ROOT / "data")
print(f"{len(emp)} employés, {len(ev)} envois sur {len(camps)} campagnes -> data/")
