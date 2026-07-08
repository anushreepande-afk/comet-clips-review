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

## Supabase unique clip rating storage

Ratings are saved in Supabase when a reviewer clicks Submit rating. To store
each rating against one unique clip record, run `supabase_unique_clips.sql` once
in the Supabase SQL Editor. The hierarchy is:

```text
content_id x prompt x model -> clip_id -> reviewer rating
```

After this is applied, every submitted rating also upserts a row in `clip_sets`,
upserts a row in `clips`, and saves the rating against
`ratings.unique_clip_key`.

## Excel rating exports

Admins can download a fresh Excel workbook from the app's Admin view using
`Download Excel with average ratings`.

To update an existing visualization workbook instead, run:

```bash
python update_excel_with_ratings.py /path/to/input.xlsx /path/to/output.xlsx
```

The script adds or updates `Unique Clip Key`, `Avg User Rating`, and
`Rating Count` columns in tabs that contain `content_id` and `clip_id`.
