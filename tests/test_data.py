import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from data import load_clips, tier_for_score, extract_drive_file_id

def test_tier_for_score():
    assert tier_for_score(10) == "Gold"
    assert tier_for_score(7)  == "Gold"
    assert tier_for_score(6)  == "Silver"
    assert tier_for_score(4)  == "Silver"
    assert tier_for_score(3)  == "Bronze"
    assert tier_for_score(1)  == "Bronze"

def test_extract_drive_file_id():
    url = "https://drive.google.com/file/d/1VCE1AJhGqGG64d9KpjhqxyYaBGR0tp9z/view?usp=drivesdk"
    assert extract_drive_file_id(url) == "1VCE1AJhGqGG64d9KpjhqxyYaBGR0tp9z"

def test_load_clips_structure():
    clips = load_clips()
    assert len(clips) > 0
    first = clips[0]
    assert "clip_id"       in first
    assert "content_id"    in first
    assert "clip_type"     in first
    assert "genre_cms"     in first
    assert "description"   in first
    assert "drive_file_id" in first
    assert "score"         in first
    assert "tier"          in first
    assert "watch_prob"    in first
    assert first["clip_type"] in ("momenttype", "cliffhanger")
