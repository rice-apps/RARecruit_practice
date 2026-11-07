"""Google OAuth login endpoints built with FastAPI.

Run locally:
    .venv/bin/uvicorn login:app --host localhost --port 8080 --reload

Then open http://localhost:8080/login in a browser.

Endpoints:
    GET /                -> health check + links
    GET /login           -> redirects to Google's sign-in page
    GET /oauth2callback  -> Google redirects back here; we verify and log the user in
    GET /me              -> the logged-in user's profile (401 if not logged in)
    GET /logout          -> clears the session
"""

import os
import secrets
from pathlib import Path

import google.auth.transport.requests
import google_auth_oauthlib.flow
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from google.oauth2 import id_token
from starlette.middleware.sessions import SessionMiddleware

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "env.env")

# Google allows plain http only for localhost during development.
# Do NOT set this in production (production must use https).
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
# Google returns "openid email profile" as full URLs, which oauthlib would
# otherwise treat as a scope change and reject.
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", str(BASE_DIR / "secret.json"))

# Must exactly match one of the redirect URIs registered in the Google Cloud
# console (secret.json lists http://localhost:8080/oauth2callback).
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8080/oauth2callback")

# Only ask for what login needs: who the user is and their email.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

# Signs the session cookie. Set SESSION_SECRET in env.env so sessions survive
# restarts; otherwise a random one is generated each time the server starts.
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_urlsafe(32)

app = FastAPI(title="RARecruit Login")
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=False,  # set True once served over https
)


def make_flow(state: str | None = None, code_verifier: str | None = None):
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        code_verifier=code_verifier,
        # Generate a PKCE verifier only when starting a new login.
        autogenerate_code_verifier=code_verifier is None,
    )
    flow.redirect_uri = REDIRECT_URI
    return flow


@app.get("/")
def index(request: Request):
    return {
        "status": "ok",
        "logged_in": "user" in request.session,
        "links": {"login": "/login", "me": "/me", "logout": "/logout"},
    }


@app.get("/login")
def login(request: Request):
    flow = make_flow()
    authorization_url, state = flow.authorization_url(
        access_type="online",
        include_granted_scopes="true",
        prompt="select_account",
    )
    # Remember these so the callback can prove the response is for this login.
    request.session["oauth_state"] = state
    request.session["code_verifier"] = flow.code_verifier
    return RedirectResponse(authorization_url)


@app.get("/oauth2callback")
def oauth2callback(request: Request):
    if "error" in request.query_params:
        raise HTTPException(400, f"Google sign-in failed: {request.query_params['error']}")

    expected_state = request.session.pop("oauth_state", None)
    code_verifier = request.session.pop("code_verifier", None)
    if not expected_state or request.query_params.get("state") != expected_state:
        raise HTTPException(400, "Invalid or expired login state. Start again at /login.")

    flow = make_flow(state=expected_state, code_verifier=code_verifier)
    try:
        flow.fetch_token(authorization_response=str(request.url))
    except Exception as exc:
        raise HTTPException(400, f"Could not exchange the code with Google: {exc}") from exc

    # Verify the ID token's signature, issuer, expiry and that it was issued to our app.
    try:
        claims = id_token.verify_oauth2_token(
            flow.credentials.id_token,
            google.auth.transport.requests.Request(),
            audience=flow.client_config["client_id"],
        )
    except ValueError as exc:
        raise HTTPException(401, f"Invalid ID token: {exc}") from exc

    request.session["user"] = {
        "id": claims["sub"],
        "email": claims.get("email"),
        "email_verified": claims.get("email_verified", False),
        "name": claims.get("name"),
        "picture": claims.get("picture"),
    }
    return RedirectResponse("/me")


@app.get("/me")
def me(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(401, "Not logged in. Go to /login.")
    return user


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "logged out"}
