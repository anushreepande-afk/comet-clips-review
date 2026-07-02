import json
import os
import re
from typing import List, Dict, Optional

_CLIPS_JSON = os.path.join(os.path.dirname(__file__), "clips_data.json")


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
    with open(_CLIPS_JSON, "r") as f:
        return json.load(f)


def clips_for(content_id: str, clip_type: str) -> List[Dict]:
    return [
        c for c in load_clips()
        if c["content_id"] == content_id and c["clip_type"] == clip_type
    ]


def all_content_ids() -> List[str]:
    seen = []
    for c in load_clips():
        if c["content_id"] not in seen:
            seen.append(c["content_id"])
    return seen
