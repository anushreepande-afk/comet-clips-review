import streamlit as st
from supabase import create_client, Client
from typing import Dict, List, Optional

CLIP_TYPE_TO_PROMPT_MODEL: Dict[str, tuple[str, str]] = {
    "cliffhanger_pro": ("cliffhanger", "pro"),
    "cliffhanger_flash": ("cliffhanger", "flash"),
    "momenttype_pro": ("momenttype", "pro"),
    "momenttype_flash": ("momenttype", "flash"),
}


@st.cache_resource
def _client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def _normalize_key_part(value: str) -> str:
    return str(value).strip().lower().replace(" ", "")


def prompt_model_from_clip_type(clip_type: str) -> tuple[str, str]:
    if clip_type in CLIP_TYPE_TO_PROMPT_MODEL:
        return CLIP_TYPE_TO_PROMPT_MODEL[clip_type]
    parts = str(clip_type).rsplit("_", 1)
    if len(parts) == 2:
        return _normalize_key_part(parts[0]), _normalize_key_part(parts[1])
    return _normalize_key_part(clip_type), ""


def build_clip_set_key(content_id: str, prompt: str, model: str) -> str:
    return f"{content_id}::{_normalize_key_part(prompt)}::{_normalize_key_part(model)}"


def build_unique_clip_key(content_id: str, clip_type: str, clip_id: str) -> str:
    prompt, model = prompt_model_from_clip_type(clip_type)
    return f"{build_clip_set_key(content_id, prompt, model)}::{clip_id}"


def _build_clip_set_payload(clip: Dict) -> Dict:
    prompt, model = prompt_model_from_clip_type(str(clip["clip_type"]))
    prompt = _normalize_key_part(clip.get("prompt") or prompt)
    model = _normalize_key_part(clip.get("model") or model)
    return {
        "clip_set_key":   build_clip_set_key(str(clip["content_id"]), prompt, model),
        "content_id":     clip["content_id"],
        "content_name":   clip.get("content_name", ""),
        "prompt":         prompt,
        "model":          model,
        "clip_type":      clip["clip_type"],
        "output_label":   clip.get("output_label", ""),
        "source_status":  clip.get("source_status", ""),
        "json_source_file": clip.get("json_source_file", ""),
        "json_source_link": clip.get("json_source_link", ""),
        "clip_folder_name": clip.get("clip_folder_name", ""),
        "clip_folder_link": clip.get("clip_folder_link", ""),
    }


