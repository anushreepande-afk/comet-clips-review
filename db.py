import streamlit as st
from supabase import create_client, Client
from typing import Dict, List, Optional


@st.cache_resource
def _client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def build_unique_clip_key(content_id: str, clip_type: str, clip_id: str) -> str:
    return f"{content_id}::{clip_type}::{clip_id}"


def _build_clip_payload(clip: Dict) -> Dict:
    unique_clip_key = build_unique_clip_key(
        str(clip["content_id"]),
        str(clip["clip_type"]),
        str(clip["clip_id"]),
    )
    return {
        "unique_clip_key": unique_clip_key,
        "clip_id":         clip["clip_id"],
        "content_id":      clip["content_id"],
        "content_name":    clip.get("content_name", ""),
        "clip_type":       clip["clip_type"],
        "output_label":    clip.get("output_label", ""),
        "clip_file_name":  clip.get("clip_file_name", ""),
        "clip_drive_link": clip.get("clip_drive_link", ""),
        "drive_file_id":   clip.get("drive_file_id", ""),
        "genre_cms":       clip.get("genre_cms", ""),
        "description":     clip.get("description", ""),
    }


def _build_upsert_payload(
    clip_id: str,
    content_id: str,
    clip_type: str,
    reviewer_email: str,
    score: int,
    unique_clip_key: Optional[str] = None,
) -> Dict:
    payload = {
        "clip_id":        clip_id,
        "content_id":     content_id,
        "clip_type":      clip_type,
        "reviewer_email": reviewer_email,
        "score":          score,
    }
    if unique_clip_key:
        payload["unique_clip_key"] = unique_clip_key
    return payload


def _is_schema_error(exc: Exception) -> bool:
    message = str(exc).lower()
    schema_markers = [
        "could not find",
        "column",
        "constraint",
        "foreign key",
        "relation",
        "schema cache",
    ]
    return any(marker in message for marker in schema_markers)


def upsert_rating(
    clip_id: str,
    content_id: str,
    clip_type: str,
    reviewer_email: str,
    score: int,
    clip: Optional[Dict] = None,
) -> None:
    unique_clip_key = build_unique_clip_key(content_id, clip_type, clip_id)
    rating_payload = _build_upsert_payload(
        clip_id,
        content_id,
        clip_type,
        reviewer_email,
        score,
        unique_clip_key=unique_clip_key,
    )

    try:
        if clip:
            _client().table("clips").upsert(
                _build_clip_payload(clip),
                on_conflict="unique_clip_key",
            ).execute()
        _client().table("ratings").upsert(
            rating_payload,
            on_conflict="unique_clip_key,reviewer_email",
        ).execute()
    except Exception as exc:
        if not _is_schema_error(exc):
            raise
        legacy_payload = _build_upsert_payload(
            clip_id,
            content_id,
            clip_type,
            reviewer_email,
            score,
        )
        _client().table("ratings").upsert(
            legacy_payload,
            on_conflict="clip_id,content_id,clip_type,reviewer_email",
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
