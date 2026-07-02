import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db import _build_upsert_payload, avg_score_for_clips

def test_build_upsert_payload():
    payload = _build_upsert_payload(
        clip_id="clip1",
        content_id="1260029222",
        clip_type="momenttype",
        reviewer_email="test@jiostar.com",
        score=8
    )
    assert payload["clip_id"]        == "clip1"
    assert payload["content_id"]     == "1260029222"
    assert payload["clip_type"]      == "momenttype"
    assert payload["reviewer_email"] == "test@jiostar.com"
    assert payload["score"]          == 8

def test_avg_score_empty():
    result = avg_score_for_clips([], "clip1", "1260029222", "momenttype")
    assert result is None

def test_avg_score_calculation():
    ratings = [
        {"clip_id": "clip1", "content_id": "1260029222", "clip_type": "momenttype", "score": 8},
        {"clip_id": "clip1", "content_id": "1260029222", "clip_type": "momenttype", "score": 6},
        {"clip_id": "clip2", "content_id": "1260029222", "clip_type": "momenttype", "score": 9},
    ]
    assert avg_score_for_clips(ratings, "clip1", "1260029222", "momenttype") == 7.0
    assert avg_score_for_clips(ratings, "clip2", "1260029222", "momenttype") == 9.0
    assert avg_score_for_clips(ratings, "clip3", "1260029222", "momenttype") is None
