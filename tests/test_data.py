import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from clip_data import (
    OUTPUT_SET_ORDER,
    all_content_ids,
    extract_drive_file_id,
    load_clips,
    load_manifest,
    manifest_for,
    output_sets_for,
    tier_for_score,
)

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
    assert "content_name"  in first
    assert "clip_type"     in first
    assert "output_label"  in first
    assert "genre_cms"     in first
    assert "description"   in first
    assert "drive_file_id" in first
    assert "score"         in first
    assert "tier"          in first
    assert "watch_prob"    in first
    assert first["clip_type"] in OUTPUT_SET_ORDER

def test_new_dataset_shape():
    clips = load_clips()
    manifest = load_manifest()
    assert len(all_content_ids()) == 11
    assert len(manifest) == 44
    assert len(clips) == 437
    assert {c["clip_type"] for c in clips} == set(OUTPUT_SET_ORDER)

def test_genre_cms_stays_separate_from_generic_genre():
    clips = load_clips()
    assert any(c.get("genre_cms") == "Sports" and c.get("genre") == "Sports Drama" for c in clips)

def test_output_sets_for_each_content():
    for content_id in all_content_ids():
        assert output_sets_for(content_id) == OUTPUT_SET_ORDER

def test_manifest_tracks_missing_sources():
    rudra_ch_pro = manifest_for("1260084562", "cliffhanger_pro")
    rudra_mt_pro = manifest_for("1260084562", "momenttype_pro")
    assert rudra_ch_pro["source_status"] == "OK"
    assert rudra_ch_pro["clip_links"] == 10
    assert rudra_mt_pro["source_status"] == "OK"
    assert rudra_mt_pro["clip_links"] == 10
