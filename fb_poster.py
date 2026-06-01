import json
import os
import re
import sqlite3
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv(override=True)

DB_PATH = "content.db"
GRAPH_BASE = "https://graph.facebook.com/v19.0"
ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")


def _page_id() -> str:
    return os.environ["FB_PAGE_ID"]


def _token() -> str:
    return os.environ["FB_ACCESS_TOKEN"]


def post_to_facebook(content: dict, format: str) -> str | None:
    page_id = _page_id()
    token = _token()
    url = f"{GRAPH_BASE}/{page_id}/feed"

    try:
        if format == "text_post":
            hashtags = " ".join(content.get("hashtags", []))
            message = f"{content['post_text']}\n\n{hashtags}".strip()
            params = {"message": message, "access_token": token}

        elif format == "carousel":
            slides = content.get("slides", [])
            slide_text = "\n\n".join(
                f"Slide {i+1}: {s['headline']}\n{s['body']}"
                for i, s in enumerate(slides)
            )
            hashtags = " ".join(content.get("hashtags", []))
            caption = content.get("caption", "")
            message = f"{caption}\n\n{slide_text}\n\n{hashtags}".strip()
            params = {"message": message, "access_token": token}

        elif format == "reel_script":
            hashtags = " ".join(content.get("hashtags", []))
            caption = content.get("caption", "")
            hook = content.get("hook", "")
            body = content.get("body", "")
            cta = content.get("cta", "")
            message = (
                f"[REEL SCRIPT]\n\n"
                f"HOOK: {hook}\n\n"
                f"BODY: {body}\n\n"
                f"CTA: {cta}\n\n"
                f"{caption}\n\n{hashtags}"
            ).strip()
            params = {"message": message, "access_token": token}

        else:
            raise ValueError(f"Unknown format: {format}")

        response = requests.post(url, params=params)
        response.raise_for_status()
        data = response.json()
        post_id = data.get("id")
        if not post_id:
            raise RuntimeError(f"No post ID in response: {data}")
        return post_id

    except requests.HTTPError as e:
        try:
            fb_err = e.response.json().get("error", {})
            detail = fb_err.get("message", e.response.text)
            code = fb_err.get("code", 0)
        except Exception:
            detail = e.response.text
            code = 0
        # Auto-retry once on auth errors (190 = expired, 102/104 = invalid)
        if code in (190, 102, 104) and not getattr(post_to_facebook, "_retrying", False):
            print(f"Auth error ({code}), attempting token refresh...")
            try:
                post_to_facebook._retrying = True
                refresh_page_token()
                return post_to_facebook(content, format)
            finally:
                post_to_facebook._retrying = False
        raise RuntimeError(f"Facebook API error: {detail}") from e


def schedule_post(content_id: int, scheduled_time: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE content SET status='scheduled', scheduled_time=? WHERE id=?",
        (scheduled_time, content_id),
    )
    conn.commit()
    conn.close()


def mark_posted(content_id: int, fb_post_id: str):
    posted_at = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE content SET status='posted', posted_at=?, fb_post_id=? WHERE id=?",
        (posted_at, fb_post_id, content_id),
    )
    conn.commit()
    conn.close()


def check_token_expiry() -> dict:
    token = _token()
    try:
        r = requests.get(f"{GRAPH_BASE}/debug_token", params={
            "input_token": token,
            "access_token": token,
        })
        data = r.json().get("data", {})
        expires_at = data.get("expires_at", 0)
        is_valid = data.get("is_valid", False)
        if expires_at == 0:
            return {"valid": is_valid, "expires_at": None, "days_remaining": None, "warning": False}
        expires_dt = datetime.fromtimestamp(expires_at, tz=timezone.utc)
        days_remaining = (expires_dt - datetime.now(timezone.utc)).days
        return {
            "valid": is_valid,
            "expires_at": expires_dt.isoformat(),
            "days_remaining": days_remaining,
            "warning": days_remaining < 7,
        }
    except Exception as e:
        return {"valid": False, "expires_at": None, "days_remaining": None, "warning": True, "error": str(e)}


def refresh_page_token() -> str:
    app_id = os.environ.get("FB_APP_ID", "")
    app_secret = os.environ.get("FB_APP_SECRET", "")
    user_token = os.environ.get("FB_USER_TOKEN", "")
    page_id = _page_id()

    if not all([app_id, app_secret, user_token]) or "your_" in f"{app_secret}{user_token}":
        raise RuntimeError("FB_APP_SECRET and FB_USER_TOKEN must be set in .env for auto-refresh")

    # Exchange user token for long-lived user token (60 days)
    r = requests.get(f"{GRAPH_BASE}/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": user_token,
    })
    r.raise_for_status()
    long_lived_user_token = r.json()["access_token"]

    # Get page token from long-lived user token
    accounts = requests.get(f"{GRAPH_BASE}/me/accounts", params={"access_token": long_lived_user_token})
    accounts.raise_for_status()
    page = next((p for p in accounts.json().get("data", []) if p["id"] == page_id), None)
    if not page:
        raise RuntimeError(f"Page {page_id} not found under this user token")
    new_page_token = page["access_token"]

    # Write new tokens back to .env
    env_text = open(ENV_PATH).read()
    env_text = re.sub(r"FB_ACCESS_TOKEN=.*", f"FB_ACCESS_TOKEN={new_page_token}", env_text)
    env_text = re.sub(r"FB_USER_TOKEN=.*", f"FB_USER_TOKEN={long_lived_user_token}", env_text)
    with open(ENV_PATH, "w") as f:
        f.write(env_text)

    # Reload env so the running process picks it up
    load_dotenv(ENV_PATH, override=True)
    print(f"Token refreshed — new token starts with {new_page_token[:20]}...")
    return new_page_token


def get_post_insights(fb_post_id: str) -> dict:
    url = f"{GRAPH_BASE}/{fb_post_id}/insights"
    params = {
        "metric": "post_impressions,post_video_views,post_engaged_users",
        "access_token": _token(),
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json().get("data", [])
        metrics = {item["name"]: item["values"][0]["value"] for item in data}
        return {
            "reach": metrics.get("post_impressions", 0),
            "views": metrics.get("post_video_views", 0),
            "engagement": metrics.get("post_engaged_users", 0),
        }
    except Exception as e:
        print(f"get_post_insights error: {e}")
        return {"reach": 0, "views": 0, "engagement": 0}
