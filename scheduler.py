import json
import os
import sqlite3
import time
from datetime import datetime, timedelta

import pytz
from dotenv import load_dotenv

import content_generator
import fb_poster

load_dotenv()

DB_PATH = "content.db"


def _post_times() -> list[str]:
    return os.environ.get("POST_TIMES", "09:00,12:00,19:00").split(",")


def _timezone() -> pytz.BaseTzInfo:
    return pytz.timezone(os.environ.get("TIMEZONE", "America/New_York"))


def build_weekly_calendar(topics: list) -> list:
    tz = _timezone()
    post_times = _post_times()
    formats = ["reel_script", "carousel", "text_post"]
    slots = []

    now = datetime.now(tz)
    day_offset = 0
    slot_index = 0

    for i, topic in enumerate(topics):
        while True:
            target_day = now.date() + timedelta(days=day_offset)
            time_str = post_times[slot_index % len(post_times)]
            hour, minute = map(int, time_str.split(":"))
            scheduled_dt = tz.localize(
                datetime(target_day.year, target_day.month, target_day.day, hour, minute)
            )
            slot_index += 1
            if slot_index % len(post_times) == 0:
                day_offset += 1
            if scheduled_dt > now:
                break

        assigned_format = formats[i % len(formats)]
        topic_copy = dict(topic)
        topic_copy["format"] = assigned_format
        slots.append({
            "topic": topic_copy,
            "format": assigned_format,
            "scheduled_time": scheduled_dt.isoformat(),
        })

    return slots


def run_scheduler():
    print("Scheduler started. Checking every 60 seconds...")
    while True:
        tz = _timezone()
        now = datetime.now(tz).isoformat()

        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT id, topic, format, content_json FROM content "
            "WHERE status='scheduled' AND scheduled_time <= ?",
            (now,),
        ).fetchall()
        conn.close()

        for row in rows:
            content_id, topic_str, fmt, content_json_str = row
            print(f"Processing content_id={content_id} format={fmt}")

            try:
                topic = json.loads(topic_str)

                if content_json_str:
                    content = json.loads(content_json_str)
                else:
                    if fmt == "reel_script":
                        content = content_generator.generate_reel_script(topic)
                    elif fmt == "carousel":
                        content = content_generator.generate_carousel(topic)
                    else:
                        content = content_generator.generate_text_post(topic)

                    conn = sqlite3.connect(DB_PATH)
                    conn.execute(
                        "UPDATE content SET content_json=? WHERE id=?",
                        (json.dumps(content), content_id),
                    )
                    conn.commit()
                    conn.close()

                fb_post_id = fb_poster.post_to_facebook(content, fmt)
                if fb_post_id:
                    fb_poster.mark_posted(content_id, fb_post_id)
                    print(f"  Posted: fb_post_id={fb_post_id}")
                else:
                    print(f"  Failed to post content_id={content_id}")

            except Exception as e:
                print(f"  Error processing content_id={content_id}: {e}")

        time.sleep(60)
