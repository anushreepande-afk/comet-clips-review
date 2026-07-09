"""
Comet Clips Review — JioHotstar-themed Streamlit application.
Stakeholders accept or reject video clips; decisions are stored in Supabase.
"""
from __future__ import annotations

import html
import streamlit as st
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from auth import require_auth, is_admin
from clip_data import (
    OUTPUT_SET_LABELS,
    all_content_ids,
    clips_for,
    content_name_for,
    load_clips,
    manifest_for,
    output_sets_for,
)
from db import upsert_rating, fetch_ratings_for_tab, fetch_my_ratings, fetch_rating_summary, fetch_all_ratings
from excel_export import build_individual_ratings_workbook, build_rating_export_workbook

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Comet Clips Review",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS — JioHotstar dark theme
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ── base ── */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0e0e0e;
        color: #f0f0f0;
    }
    [data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #2a2a2a;
    }
    /* cards / surfaces */
    .clip-card {
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        padding: 12px;
    }
    /* gradient logo text */
    .logo-gradient {
        background: linear-gradient(90deg, #1a56db, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin-bottom: 4px;
    }
    /* decision badges */
    .badge-accept { background:#064e3b; color:#a7f3d0; padding:2px 10px; border-radius:9999px; font-size:0.78rem; font-weight:800; }
    .badge-reject { background:#7f1d1d; color:#fecaca; padding:2px 10px; border-radius:9999px; font-size:0.78rem; font-weight:800; }
    /* video wrapper — 16:9 */
    .video-wrapper {
        position: relative;
        width: 100%;
        padding-bottom: 56.25%;
        border-radius: 10px;
        overflow: hidden;
        background: #000;
    }
    .video-wrapper iframe {
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        border: none;
        border-radius: 10px;
    }
    /* submit flash */
    .flash-success {
        background: linear-gradient(90deg, #16a34a, #15803d);
        color: #fff;
        padding: 10px 16px;
        border-radius: 8px;
        font-weight: 600;
        margin-bottom: 12px;
    }
    /* misc */
    .section-label {
        color: #9ca3af;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .desc-text {
        color: #d1d5db;
        font-size: 0.92rem;
        line-height: 1.6;
        margin-top: 4px;
    }
    .content-context {
        color: #d1d5db;
        font-size: 1.08rem;
        font-weight: 700;
        margin-top: 6px;
    }
    .content-select-label {
        color: #f3f4f6;
        font-size: 1.12rem;
        font-weight: 800;
        line-height: 1.25;
        margin-bottom: 5px;
    }
    [data-testid="stExpander"] details summary p {
        background: linear-gradient(90deg, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 900;
    }
    [data-testid="stExpander"] details summary {
        border: 1px solid rgba(168, 85, 247, 0.4);
        border-radius: 8px;
        background: linear-gradient(90deg, rgba(168, 85, 247, 0.12), rgba(236, 72, 153, 0.08));
    }
    .rating-heading {
        color: #f3f4f6;
        font-size: 0.86rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-top: 10px;
        margin-bottom: 4px;
    }
    div[data-testid="stButton"] button p {
        font-size: 1.05rem;
        font-weight: 700;
    }
    .decision-row {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:8px;
        margin-top:8px;
        margin-bottom:4px;
    }
    .decision-row .section-label {
        margin-bottom:0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
email: str = require_auth()
admin: bool = is_admin(email)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
content_ids = all_content_ids()

_defaults: Dict = {
    "content_id": content_ids[0],
    "clip_type":  "cliffhanger_pro",
    "active_idx": 0,
    "flash":      None,
    "active_tab": "reviewer",
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

ss = st.session_state
output_options = output_sets_for(ss.content_id)
if ss.clip_type not in output_options and output_options:
    ss.clip_type = output_options[0]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
ACCEPT_SCORE = 1
REJECT_SCORE = 0

def decision_from_score(score: Optional[int]) -> str:
    if score is None:
        return ""
    return "Accept" if int(score) == ACCEPT_SCORE else "Reject"

def badge_html(decision: str) -> str:
    css = "badge-accept" if decision == "Accept" else "badge-reject"
    return f'<span class="{css}">{decision}</span>'

def drive_embed_html(file_id: str) -> str:
    if not file_id:
        return (
            '<div class="video-wrapper" style="display:flex;align-items:center;justify-content:center;color:#9ca3af;">'
            "Clip file unavailable"
            "</div>"
        )
    src = f"https://drive.google.com/file/d/{file_id}/preview"
    return (
        '<div class="video-wrapper">'
        f'<iframe src="{src}" allow="autoplay; encrypted-media" allowfullscreen></iframe>'
        '</div>'
    )

def next_unrated_idx(
    clips: List[Dict],
    my_ratings: Dict[str, int],
    current_idx: int,
) -> int:
    """Scan forward (wrapping) from current_idx for the next unrated clip."""
    n = len(clips)
    for offset in range(1, n + 1):
        idx = (current_idx + offset) % n
        if clips[idx]["clip_id"] not in my_ratings:
            return idx
    # All rated — stay on current
    return current_idx

def _render_reviewer_row(row: Dict) -> None:
    rev_email: str = row["reviewer_email"]
    decision = decision_from_score(row.get("score"))
    rev_name = rev_email.split("@")[0]
    safe_rev_name = html.escape(rev_name)
    safe_rev_email = html.escape(rev_email)
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">'
        f'<span style="color:#d1d5db; font-size:0.82rem; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{safe_rev_email}">{safe_rev_name}</span>'
        f'{badge_html(decision)}'
        f'</div>',
        unsafe_allow_html=True,
    )

def _review_targets() -> List[Tuple[str, str]]:
    targets: List[Tuple[str, str]] = []
    for content_id in content_ids:
        for clip_type in output_sets_for(content_id):
            if clips_for(content_id, clip_type):
                targets.append((content_id, clip_type))
    return targets

def _move_clip(delta: int, rerun: bool = True) -> None:
    if n_clips == 0:
        return

    if delta > 0 and ss.active_idx < n_clips - 1:
        ss.active_idx += 1
    elif delta < 0 and ss.active_idx > 0:
        ss.active_idx -= 1
    else:
        targets = _review_targets()
        current_target = (ss.content_id, ss.clip_type)
        if current_target in targets:
            current_target_idx = targets.index(current_target)
            next_target_idx = current_target_idx + (1 if delta > 0 else -1)
            if 0 <= next_target_idx < len(targets):
                ss.content_id, ss.clip_type = targets[next_target_idx]
                target_clips = clips_for(ss.content_id, ss.clip_type)
                ss.active_idx = 0 if delta > 0 else max(len(target_clips) - 1, 0)
            else:
                ss.active_idx = n_clips - 1 if delta > 0 else 0
        else:
            ss.active_idx = 0

    if rerun:
        st.rerun()

# ---------------------------------------------------------------------------
# Fetch data once (before sidebar and main area reuse)
# ---------------------------------------------------------------------------
clips: List[Dict] = clips_for(ss.content_id, ss.clip_type)
n_clips = len(clips)
current_manifest: Optional[Dict] = manifest_for(ss.content_id, ss.clip_type)

my_ratings: Dict[str, int] = {}
all_ratings: List[Dict] = []
decision_summary: Dict[str, Dict[str, int]] = {}

if n_clips > 0:
    my_ratings = fetch_my_ratings(email, ss.content_id, ss.clip_type)
    all_ratings = fetch_ratings_for_tab(ss.content_id, ss.clip_type)
    for r in all_ratings:
        if r["content_id"] == ss.content_id and r["clip_type"] == ss.clip_type:
            row = decision_summary.setdefault(r["clip_id"], {"accept": 0, "reject": 0})
            if int(r["score"]) == ACCEPT_SCORE:
                row["accept"] += 1
            else:
                row["reject"] += 1

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="logo-gradient">Comet Clips Review</div>', unsafe_allow_html=True)
    st.caption(f"Signed in as **{email}**")
    if st.button(
        "Sign out",
        key="signout_btn",
        help="Sign out of the review app.",
    ):
        st.logout()

    st.divider()

    # Content ID selector
    ss.pop("_sidebar_content_id", None)
    ss.pop("_pending_sidebar_content_id", None)

    content_id_idx = content_ids.index(ss.content_id) if ss.content_id in content_ids else 0
    st.markdown('<div class="content-select-label">Select content id to review</div>', unsafe_allow_html=True)
    chosen_cid = st.selectbox(
        "Select content id to review",
        options=content_ids,
        index=content_id_idx,
        format_func=lambda cid: f"{content_name_for(cid)} ({cid})",
        help="Choose the content title whose clips you want to review.",
        label_visibility="collapsed",
    )
    if chosen_cid != ss.content_id:
        ss.content_id = chosen_cid
        ss.active_idx = 0
        available_sets = output_sets_for(chosen_cid)
        ss.clip_type = available_sets[0] if available_sets else "cliffhanger_pro"
        st.rerun()

    st.divider()

    if n_clips == 0:
        st.info("No clips for this selection.")
    else:
        rated_count = sum(1 for c in clips if c["clip_id"] in my_ratings)

        st.markdown('<div class="section-label">Clips</div>', unsafe_allow_html=True)
        for idx, clip in enumerate(clips):
            cid = clip["clip_id"]
            is_active = idx == ss.active_idx

            # Keep clip navigation free of submitted decision values.
            if ss.active_tab == "admin":
                label = f"{'▶ ' if is_active else ''}{cid}"
            else:
                if cid in my_ratings:
                    label = f"✓ {cid}"
                elif is_active:
                    label = f"▶ {cid}"
                else:
                    label = cid

            is_reviewed = cid in my_ratings and ss.active_tab != "admin"
            btn_type = "primary" if is_reviewed else "secondary"
            if st.button(
                label,
                key=f"nav_{ss.content_id}_{ss.clip_type}_{idx}",
                use_container_width=True,
                type=btn_type,
                help=f"Jump to {cid} in the current version.",
            ):
                ss.active_idx = idx
                st.rerun()

        st.divider()
        # Progress bar
        progress = rated_count / n_clips if n_clips > 0 else 0.0
        st.progress(progress, text=f"Rated {rated_count} / {n_clips}")

# ---------------------------------------------------------------------------
# Main area — guard against empty clip list
# ---------------------------------------------------------------------------
if n_clips == 0:
    st.title("Comet Clips Review")
    content_label = f"{content_name_for(ss.content_id)} ({ss.content_id})"
    output_label = OUTPUT_SET_LABELS.get(ss.clip_type, ss.clip_type)
    st.warning(f"No playable clips found for {content_label} · {output_label}.")
    if current_manifest and current_manifest.get("source_status") != "OK":
        st.info(f"Source status: {current_manifest['source_status']}")
    st.stop()

# Clamp active_idx
if ss.active_idx >= n_clips:
    ss.active_idx = 0

clip = clips[ss.active_idx]
clip_id: str = clip["clip_id"]
file_id: str = clip["drive_file_id"]

decision_key = f"decision_{ss.content_id}_{ss.clip_type}_{clip_id}"
if decision_key not in ss and clip_id in my_ratings:
    ss[decision_key] = decision_from_score(my_ratings[clip_id])

# ---------------------------------------------------------------------------
# Reviewer view
# ---------------------------------------------------------------------------
ss.active_tab = "reviewer"

# Flash message
if ss.flash:
    st.markdown(
        f'<div class="flash-success">{ss.flash}</div>',
        unsafe_allow_html=True,
    )
    ss.flash = None

if output_options:
    ribbon_cols = st.columns(len(output_options))
    for idx, option in enumerate(output_options):
        label = OUTPUT_SET_LABELS.get(option, option)
        btn_type = "primary" if option == ss.clip_type else "secondary"
        if ribbon_cols[idx].button(
            label,
            key=f"ribbon_{ss.content_id}_{option}",
            type=btn_type,
            use_container_width=True,
            help=f"Switch to {label} for this content.",
        ):
            ss.clip_type = option
            ss.active_idx = 0
            st.rerun()

col_vid, col_panel = st.columns([4.4, 1.35])

with col_vid:
    st.markdown(drive_embed_html(file_id), unsafe_allow_html=True)
    nav_left, nav_counter, nav_right = st.columns([1, 1.2, 1])
    if nav_left.button(
        "‹ Previous",
        key=f"prev_{ss.content_id}_{ss.clip_type}_{clip_id}",
        use_container_width=True,
        help="Go to the previous clip. At the start of a version, this moves to the previous version or previous content.",
    ):
        _move_clip(-1)
    nav_counter.markdown(
        f"<div style='text-align:center;color:#9ca3af;font-weight:700;padding-top:0.45rem;'>{ss.active_idx + 1} / {n_clips}</div>",
        unsafe_allow_html=True,
    )
    if nav_right.button(
        "Next ›",
        key=f"next_{ss.content_id}_{ss.clip_type}_{clip_id}",
        use_container_width=True,
        help="Go to the next clip. At the end of a version, this moves to the next version or next content.",
    ):
        _move_clip(1)

with col_panel:
    # Header row: clip id + type label
    safe_clip_id = html.escape(clip_id)
    type_label = OUTPUT_SET_LABELS.get(ss.clip_type, ss.clip_type)
    safe_type_label = html.escape(type_label)
    safe_content_name = html.escape(clip.get("content_name", content_name_for(ss.content_id)))
    st.markdown(
        f"<span style='font-size:1.25rem; font-weight:800;'>{safe_clip_id}</span> "
        f"<span style='color:#9ca3af; font-size:1rem;'>{safe_type_label}</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='content-context'>{safe_content_name} · {html.escape(ss.content_id)}</div>",
        unsafe_allow_html=True,
    )

    if clip.get("source_status") and clip.get("source_status") != "OK":
        st.warning(f"Source status: {clip['source_status']}")

    # Genre badge: use only the Genre CMS value from the source JSON.
    st.markdown('<div class="section-label" style="margin-top:10px;">Genre CMS</div>', unsafe_allow_html=True)
    genre = clip.get("genre_cms") or "—"
    safe_genre = html.escape(str(genre))
    st.markdown(
        f'<span style="background:#1f2937;color:#e5e7eb;border-radius:5px;padding:4px 12px;font-size:14px;font-weight:700;">{safe_genre}</span>',
        unsafe_allow_html=True,
    )

    # Description
    st.markdown('<div class="section-label" style="margin-top:10px;">Description</div>', unsafe_allow_html=True)
    safe_desc = html.escape(clip.get("description", ""))
    st.markdown(f'<div class="desc-text">{safe_desc}</div>', unsafe_allow_html=True)

    # Current decision badge (if already reviewed)
    existing_score: Optional[int] = my_ratings.get(clip_id)
    if existing_score is not None:
        current_decision = decision_from_score(existing_score)
        current_decision_html = badge_html(current_decision)
    else:
        current_decision_html = '<span style="color:#6b7280;font-size:0.82rem;font-weight:700;">Not reviewed</span>'

    st.markdown(
        f'<div class="decision-row">'
        f'<div class="section-label">Decision</div>'
        f'{current_decision_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    decision_cols = st.columns(2, gap="small")
    actions = [("Accept", ACCEPT_SCORE), ("Reject", REJECT_SCORE)]
    for col, (decision, score_to_save) in zip(decision_cols, actions):
        if col.button(
            decision,
            key=f"decision_{ss.content_id}_{ss.clip_type}_{clip_id}_{decision.lower()}",
            type="primary" if decision == "Accept" else "secondary",
            use_container_width=True,
            help=f"Save this clip as {decision} and move to the next clip.",
        ):
            try:
                upsert_rating(
                    clip_id,
                    ss.content_id,
                    ss.clip_type,
                    email,
                    score_to_save,
                    clip=clip,
                )
            except Exception:
                st.error(
                    "Could not save this decision. If Reject is failing, run the updated "
                    "Supabase setup SQL so decisions can be stored as Accept = 1 and Reject = 0."
                )
                st.stop()
            my_ratings[clip_id] = score_to_save
            ss[decision_key] = decision
            ss.flash = f"Saved — {decision}"
            _move_clip(1, rerun=False)
            st.rerun()

# ── ADMIN SECTION ───────────────────────────────────────────────────────────
if admin:
    with st.expander("Admin view (restricted)", expanded=False):
        ss.active_tab = "admin"

        st.markdown('<div class="section-label">Excel export</div>', unsafe_allow_html=True)
        rating_summary = fetch_rating_summary()
        individual_ratings = fetch_all_ratings()
        all_clips = load_clips()
        export_stamp = datetime.now().strftime("%Y%m%d_%H%M")
        avg_export_bytes = build_rating_export_workbook(all_clips, rating_summary)
        individual_export_bytes = build_individual_ratings_workbook(all_clips, individual_ratings)
        avg_col, individual_col = st.columns(2)
        avg_col.download_button(
            "Download decision summary",
            data=avg_export_bytes,
            file_name=f"comet_clip_decision_summary_{export_stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Download clip-level Accept/Reject counts and acceptance rate.",
        )
        individual_col.download_button(
            "Download individual decisions",
            data=individual_export_bytes,
            file_name=f"comet_clip_individual_decisions_{export_stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            help="Download each reviewer decision with content, version, and clip link details.",
        )

        st.divider()

        col_vid2, col_panel2 = st.columns([4.4, 1.35])

        with col_vid2:
            st.markdown(drive_embed_html(file_id), unsafe_allow_html=True)

        with col_panel2:
            # Header
            safe_clip_id2 = html.escape(clip_id)
            type_label2 = OUTPUT_SET_LABELS.get(ss.clip_type, ss.clip_type)
            safe_type_label2 = html.escape(type_label2)
            st.markdown(
                f"<span style='font-size:1.1rem; font-weight:700;'>{safe_clip_id2}</span> "
                f"<span style='color:#9ca3af; font-size:0.85rem;'>{safe_type_label2}</span>",
                unsafe_allow_html=True,
            )

            # Decision summary
            summary = decision_summary.get(clip_id, {"accept": 0, "reject": 0})
            total_decisions = summary["accept"] + summary["reject"]
            acceptance_rate = round(summary["accept"] / total_decisions * 100) if total_decisions else 0
            st.markdown('<div class="section-label" style="margin-top:12px;">Decision summary</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:4px;">'
                f'<span class="badge-accept">Accept {summary["accept"]}</span>'
                f'<span class="badge-reject">Reject {summary["reject"]}</span>'
                f'<span style="color:#9ca3af; font-size:0.85rem;">Acceptance: <strong style="color:#f0f0f0;">{acceptance_rate}%</strong></span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.divider()

            # Per-reviewer decisions
            clip_ratings = [
                r for r in all_ratings
                if r["clip_id"] == clip_id
                and r["content_id"] == ss.content_id
                and r["clip_type"] == ss.clip_type
            ]

            st.markdown('<div class="section-label">Reviewer decisions</div>', unsafe_allow_html=True)

            if not clip_ratings:
                st.markdown('<span style="color:#6b7280; font-size:0.85rem;">No decisions yet.</span>', unsafe_allow_html=True)
            else:
                visible = clip_ratings[:15]
                overflow = clip_ratings[15:]

                for row in visible:
                    _render_reviewer_row(row)

                if overflow:
                    with st.expander(f"More ({len(overflow)})"):
                        for row in overflow:
                            _render_reviewer_row(row)
