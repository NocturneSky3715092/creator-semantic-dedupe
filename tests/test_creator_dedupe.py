import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.creator_dedupe import classify


def test_near_duplicate_decision():
    candidates = [{"record_id": "receipt-1", "embedding": [1.0, 0.0]}]
    assert classify("receipt-2", [0.995, 0.01], candidates).status == "duplicate"
    assert classify("update-1", [0.0, 1.0], candidates).status == "unique"
