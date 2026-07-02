import json
import os
import re
from typing import List, Dict, Optional

_CLIPS_JSON = os.path.join(os.path.dirname(__file__), "clips_data.json")
_cache: list = []


def tier_for_score(score: int) -> str:
    if score >= 7:
        return "Gold"
    if score >= 4:
        return "Silver"
    return "Bronze"


def extract_drive_file_id(drive_url: str) -> str:
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", drive_url)
    return match.group(1) if match else ""


def load_clips() -> List[Dict]:
    global _cache
    if not _cache:
        with open(_CLIPS_JSON, "r") as f:
            raw = json.load(f)
        for clip in raw:
            if clip.get("score") == "" or clip.get("score") is None:
                clip["score"] = 0
            if clip.get("tier") == "" or clip.get("tier") is None:
                clip["tier"] = "Bronze"
            if clip.get("watch_prob") == "" or clip.get("watch_prob") is None:
                clip["watch_prob"] = 0
        _cache = raw
    return _cache


def clips_for(content_id: str, clip_type: str) -> List[Dict]:
    return [
        c for c in load_clips()
        if c["content_id"] == content_id and c["clip_type"] == clip_type
    ]


def all_content_ids() -> List[str]:
    return list(dict.fromkeys(c["content_id"] for c in load_clips()))
