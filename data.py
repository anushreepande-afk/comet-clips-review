import json
import os
import re
import streamlit as st
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


@st.cache_data
def load_clips() -> List[Dict]:
    with open(_CLIPS_JSON, "r") as f:
        raw = json.load(f)
    result = []
    for clip in raw:
        c = dict(clip)  # copy to avoid mutating source
        if c.get("score") == "" or c.get("score") is None:
            c["score"] = 0
        if c.get("tier") == "" or c.get("tier") is None:
            c["tier"] = "Bronze"
        if c.get("watch_prob") == "" or c.get("watch_prob") is None:
            c["watch_prob"] = 0
        result.append(c)
    return result


def clips_for(content_id: str, clip_type: str) -> List[Dict]:
    return [
        c for c in load_clips()
        if c["content_id"] == content_id and c["clip_type"] == clip_type
    ]


def all_content_ids() -> List[str]:
    return list(dict.fromkeys(c["content_id"] for c in load_clips()))
