import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db import _build_clip_payload, _build_upsert_payload, avg_score_for_clips, build_unique_clip_key

def test_build_unique_clip_key():
    assert build_unique_clip_key("1260029222", "momenttype_pro", "clip1") == "1260029222::momenttype_pro::clip1"

def test_build_upsert_payload():
    payload = _build_upsert_payload(
        clip_id="clip1",
        content_id="1260029222",
        clip_type="momenttype",
        reviewer_email="test@jiostar.com",
        score=8,
        unique_clip_key="1260029222::momenttype::clip1",
    )
    assert payload["clip_id"]        == "clip1"
    assert payload["content_id"]     == "1260029222"
    assert payload["clip_type"]      == "momenttype"
    assert payload["reviewer_email"] == "test@jiostar.com"
    assert payload["score"]          == 8
    assert payload["unique_clip_key"] == "1260029222::momenttype::clip1"

def test_build_clip_payload():
    payload = _build_clip_payload({
        "clip_id": "clip1",
        "content_id": "1260029222",
        "content_name": "Example Movie",
        "clip_type": "momenttype_pro",
        "output_label": "Gamma",
        "clip_file_name": "clip1.mp4",
        "clip_drive_link": "https://drive.google.com/file/d/abc/view",
        "drive_file_id": "abc",
        "genre_cms": "Drama",
        "description": "A key moment.",
    })
    assert payload["unique_clip_key"] == "1260029222::momenttype_pro::clip1"
    assert payload["content_name"] == "Example Movie"
    assert payload["drive_file_id"] == "abc"
    assert payload["genre_cms"] == "Drama"

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
