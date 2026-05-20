#!/usr/bin/env bash
set -e

pip install -r requirements.txt

playwright install chromium

mkdir -p .streamlit

cat > .streamlit/secrets.toml <<EOF
GOOGLE_DRIVE_JSON_FOLDER_ID = "$GOOGLE_DRIVE_JSON_FOLDER_ID"
GOOGLE_DRIVE_PDF_FOLDER_ID = "$GOOGLE_DRIVE_PDF_FOLDER_ID"
GOOGLE_DRIVE_RECEIPT_FOLDER_ID = "$GOOGLE_DRIVE_RECEIPT_FOLDER_ID"

ADMIN_EMAIL = "$ADMIN_EMAIL"

[google_oauth_token]
token = "$GOOGLE_OAUTH_TOKEN"
refresh_token = "$GOOGLE_OAUTH_REFRESH_TOKEN"
token_uri = "https://oauth2.googleapis.com/token"
client_id = "$GOOGLE_OAUTH_CLIENT_ID"
client_secret = "$GOOGLE_OAUTH_CLIENT_SECRET"
scopes = ["https://www.googleapis.com/auth/drive"]

[auth]
redirect_uri = "$AUTH_REDIRECT_URI"
cookie_secret = "$AUTH_COOKIE_SECRET"
client_id = "$AUTH_CLIENT_ID"
client_secret = "$AUTH_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
EOF