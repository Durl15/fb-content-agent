import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import content_generator
import fb_poster
import performance_monitor

load_dotenv(override=True)

app = FastAPI(title="FB Content Agent API")


@app.on_event("startup")
def startup_check():
    status = fb_poster.check_token_expiry()
    days = status.get("days_remaining")
    if days is None:
        print("WARNING: Could not check FB token expiry")
    elif not status.get("valid"):
        print("ERROR: FB access token is invalid or expired")
    elif days < 7:
        print(f"WARNING: FB access token expires in {days} day(s) — refresh soon")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "content.db"
FORMATS = ["reel_script", "carousel", "text_post"]


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class GenerateRequest(BaseModel):
    count: int = 10


class ScheduleRequest(BaseModel):
    scheduled_time: str


@app.get("/content")
def list_content(status: str = None, limit: int = 50):
    conn = _db()
    if status:
        rows = conn.execute(
            "SELECT * FROM content WHERE status=? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM content ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/content/{content_id}")
def get_content(content_id: int):
    conn = _db()
    row = conn.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")
    return dict(row)


@app.post("/content/generate")
def generate_content(req: GenerateRequest):
    niche = os.environ.get("NICHE", "")
    topics = content_generator.generate_topics(niche, req.count)
    created_at = datetime.now(timezone.utc).isoformat()
    saved = 0

    conn = sqlite3.connect(DB_PATH)
    for i, topic in enumerate(topics):
        fmt = FORMATS[i % len(FORMATS)]
        topic["format"] = fmt

        if fmt == "reel_script":
            content = content_generator.generate_reel_script(topic)
        elif fmt == "carousel":
            content = content_generator.generate_carousel(topic)
        else:
            content = content_generator.generate_text_post(topic)

        conn.execute(
            "INSERT INTO content (topic, format, content_json, status, created_at) "
            "VALUES (?, ?, ?, 'draft', ?)",
            (json.dumps(topic), fmt, json.dumps(content), created_at),
        )
        saved += 1

    conn.commit()
    conn.close()
    return {"generated": saved}


@app.post("/content/{content_id}/schedule")
def schedule_content(content_id: int, req: ScheduleRequest):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT id FROM content WHERE id=?", (content_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")
    fb_poster.schedule_post(content_id, req.scheduled_time)
    return {"status": "scheduled", "scheduled_time": req.scheduled_time}


@app.post("/content/{content_id}/post-now")
def post_now(content_id: int):
    conn = _db()
    row = conn.execute("SELECT * FROM content WHERE id=?", (content_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")

    record = dict(row)
    content = json.loads(record["content_json"]) if record["content_json"] else {}
    fmt = record["format"]

    try:
        fb_post_id = fb_poster.post_to_facebook(content, fmt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    fb_poster.mark_posted(content_id, fb_post_id)
    return {"status": "posted", "fb_post_id": fb_post_id}


@app.get("/token-status")
def token_status():
    return fb_poster.check_token_expiry()


@app.post("/token-refresh")
def token_refresh():
    try:
        new_token = fb_poster.refresh_page_token()
        return {"status": "refreshed", "token_prefix": new_token[:20] + "..."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/performance")
def get_performance():
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    conn = _db()
    rows = conn.execute(
        "SELECT pl.*, c.topic, c.format FROM performance_log pl "
        "LEFT JOIN content c ON pl.content_id = c.id "
        "WHERE pl.checked_at >= ? ORDER BY pl.checked_at DESC",
        (since,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/report")
def get_report():
    summary = performance_monitor.generate_performance_report()
    return {"report": summary}
