import streamlit as st


ALLOWED_DOMAINS = ("@jiostar.com", "@viacom18.com")


def is_allowed_email(email: str) -> bool:
    return any(email.lower().endswith(d) for d in ALLOWED_DOMAINS)


def is_admin(email: str) -> bool:
    admin_list = st.secrets.get("admin", {}).get("emails", [])
    return email.lower() in [e.lower() for e in admin_list]


def require_auth() -> str:
    """Gate access. Returns the authenticated email or stops the app."""
    if not st.user.is_logged_in:
        st.title("Comet Clips Review")
        st.markdown("Sign in with your JioStar Google account to continue.")
        st.button("Sign in with Google", on_click=st.login, args=["google"])
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
