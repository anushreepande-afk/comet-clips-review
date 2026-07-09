"""
Comet Clips Review — JioHotstar-themed Streamlit application.
Stakeholders rate video clips (1–10); ratings stored in Supabase.
"""
from __future__ import annotations

import html
import streamlit as st
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from auth import require_auth, is_admin
from clip_data import (
    OUTPUT_SET_LABELS,
    all_content_ids,
    clips_for,
    content_name_for,
    load_clips,
    manifest_for,
    output_sets_for,
    tier_for_score,
)
from db import upsert_rating, fetch_ratings_for_tab, fetch_my_ratings, fetch_rating_summary, fetch_all_ratings, avg_score_for_clips
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
        padding: 16px;
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
    /* tier badges */
    .badge-gold   { background:#92400e; color:#fef3c7; padding:2px 10px; border-radius:9999px; font-size:0.78rem; font-weight:700; }
    .badge-silver { background:#1e3a5f; color:#bfdbfe; padding:2px 10px; border-radius:9999px; font-size:0.78rem; font-weight:700; }
    .badge-bronze { background:#7c2d12; color:#fed7aa; padding:2px 10px; border-radius:9999px; font-size:0.78rem; font-weight:700; }
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
    /* score row progress bar (admin) */
    .reviewer-bar-bg {
        background: #2a2a2a;
        border-radius: 4px;
        height: 8px;
        flex: 1;
        margin: 0 8px;
    }
    .reviewer-bar-fill {
        border-radius: 4px;
        height: 8px;
        background: linear-gradient(90deg, #1a56db, #a855f7);
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
    .rating-heading {
        color: #f3f4f6;
        font-size: 1rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-top: 18px;
        margin-bottom: 8px;
    }
    .rating-band {
        font-size: 0.95rem;
        font-weight: 800;
    }
    div[data-testid="stButton"] button p {
        font-size: 1.05rem;
        font-weight: 700;
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TIER_BADGE: Dict[str, str] = {
    "Gold":   "badge-gold",
    "Silver": "badge-silver",
    "Bronze": "badge-bronze",
}

def badge_html(tier: str) -> str:
    css = TIER_BADGE.get(tier, "badge-bronze")
    return f'<span class="{css}">{tier}</span>'

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

def _score_btn(val: int, score_key: str) -> None:
    ss[score_key] = val

def _render_reviewer_row(row: Dict) -> None:
    rev_email: str = row["reviewer_email"]
    rev_score: int = row["score"]
    rev_tier = tier_for_score(rev_score)
    rev_name = rev_email.split("@")[0]
    safe_rev_name = html.escape(rev_name)
    safe_rev_email = html.escape(rev_email)
    bar_pct = int(rev_score / 10 * 100)
    st.markdown(
        f'<div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">'
        f'<span style="color:#d1d5db; font-size:0.82rem; width:90px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{safe_rev_email}">{safe_rev_name}</span>'
        f'<div class="reviewer-bar-bg">'
        f'<div class="reviewer-bar-fill" style="width:{bar_pct}%;"></div>'
        f'</div>'
        f'<span style="color:#f0f0f0; font-weight:700; font-size:0.85rem; width:20px; text-align:right;">{rev_score}</span>'
        f'&nbsp;{badge_html(rev_tier)}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Fetch data once (before sidebar and main area reuse)
# ---------------------------------------------------------------------------
clips: List[Dict] = clips_for(ss.content_id, ss.clip_type)
n_clips = len(clips)
current_manifest: Optional[Dict] = manifest_for(ss.content_id, ss.clip_type)

my_ratings: Dict[str, int] = {}
all_ratings: List[Dict] = []
_avg_map: Dict[str, Optional[float]] = {}

if n_clips > 0:
    my_ratings = fetch_my_ratings(email, ss.content_id, ss.clip_type)
    all_ratings = fetch_ratings_for_tab(ss.content_id, ss.clip_type)

    # Pre-compute avg scores per clip_id (O(N) instead of O(N²))
    _score_groups: Dict[str, list] = defaultdict(list)
    for r in all_ratings:
        if r["content_id"] == ss.content_id and r["clip_type"] == ss.clip_type:
            _score_groups[r["clip_id"]].append(r["score"])
    for cid, scores in _score_groups.items():
        _avg_map[cid] = round(sum(scores) / len(scores), 1)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="logo-gradient">Comet Clips Review</div>', unsafe_allow_html=True)
    st.caption(f"Signed in as **{email}**")
    if st.button("Sign out", key="signout_btn"):
        st.logout()

    st.divider()

    # Content ID selector
    content_id_idx = content_ids.index(ss.content_id) if ss.content_id in content_ids else 0
    chosen_cid = st.selectbox(
        "Content",
        options=content_ids,
        index=content_id_idx,
        format_func=lambda cid: f"{content_name_for(cid)} ({cid})",
        key="_sidebar_content_id",
    )
    if chosen_cid != ss.content_id:
        ss.content_id = chosen_cid
        ss.active_idx = 0
        available_sets = output_sets_for(chosen_cid)
        ss.clip_type = available_sets[0] if available_sets else "cliffhanger_pro"
        st.rerun()

    # Output set radio
    output_options = output_sets_for(ss.content_id)
    if ss.clip_type not in output_options and output_options:
        ss.clip_type = output_options[0]
    chosen_type = st.radio(
        "Output set",
        options=output_options,
        index=output_options.index(ss.clip_type) if ss.clip_type in output_options else 0,
        key="_sidebar_clip_type",
        format_func=lambda clip_type: OUTPUT_SET_LABELS.get(clip_type, clip_type),
    )
    if chosen_type != ss.clip_type:
        ss.clip_type = chosen_type
        ss.active_idx = 0
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

            # Build label depending on active tab
            if ss.active_tab == "admin":
                avg = _avg_map.get(cid)
                if avg is not None:
                    label = f"{'▶ ' if is_active else ''}{cid}  ·  {avg}"
                else:
                    label = f"{'▶ ' if is_active else ''}{cid}"
            else:
                if cid in my_ratings:
                    label = f"✓ {cid}  ·  {my_ratings[cid]}"
                elif is_active:
                    label = f"▶ {cid}"
                else:
                    label = cid

            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{ss.content_id}_{ss.clip_type}_{idx}", use_container_width=True, type=btn_type):
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
tier_clip: str = clip.get("tier", "Bronze")
score_algo: int = int(clip.get("score", 0))
watch_prob: int = int(clip.get("watch_prob", 0))

# Pre-fill session state score from existing rating (do once per clip load)
score_key = f"score_{ss.content_id}_{ss.clip_type}_{clip_id}"
if score_key not in ss and clip_id in my_ratings:
    ss[score_key] = my_ratings[clip_id]

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_labels = ["Reviewer view"]
if admin:
    tab_labels.append("Admin view (restricted)")

tabs = st.tabs(tab_labels)

# ── REVIEWER TAB ────────────────────────────────────────────────────────────
with tabs[0]:
    ss.active_tab = "reviewer"

    # Flash message
    if ss.flash:
        st.markdown(
            f'<div class="flash-success">{ss.flash}</div>',
            unsafe_allow_html=True,
        )
        ss.flash = None

    col_vid, col_panel = st.columns([3, 2])

    with col_vid:
        st.markdown(drive_embed_html(file_id), unsafe_allow_html=True)

    with col_panel:
        st.markdown('<div class="clip-card">', unsafe_allow_html=True)

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

        # Current rating badge (if already rated)
        existing_score: Optional[int] = my_ratings.get(clip_id)
        if existing_score is not None:
            existing_tier = tier_for_score(existing_score)
            st.markdown(
                f'<div style="margin-top:12px;" class="section-label">Your current rating</div>'
                f'<div style="margin-top:4px;">'
                f'<span style="font-size:1.5rem; font-weight:800; color:#f0f0f0;">{existing_score}</span>'
                f'&nbsp;&nbsp;{badge_html(existing_tier)}'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="rating-heading">Rate this clip</div>', unsafe_allow_html=True)

        # Rating buttons — 3 groups
        selected_score: Optional[int] = ss.get(score_key)

        # Bronze 1–3
        st.markdown("<span class='rating-band' style='color:#fed7aa;'>Bronze · 1–3</span>", unsafe_allow_html=True)
        bronze_cols = st.columns(3)
        for i, val in enumerate([1, 2, 3]):
            btn_t = "primary" if selected_score == val else "secondary"
            if bronze_cols[i].button(str(val), key=f"btn_{ss.content_id}_{ss.clip_type}_{clip_id}_{val}", type=btn_t, use_container_width=True):
                _score_btn(val, score_key)
                st.rerun()

        # Silver 4–6
        st.markdown("<span class='rating-band' style='color:#bfdbfe;'>Silver · 4–6</span>", unsafe_allow_html=True)
        silver_cols = st.columns(3)
        for i, val in enumerate([4, 5, 6]):
            btn_t = "primary" if selected_score == val else "secondary"
            if silver_cols[i].button(str(val), key=f"btn_{ss.content_id}_{ss.clip_type}_{clip_id}_{val}", type=btn_t, use_container_width=True):
                _score_btn(val, score_key)
                st.rerun()

        # Gold 7–10
        st.markdown("<span class='rating-band' style='color:#fef3c7;'>Gold · 7–10</span>", unsafe_allow_html=True)
        gold_cols = st.columns(4)
        for i, val in enumerate([7, 8, 9, 10]):
            btn_t = "primary" if selected_score == val else "secondary"
            if gold_cols[i].button(str(val), key=f"btn_{ss.content_id}_{ss.clip_type}_{clip_id}_{val}", type=btn_t, use_container_width=True):
                _score_btn(val, score_key)
                st.rerun()

        # Submit button
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        submit_disabled = selected_score is None
        if st.button(
            "Submit rating",
            key=f"submit_{ss.content_id}_{ss.clip_type}_{clip_id}",
            type="primary",
            disabled=submit_disabled,
            use_container_width=True,
        ):
            score_to_save = int(selected_score)  # type: ignore[arg-type]
            tier_saved = tier_for_score(score_to_save)
            try:
                upsert_rating(clip_id, ss.content_id, ss.clip_type, email, score_to_save, clip=clip)
            except Exception:
                st.error(
                    "Could not save this rating. Please rerun supabase_unique_clips.sql in Supabase, "
                    "then choose Run without RLS."
                )
                st.stop()
            # Update local cache
            my_ratings[clip_id] = score_to_save
            ss.flash = f"Saved — {score_to_save} ({tier_saved})"
            # Advance to next unrated clip
            ss.active_idx = next_unrated_idx(clips, my_ratings, ss.active_idx)
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)  # close clip-card

# ── ADMIN TAB ───────────────────────────────────────────────────────────────
if admin and len(tabs) > 1:
    with tabs[1]:
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
            "Download average ratings",
            data=avg_export_bytes,
            file_name=f"comet_clip_average_ratings_{export_stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        individual_col.download_button(
            "Download individual ratings",
            data=individual_export_bytes,
            file_name=f"comet_clip_individual_ratings_{export_stamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.divider()

        col_vid2, col_panel2 = st.columns([3, 2])

        with col_vid2:
            st.markdown(drive_embed_html(file_id), unsafe_allow_html=True)

        with col_panel2:
            st.markdown('<div class="clip-card">', unsafe_allow_html=True)

            # Header
            safe_clip_id2 = html.escape(clip_id)
            type_label2 = OUTPUT_SET_LABELS.get(ss.clip_type, ss.clip_type)
            safe_type_label2 = html.escape(type_label2)
            st.markdown(
                f"<span style='font-size:1.1rem; font-weight:700;'>{safe_clip_id2}</span> "
                f"<span style='color:#9ca3af; font-size:0.85rem;'>{safe_type_label2}</span>",
                unsafe_allow_html=True,
            )

            # Algorithm score card
            st.markdown('<div class="section-label" style="margin-top:12px;">Algorithm score</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:12px; margin-top:4px;">'
                f'<span style="font-size:2rem; font-weight:900; color:#f0f0f0;">{score_algo}</span>'
                f'{badge_html(tier_clip)}'
                f'<span style="color:#9ca3af; font-size:0.85rem;">Watch prob: <strong style="color:#f0f0f0;">{watch_prob}%</strong></span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.divider()

            # Per-reviewer ratings
            clip_ratings = [
                r for r in all_ratings
                if r["clip_id"] == clip_id
                and r["content_id"] == ss.content_id
                and r["clip_type"] == ss.clip_type
            ]

            avg = _avg_map.get(clip_id)

            st.markdown('<div class="section-label">Reviewer ratings</div>', unsafe_allow_html=True)

            if not clip_ratings:
                st.markdown('<span style="color:#6b7280; font-size:0.85rem;">No ratings yet.</span>', unsafe_allow_html=True)
            else:
                visible = clip_ratings[:15]
                overflow = clip_ratings[15:]

                for row in visible:
                    _render_reviewer_row(row)

                if overflow:
                    with st.expander(f"More ({len(overflow)})"):
                        for row in overflow:
                            _render_reviewer_row(row)

                # Average (always visible when ratings exist)
                st.markdown(
                    f'<div style="margin-top:10px; display:flex; align-items:center; gap:8px;">'
                    f'<span class="section-label" style="margin-bottom:0;">Average</span>'
                    f'<span style="font-size:1.4rem; font-weight:800; color:#f0f0f0;">{avg}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)  # close clip-card
