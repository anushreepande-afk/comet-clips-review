import streamlit as st
from supabase import create_client, Client
from typing import List, Dict, Optional


def _client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def _build_upsert_payload(
    clip_id: str,
    content_id: str,
    clip_type: str,
    reviewer_email: str,
    score: int,
) -> Dict:
    return {
        "clip_id":        clip_id,
        "content_id":     content_id,
        "clip_type":      clip_type,
        "reviewer_email": reviewer_email,
        "score":          score,
    }


def upsert_rating(
    clip_id: str,
    content_id: str,
    clip_type: str,
    reviewer_email: str,
    score: int,
) -> None:
    payload = _build_upsert_payload(clip_id, content_id, clip_type, reviewer_email, score)
    _client().table("ratings").upsert(
        payload,
        on_conflict="clip_id,content_id,clip_type,reviewer_email"
    ).execute()


def fetch_ratings_for_tab(content_id: str, clip_type: str) -> List[Dict]:
    resp = (
        _client()
        .table("ratings")
        .select("clip_id,content_id,clip_type,reviewer_email,score,submitted_at")
        .eq("content_id", content_id)
        .eq("clip_type", clip_type)
        .execute()
    )
    return resp.data or []


def fetch_my_ratings(reviewer_email: str, content_id: str, clip_type: str) -> Dict[str, int]:
    """Returns {clip_id: score} for this reviewer on this tab."""
    resp = (
        _client()
        .table("ratings")
        .select("clip_id,score")
        .eq("reviewer_email", reviewer_email)
        .eq("content_id", content_id)
        .eq("clip_type", clip_type)
        .execute()
    )
    return {row["clip_id"]: row["score"] for row in (resp.data or [])}


def avg_score_for_clips(
    ratings: List[Dict],
    clip_id: str,
    content_id: str,
    clip_type: str,
) -> Optional[float]:
    scores = [
        r["score"] for r in ratings
        if r["clip_id"] == clip_id
        and r["content_id"] == content_id
        and r["clip_type"] == clip_type
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 1)
