"""
Offline end-to-end test of the pipeline.

tests/sample_week.json holds one real week of SMARD data (14-20 Sep 2026) for
14 series. The test serves it instead of the network, then runs the download
script, the SQLite loader and every query in sql/analysis.sql. The nuclear
series is left out on purpose to check that it is filled with zeros.

Run:  python tests/test_pipeline.py
"""
import importlib.util
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / "tests" / "sample_week.json").read_text())


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "src" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_get_json(url, session, retries=3):
    m = re.search(r"/(\d+)/[A-Z-]+/index_hour\.json$", url)
    if m:
        return {"timestamps": [int(t) for t in SAMPLE.get(m.group(1), {})]}
    m = re.search(r"/(\d+)_[A-Z-]+_hour_(\d+)\.json$", url)
    return {"series": SAMPLE[m.group(1)][m.group(2)]}


download = load("01_download_smard")
download.get_json = fake_get_json
download.CACHE = ROOT / "data" / "cache_test"
download.time.sleep = lambda s: None
sys.argv = ["test", "--start", "2026-09-01"]
download.main()

loader = load("02_load_sqlite")
loader.main()

with sqlite3.connect(loader.DB) as con:
    hours, nuclear = con.execute("SELECT COUNT(*), SUM(nuclear_mwh) FROM hourly").fetchone()
    assert hours == 168, f"expected 168 hours, got {hours}"
    assert nuclear == 0, "nuclear should be filled with 0"
    queries = [q for q in (ROOT / "sql" / "analysis.sql").read_text().split(";") if "SELECT" in q]
    for i, q in enumerate(queries, 1):
        rows = con.execute(q).fetchall()
        assert rows, f"Q{i} returned no rows"
        print(f"Q{i}: {len(rows)} rows, first: {rows[0]}")
print("All checks passed.")
