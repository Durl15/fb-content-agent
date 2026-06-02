"""
automate.py — fully automated FB Content Agent pipeline

Scheduled jobs:
  generate_and_schedule  daily at GENERATE_HOUR (default midnight)
  post_due               every hour — fires anything with scheduled_time <= now
  run_monitor            daily at MONITOR_HOUR (default 8am)
  pipeline_health        every 6 hours — refills if queue drops below MIN_QUEUE

Run:  python automate.py
Logs: logs/automate.log
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH       = os.getenv("DB_PATH", "content.db")
NICHE         = os.getenv("NICHE", "AI business consulting, small business automation, Syracuse NY")
TIMEZONE      = os.getenv("TIMEZONE", "America/New_York")
GENERATE_HOUR = int(os.getenv("GENERATE_HOUR", "0"))    # midnight
MONITOR_HOUR  = int(os.getenv("MONITOR_HOUR", "8"))     # 8am
GENERATE_COUNT = int(os.getenv("GENERATE_COUNT", "20"))
MIN_QUEUE     = int(os.getenv("MIN_QUEUE", "9"))         # refill if < 9 queued (3 days)

# ── Logging ───────────────────────────────────────────────────────────────────

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/automate.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("automate")

# ── Lazy imports (avoid loading heavy libs at startup) ────────────────────────

def _content_generator():
    import content_generator
    return content_generator

def _fb_poster():
    import fb_poster
    return fb_poster

def _performance_monitor():
    import performance_monitor
    return performance_monitor

# ── DB helpers ────────────────────────────────────────────────────────────────

def _draft_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM content WHERE status='draft'").fetchone()[0]
    conn.close()
    return n

def _scheduled_count() -> int:
    conn = sqlite3.connect(DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM content WHERE status='scheduled'").fetchone()[0]
    conn.close()
    return n

def _queue_count() -> int:
    return _draft_count() + _scheduled_count()

def _due_posts() -> list[tuple]:
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).isoformat()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, topic, format, content_json FROM content "
        "WHERE status='scheduled' AND scheduled_time <= ?",
        (now,),
    ).fetchall()
    conn.close()
    return rows

def _save_drafts(topics: list, formats: list):
    created_at = datetime.now(timezone.utc).isoformat()
    cg = _content_generator()
    conn = sqlite3.connect(DB_PATH)
    saved = 0
    for i, topic in enumerate(topics):
        fmt = formats[i % len(formats)]
        topic["format"] = fmt
        try:
            if fmt == "reel_script":
                content = cg.generate_reel_script(topic)
            elif fmt == "carousel":
                content = cg.generate_carousel(topic)
            else:
                content = cg.generate_text_post(topic)
            conn.execute(
                "INSERT INTO content (topic, format, content_json, status, created_at) "
                "VALUES (?, ?, ?, 'draft', ?)",
                (json.dumps(topic), fmt, json.dumps(content), created_at),
            )
            saved += 1
        except Exception as e:
            log.warning(f"  Failed to generate content for topic '{topic.get('title')}': {e}")
    conn.commit()
    conn.close()
    return saved

def _schedule_drafts():
    from scheduler import build_weekly_calendar
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, topic, format FROM content WHERE status='draft'"
    ).fetchall()
    conn.close()
    if not rows:
        return 0
    topics = [json.loads(r["topic"]) for r in rows]
    calendar = build_weekly_calendar(topics)
    fp = _fb_poster()
    for entry, row in zip(calendar, rows):
        fp.schedule_post(row["id"], entry["scheduled_time"])
    return len(calendar)

# ── Scheduled jobs ────────────────────────────────────────────────────────────

def job_generate_and_schedule():
    """Generate GENERATE_COUNT new content pieces and schedule them."""
    log.info(f"[generate] Starting — generating {GENERATE_COUNT} pieces for: {NICHE}")
    try:
        cg = _content_generator()
        topics = cg.generate_topics(NICHE, GENERATE_COUNT)
        formats = ["reel_script", "carousel", "text_post"]
        saved = _save_drafts(topics, formats)
        scheduled = _schedule_drafts()
        log.info(f"[generate] Done — {saved} generated, {scheduled} scheduled")
    except Exception as e:
        log.error(f"[generate] Failed: {e}")


def job_post_due():
    """Post anything with scheduled_time <= now."""
    rows = _due_posts()
    if not rows:
        log.info("[post] No posts due right now")
        return

    log.info(f"[post] {len(rows)} post(s) due — firing")
    fp = _fb_poster()
    cg = _content_generator()
    posted = 0

    for content_id, topic_str, fmt, content_json_str in rows:
        try:
            topic = json.loads(topic_str)
            if content_json_str:
                content = json.loads(content_json_str)
            else:
                if fmt == "reel_script":
                    content = cg.generate_reel_script(topic)
                elif fmt == "carousel":
                    content = cg.generate_carousel(topic)
                else:
                    content = cg.generate_text_post(topic)
                conn = sqlite3.connect(DB_PATH)
                conn.execute("UPDATE content SET content_json=? WHERE id=?",
                             (json.dumps(content), content_id))
                conn.commit()
                conn.close()

            fb_post_id = fp.post_to_facebook(content, fmt)
            fp.mark_posted(content_id, fb_post_id)
            log.info(f"  [OK] id={content_id} → {fb_post_id}")
            posted += 1
        except Exception as e:
            log.error(f"  [FAIL] id={content_id}: {e}")

    log.info(f"[post] Done — {posted}/{len(rows)} posted")


def job_monitor():
    """Pull Facebook Insights and log performance report."""
    log.info("[monitor] Checking post performance...")
    try:
        pm = _performance_monitor()
        pm.check_all_posts()
        report = pm.generate_performance_report()
        log.info(f"[monitor] Report:\n{report}")
    except Exception as e:
        log.error(f"[monitor] Failed: {e}")


def job_pipeline_health():
    """Refill the queue if it drops below MIN_QUEUE posts."""
    queued = _queue_count()
    log.info(f"[health] Queue: {queued} posts (min={MIN_QUEUE})")
    if queued < MIN_QUEUE:
        log.info(f"[health] Queue low — refilling with {GENERATE_COUNT} new posts")
        job_generate_and_schedule()
    else:
        log.info(f"[health] Queue healthy — no action needed")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    tz = TIMEZONE
    scheduler = BlockingScheduler(timezone=tz)

    # Generate + schedule: daily at GENERATE_HOUR
    scheduler.add_job(
        job_generate_and_schedule,
        CronTrigger(hour=GENERATE_HOUR, minute=0, timezone=tz),
        id="generate",
        name=f"Generate content daily at {GENERATE_HOUR:02d}:00",
        max_instances=1,
        misfire_grace_time=600,
    )

    # Post due content: every hour at :00
    scheduler.add_job(
        job_post_due,
        CronTrigger(minute=0, timezone=tz),
        id="post",
        name="Post due content every hour",
        max_instances=1,
        misfire_grace_time=300,
    )

    # Monitor: daily at MONITOR_HOUR
    scheduler.add_job(
        job_monitor,
        CronTrigger(hour=MONITOR_HOUR, minute=0, timezone=tz),
        id="monitor",
        name=f"Monitor performance daily at {MONITOR_HOUR:02d}:00",
        max_instances=1,
        misfire_grace_time=600,
    )

    # Pipeline health check: every 6 hours
    scheduler.add_job(
        job_pipeline_health,
        IntervalTrigger(hours=6, timezone=tz),
        id="health",
        name="Pipeline health check every 6h",
        max_instances=1,
    )

    log.info("=" * 55)
    log.info("  FB Content Agent — Automation Started")
    log.info(f"  Niche   : {NICHE}")
    log.info(f"  Generate: daily at {GENERATE_HOUR:02d}:00 {tz}")
    log.info(f"  Post    : every hour at :00")
    log.info(f"  Monitor : daily at {MONITOR_HOUR:02d}:00 {tz}")
    log.info(f"  Health  : every 6h (refill if queue < {MIN_QUEUE})")
    log.info("=" * 55)

    # Run pipeline health check immediately on startup
    log.info("[startup] Running pipeline health check...")
    job_pipeline_health()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Automation stopped.")


if __name__ == "__main__":
    main()
