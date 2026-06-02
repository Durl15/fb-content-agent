import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

import content_generator
import fb_poster
import performance_monitor
import affiliate_manager
from scheduler import build_weekly_calendar, run_scheduler

DB_PATH = "content.db"


def _banner(mode: str):
    page = os.environ.get("PAGE_NAME", "Unknown Page")
    print("=" * 50)
    print(f"  FB Content Agent")
    print(f"  Page : {page}")
    print(f"  Mode : {mode}")
    print(f"  Time : {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)


def mode_generate():
    niche = os.environ.get("NICHE", "")
    print(f"Generating topics for niche: {niche}")
    topics = content_generator.generate_topics(niche, 20)
    formats = ["reel_script", "carousel", "text_post"]
    created_at = datetime.now(timezone.utc).isoformat()
    saved = 0

    conn = sqlite3.connect(DB_PATH)
    for i, topic in enumerate(topics):
        fmt = formats[i % len(formats)]
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
        print(f"  [{fmt}] {topic.get('title', '')}")

    conn.commit()
    conn.close()
    print(f"Saved {saved} drafts to content.db")


def mode_schedule():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, topic, format FROM content WHERE status='draft'"
    ).fetchall()
    conn.close()

    if not rows:
        print("No drafts found to schedule.")
        return

    topics = [json.loads(r["topic"]) for r in rows]
    calendar = build_weekly_calendar(topics)

    conn = sqlite3.connect(DB_PATH)
    for entry, row in zip(calendar, rows):
        fb_poster.schedule_post(row["id"], entry["scheduled_time"])
        print(f"  Scheduled id={row['id']} at {entry['scheduled_time']}")
    conn.close()
    print(f"Scheduled {len(calendar)} posts.")


def mode_post():
    niche = os.environ.get("NICHE", "")
    now = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, topic, format, content_json FROM content "
        "WHERE status='scheduled' AND scheduled_time <= ?",
        (now,),
    ).fetchall()
    conn.close()

    if not rows:
        print("No scheduled posts due right now.")
        return

    for row in rows:
        content_id = row["id"]
        fmt = row["format"]
        content_json_str = row["content_json"]
        print(f"Posting id={content_id} format={fmt}")

        try:
            topic = json.loads(row["topic"])
            if content_json_str:
                content = json.loads(content_json_str)
            else:
                if fmt == "reel_script":
                    content = content_generator.generate_reel_script(topic)
                elif fmt == "carousel":
                    content = content_generator.generate_carousel(topic)
                else:
                    content = content_generator.generate_text_post(topic)

            fb_post_id = fb_poster.post_to_facebook(content, fmt)
            if fb_post_id:
                fb_poster.mark_posted(content_id, fb_post_id)
                print(f"  Posted: fb_post_id={fb_post_id}")
            else:
                print(f"  Failed to post id={content_id}")
        except Exception as e:
            print(f"  Error on id={content_id}: {e}")


def mode_monitor():
    print("Checking all posted content...")
    performance_monitor.check_all_posts()
    print("\nGenerating performance report...")
    report = performance_monitor.generate_performance_report()
    print("\n" + report)


def mode_affiliate():
    print("Generating affiliate performance report...")
    report = affiliate_manager.get_affiliate_report()
    print("\n" + report)


def main():
    parser = argparse.ArgumentParser(description="FB Content Agent")
    parser.add_argument(
        "--mode",
        choices=["generate", "schedule", "post", "monitor", "affiliate", "all"],
        default="all",
    )
    args = parser.parse_args()
    mode = args.mode

    _banner(mode)

    if mode == "generate":
        mode_generate()
    elif mode == "schedule":
        mode_schedule()
    elif mode == "post":
        mode_post()
    elif mode == "monitor":
        mode_monitor()
    elif mode == "affiliate":
        mode_affiliate()
    elif mode == "all":
        print("\n--- GENERATE ---")
        mode_generate()
        print("\n--- SCHEDULE ---")
        mode_schedule()
        print("\n--- POST ---")
        mode_post()
        print("\n--- MONITOR ---")
        mode_monitor()
        print("\n--- AFFILIATE ---")
        mode_affiliate()


if __name__ == "__main__":
    main()
