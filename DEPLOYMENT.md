# Deployment Notes

## Streamlit Cloud access

If the app URL redirects between `share.streamlit.io/-/auth/app` and the app URL,
the app is being blocked by Streamlit Cloud's own sharing/access gate before
the Comet Clips Review code runs.

Fix this in Streamlit Cloud:

1. Open the app settings.
2. Go to sharing/access settings.
3. Make the app public, or add the intended viewer accounts.

## Google sign-in secrets

For production, set this redirect URI in Streamlit Cloud secrets:

```toml
[auth]
redirect_uri = "https://comet-clips-review-dwlntpkrwbkr5ia4r6chsc.streamlit.app/oauth2callback"
cookie_secret = "replace-with-a-random-32-plus-character-string"

[auth.google]
client_id = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
```

The same production redirect URI must also be added to the Google OAuth
client's authorized redirect URIs.
