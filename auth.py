import streamlit as st


ALLOWED_DOMAINS = ("@jiostar.com", "@viacom18.com")


def _google_auth_configured() -> bool:
    try:
        auth = st.secrets.get("auth", {})
    except Exception:
        return False
    google = auth.get("google", {}) if hasattr(auth, "get") else {}
    client_id = google.get("client_id", "") if hasattr(google, "get") else ""
    client_secret = google.get("client_secret", "") if hasattr(google, "get") else ""
    return (
        bool(client_id)
        and bool(client_secret)
        and "YOUR_GOOGLE_CLIENT_ID" not in client_id
        and "YOUR_GOOGLE_CLIENT_SECRET" not in client_secret
    )


def is_allowed_email(email: str) -> bool:
    return any(email.lower().endswith(d) for d in ALLOWED_DOMAINS)


def is_admin(email: str) -> bool:
    admin_list = st.secrets.get("admin", {}).get("emails", [])
    return email.lower() in {e.lower() for e in admin_list}


def require_auth() -> str:
    """Gate access. Returns the authenticated email or stops the app."""
    if not getattr(st.user, "is_logged_in", False):
        st.title("Comet Clips Review")
        st.markdown("Sign in with your JioStar Google account to continue.")
        if _google_auth_configured() and st.button("Sign in with Google"):
            st.login("google")
        elif not _google_auth_configured():
            st.info("Google sign-in is not configured in local secrets yet.")
        st.stop()

    email = st.user.email
    if not is_allowed_email(email):
        st.error(
            f"Access restricted to JioStar accounts. "
            f"({email} is not authorised.)"
        )
        st.button("Sign out", on_click=st.logout)
        st.stop()

    return email
