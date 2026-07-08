import json
import os
import re
from typing import Dict, List, Optional

import streamlit as st

_CLIPS_JSON = os.path.join(os.path.dirname(__file__), "clips_data.json")
_MANIFEST_JSON = os.path.join(os.path.dirname(__file__), "clips_manifest.json")

OUTPUT_SET_ORDER = [
    "cliffhanger_pro",
    "cliffhanger_flash",
    "momenttype_pro",
    "momenttype_flash",
]

OUTPUT_SET_LABELS: Dict[str, str] = {
    "cliffhanger_pro": "Cliffhanger · Pro",
    "cliffhanger_flash": "Cliffhanger · Flash",
    "momenttype_pro": "Moment Type · Pro",
    "momenttype_flash": "Moment Type · Flash",
}


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
        c = dict(clip)
        if c.get("score") == "" or c.get("score") is None:
            c["score"] = 0
        if c.get("tier") == "" or c.get("tier") is None:
            c["tier"] = "Bronze"
        if c.get("watch_prob") == "" or c.get("watch_prob") is None:
            c["watch_prob"] = 0
        if not c.get("drive_file_id") and c.get("clip_drive_link"):
            c["drive_file_id"] = extract_drive_file_id(c["clip_drive_link"])
        result.append(c)
    return result


@st.cache_data
def load_manifest() -> List[Dict]:
    with open(_MANIFEST_JSON, "r") as f:
        return json.load(f)


def clips_for(content_id: str, clip_type: str) -> List[Dict]:
    return [
        c for c in load_clips()
        if c["content_id"] == content_id and c["clip_type"] == clip_type
    ]


def manifest_for(content_id: str, clip_type: str) -> Optional[Dict]:
    for row in load_manifest():
        if row["content_id"] == content_id and row["clip_type"] == clip_type:
            return row
    return None


def all_content_ids() -> List[str]:
    return list(dict.fromkeys(row["content_id"] for row in load_manifest()))


def content_name_for(content_id: str) -> str:
    for row in load_manifest():
        if row["content_id"] == content_id:
            return row.get("content_name", content_id)
    return content_id


def output_sets_for(content_id: str) -> List[str]:
    available = {row["clip_type"] for row in load_manifest() if row["content_id"] == content_id}
    return [clip_type for clip_type in OUTPUT_SET_ORDER if clip_type in available]
