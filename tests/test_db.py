import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db import (
    _build_clip_payload,
    _build_clip_set_payload,
    _build_upsert_payload,
    build_clip_set_key,
    build_unique_clip_key,
    prompt_model_from_clip_type,
)

def test_build_clip_set_key():
    assert build_clip_set_key("1260029222", "Moment Type", "Pro") == "1260029222::momenttype::pro"

def test_build_unique_clip_key():
    assert build_unique_clip_key("1260029222", "momenttype_pro", "clip1") == "1260029222::momenttype::pro::clip1"

def test_prompt_model_from_clip_type():
    assert prompt_model_from_clip_type("cliffhanger_flash") == ("cliffhanger", "flash")

def test_build_upsert_payload():
    payload = _build_upsert_payload(
        clip_id="clip1",
        content_id="1260029222",
        clip_type="momenttype",
        reviewer_email="test@jiostar.com",
        score=1,
        feedback_text="Needs tighter ending.",
        rejection_rating=4,
        include_rejection_details=True,
        unique_clip_key="1260029222::momenttype::pro::clip1",
        clip_set_key="1260029222::momenttype::pro",
    )
    assert payload["clip_id"]        == "clip1"
    assert payload["content_id"]     == "1260029222"
    assert payload["clip_type"]      == "momenttype"
    assert payload["reviewer_email"] == "test@jiostar.com"
    assert payload["score"]          == 1
    assert payload["feedback_text"] == "Needs tighter ending."
    assert payload["rejection_rating"] == 4
    assert payload["unique_clip_key"] == "1260029222::momenttype::pro::clip1"
    assert payload["clip_set_key"] == "1260029222::momenttype::pro"

def test_build_clip_set_payload():
    payload = _build_clip_set_payload({
        "content_id": "1260029222",
        "content_name": "Example Movie",
        "clip_type": "momenttype_pro",
        "output_label": "V3",
    })
    assert payload["clip_set_key"] == "1260029222::momenttype::pro"
    assert payload["prompt"] == "momenttype"
    assert payload["model"] == "pro"

def test_build_clip_payload():
    payload = _build_clip_payload({
        "clip_id": "clip1",
        "content_id": "1260029222",
        "content_name": "Example Movie",
        "clip_type": "momenttype_pro",
        "output_label": "V3",
        "clip_file_name": "clip1.mp4",
        "clip_drive_link": "https://drive.google.com/file/d/abc/view",
        "drive_file_id": "abc",
        "genre_cms": "Drama",
        "description": "A key moment.",
    })
    assert payload["clip_set_key"] == "1260029222::momenttype::pro"
    assert payload["unique_clip_key"] == "1260029222::momenttype::pro::clip1"
    assert payload["content_name"] == "Example Movie"
    assert payload["drive_file_id"] == "abc"
    assert payload["genre_cms"] == "Drama"
