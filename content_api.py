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
import affiliate_manager

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


class AffiliateCreate(BaseModel):
    name: str
    company: str = ""
    tracking_url: str = ""
    display_url: str = ""
    commission_type: str = "cpa"
    commission_value: float = 0.0
    cta_template: str = ""
    niche_tags: str = ""
    compatible_formats: str = "reel_script,carousel,text_post"


class AffiliateUpdate(BaseModel):
    name: str = None
    company: str = None
    tracking_url: str = None
    display_url: str = None
    commission_type: str = None
    commission_value: float = None
    cta_template: str = None
    niche_tags: str = None
    compatible_formats: str = None


class ClickEvent(BaseModel):
    affiliate_id: int
    content_id: int


class ConversionEvent(BaseModel):
    affiliate_id: int
    content_id: int
    commission: float


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


# ── Affiliate endpoints ───────────────────────────────────────────────────────

@app.get("/affiliates")
def list_affiliates():
    conn = _db()
    rows = conn.execute(
        "SELECT * FROM affiliate_links ORDER BY total_revenue DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/affiliates", status_code=201)
def create_affiliate(req: AffiliateCreate):
    created_at = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        """INSERT INTO affiliate_links
           (name, company, tracking_url, display_url, commission_type,
            commission_value, cta_template, niche_tags, compatible_formats,
            is_active, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
        (req.name, req.company, req.tracking_url, req.display_url,
         req.commission_type, req.commission_value, req.cta_template,
         req.niche_tags, req.compatible_formats, created_at),
    )
    conn.commit()
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM affiliate_links WHERE id=?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return dict(row)


@app.patch("/affiliates/{affiliate_id}")
def update_affiliate(affiliate_id: int, req: AffiliateUpdate):
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join(f"{k}=?" for k in fields)
    conn = _db()
    result = conn.execute(
        f"UPDATE affiliate_links SET {set_clause} WHERE id=?",
        (*fields.values(), affiliate_id),
    )
    conn.commit()
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Affiliate not found")
    row = conn.execute(
        "SELECT * FROM affiliate_links WHERE id=?", (affiliate_id,)
    ).fetchone()
    conn.close()
    return dict(row)


@app.post("/affiliates/{affiliate_id}/pause")
def pause_affiliate(affiliate_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE affiliate_links SET is_active=0 WHERE id=?", (affiliate_id,))
    conn.commit()
    conn.close()
    return {"id": affiliate_id, "is_active": 0}


@app.post("/affiliates/{affiliate_id}/activate")
def activate_affiliate(affiliate_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE affiliate_links SET is_active=1 WHERE id=?", (affiliate_id,))
    conn.commit()
    conn.close()
    return {"id": affiliate_id, "is_active": 1}


@app.post("/affiliates/click")
def record_click(req: ClickEvent):
    affiliate_manager.log_click(req.affiliate_id, req.content_id, "facebook")
    return {"ok": True}


@app.post("/affiliates/conversion")
def record_conversion(req: ConversionEvent):
    affiliate_manager.log_conversion(req.affiliate_id, req.content_id, req.commission)
    return {"ok": True}


@app.get("/affiliates/report")
def affiliate_report():
    return {"report": affiliate_manager.get_affiliate_report()}


@app.get("/affiliates/top")
def top_affiliates():
    conn = _db()
    top = conn.execute(
        "SELECT * FROM affiliate_links ORDER BY total_revenue DESC LIMIT 3"
    ).fetchall()
    underperforming = conn.execute(
        "SELECT * FROM affiliate_links WHERE clicks > 10 AND conversions = 0 "
        "ORDER BY clicks DESC LIMIT 3"
    ).fetchall()
    conn.close()
    return {
        "top_performers": [dict(r) for r in top],
        "underperforming": [dict(r) for r in underperforming],
    }