def _build_clip_payload(clip: Dict) -> Dict:
    clip_set_payload = _build_clip_set_payload(clip)
    unique_clip_key = build_unique_clip_key(
        str(clip["content_id"]),
        str(clip["clip_type"]),
        str(clip["clip_id"]),
    )
    return {
        "unique_clip_key": unique_clip_key,
        "clip_set_key":    clip_set_payload["clip_set_key"],
        "clip_id":         clip["clip_id"],
        "content_id":      clip["content_id"],
        "content_name":    clip.get("content_name", ""),
        "prompt":          clip_set_payload["prompt"],
        "model":           clip_set_payload["model"],
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
    feedback_text: Optional[str] = None,
    unique_clip_key: Optional[str] = None,
    clip_set_key: Optional[str] = None,
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
    if clip_set_key:
        payload["clip_set_key"] = clip_set_key
    if feedback_text is not None:
        payload["feedback_text"] = feedback_text
    return payload


def _is_schema_error(exc: Exception) -> bool:
    message = str(exc).lower()
    schema_markers = [
        "could not find",
        "column",
        "constraint",
        "foreign key",
        "no unique",
        "on conflict",
        "permission denied",
        "relation",
        "row-level security",
        "schema cache",
        "unique or exclusion",
    ]
    return any(marker in message for marker in schema_markers)


def _upsert_legacy_rating(
    clip_id: str,
    content_id: str,
    clip_type: str,
    reviewer_email: str,
    score: int,
    feedback_text: Optional[str] = None,
) -> None:
    payload = _build_upsert_payload(
        clip_id,
        content_id,
        clip_type,
        reviewer_email,
        score,
        feedback_text=feedback_text,
    )
    match = {
        "clip_id": clip_id,
        "content_id": content_id,
        "clip_type": clip_type,
        "reviewer_email": reviewer_email,
    }
    update_values = {"score": score}
    if feedback_text is not None:
        update_values["feedback_text"] = feedback_text
    try:
        update_resp = (
            _client()
            .table("ratings")
            .update(update_values)
            .match(match)
            .execute()
        )
    except Exception as exc:
        if feedback_text is None or not _is_schema_error(exc):
            raise
        payload.pop("feedback_text", None)
        update_resp = (
            _client()
            .table("ratings")
            .update({"score": score})
            .match(match)
            .execute()
        )
    if update_resp.data:
        return
    try:
        _client().table("ratings").insert(payload).execute()
    except Exception as exc:
        if "feedback_text" not in payload or not _is_schema_error(exc):
            raise
        payload.pop("feedback_text", None)
        _client().table("ratings").insert(payload).execute()


def upsert_rating(
    clip_id: str,
    content_id: str,
    clip_type: str,
    reviewer_email: str,
    score: int,
    clip: Optional[Dict] = None,
    feedback_text: Optional[str] = None,
) -> None:
    unique_clip_key = build_unique_clip_key(content_id, clip_type, clip_id)
    clip_set_key = unique_clip_key.rsplit("::", 1)[0]
    rating_payload = _build_upsert_payload(
        clip_id,
        content_id,
        clip_type,
        reviewer_email,
        score,
        feedback_text=feedback_text,
        unique_clip_key=unique_clip_key,
        clip_set_key=clip_set_key,
    )

    try:
        if clip:
            try:
                _client().table("clip_sets").upsert(
                    _build_clip_set_payload(clip),
                    on_conflict="clip_set_key",
                ).execute()
                _client().table("clips").upsert(
                    _build_clip_payload(clip),
                    on_conflict="unique_clip_key",
                ).execute()
            except Exception:
                _upsert_legacy_rating(clip_id, content_id, clip_type, reviewer_email, score, feedback_text)
                return
        _client().table("ratings").upsert(
            rating_payload,
            on_conflict="unique_clip_key,reviewer_email",
        ).execute()
    except Exception:
        _upsert_legacy_rating(clip_id, content_id, clip_type, reviewer_email, score, feedback_text)


def fetch_ratings_for_tab(content_id: str, clip_type: str) -> List[Dict]:
    try:
        resp = (
            _client()
            .table("ratings")
            .select("clip_id,content_id,clip_type,reviewer_email,score,feedback_text,submitted_at")
            .eq("content_id", content_id)
            .eq("clip_type", clip_type)
            .execute()
        )
    except Exception as exc:
        if not _is_schema_error(exc):
            raise
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


def fetch_all_ratings() -> List[Dict]:
    """Returns all rating rows, adding unique keys when older rows do not have them."""
    rows: List[Dict] = []
    start = 0
    page_size = 1000
    select_with_unique_key = (
        "unique_clip_key,clip_set_key,clip_id,content_id,clip_type,"
        "reviewer_email,score,feedback_text,submitted_at"
    )

    while True:
        try:
            resp = (
                _client()
                .table("ratings")
                .select(select_with_unique_key)
                .range(start, start + page_size - 1)
                .execute()
            )
        except Exception as exc:
            if not _is_schema_error(exc):
                raise
            try:
                resp = (
                    _client()
                    .table("ratings")
                    .select(
                        "unique_clip_key,clip_set_key,clip_id,content_id,clip_type,"
                        "reviewer_email,score,submitted_at"
                    )
                    .range(start, start + page_size - 1)
                    .execute()
                )
            except Exception as fallback_exc:
                if not _is_schema_error(fallback_exc):
                    raise
                resp = (
                    _client()
                    .table("ratings")
                    .select("clip_id,content_id,clip_type,reviewer_email,score,submitted_at")
                    .range(start, start + page_size - 1)
                    .execute()
                )
        page = resp.data or []
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size

    for row in rows:
        if row.get("content_id") and row.get("clip_type") and row.get("clip_id"):
            unique_clip_key = build_unique_clip_key(row["content_id"], row["clip_type"], row["clip_id"])
            row["unique_clip_key"] = row.get("unique_clip_key") or unique_clip_key
            row["clip_set_key"] = row.get("clip_set_key") or unique_clip_key.rsplit("::", 1)[0]
    return rows


def fetch_rating_summary() -> Dict[str, Dict[str, object]]:
    """Returns {unique_clip_key: {"avg": float, "count": int}} for all ratings."""
    rows = fetch_all_ratings()
    score_groups: Dict[str, List[int]] = {}
    for row in rows:
        if row.get("score") is None:
            continue
        key = row.get("unique_clip_key") or build_unique_clip_key(row["content_id"], row["clip_type"], row["clip_id"])
        score_groups.setdefault(key, []).append(int(row["score"]))

    return {
        key: {"avg": round(sum(scores) / len(scores), 2), "count": len(scores)}
        for key, scores in score_groups.items()
    }


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
