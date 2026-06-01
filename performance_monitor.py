import json
import os
import sqlite3
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

import fb_poster

load_dotenv()

DB_PATH = "content.db"


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def check_all_posts():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, topic, fb_post_id FROM content "
        "WHERE status='posted' AND fb_post_id IS NOT NULL"
    ).fetchall()
    conn.close()

    if not rows:
        print("No posted content found.")
        return

    checked_at = datetime.now(timezone.utc).isoformat()

    for content_id, topic_str, fb_post_id in rows:
        insights = fb_poster.get_post_insights(fb_post_id)

        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO performance_log "
            "(content_id, checked_at, reach, views, likes, comments, shares) "
            "VALUES (?, ?, ?, ?, 0, 0, 0)",
            (
                content_id,
                checked_at,
                insights["reach"],
                insights["views"],
            ),
        )
        conn.execute(
            "UPDATE content SET reach=?, views=?, engagement=? WHERE id=?",
            (insights["reach"], insights["views"], insights["engagement"], content_id),
        )
        conn.commit()
        conn.close()

        try:
            topic = json.loads(topic_str) if topic_str else {}
            topic_title = topic.get("title", f"content_id={content_id}")
        except Exception:
            topic_title = f"content_id={content_id}"

        print(
            f"  [{topic_title}] "
            f"reach={insights['reach']} "
            f"views={insights['views']} "
            f"engagement={insights['engagement']}"
        )


def generate_performance_report() -> str:
    conn = sqlite3.connect(DB_PATH)

    top_posts = conn.execute(
        "SELECT topic, format, reach, views, engagement FROM content "
        "WHERE status='posted' ORDER BY reach DESC LIMIT 5"
    ).fetchall()

    format_averages = conn.execute(
        "SELECT format, AVG(reach), AVG(views), AVG(engagement), COUNT(*) "
        "FROM content WHERE status='posted' GROUP BY format"
    ).fetchall()

    conn.close()

    if not top_posts:
        return "No posted content to report on yet."

    top_posts_text = "\n".join(
        f"- {row[0]} | format={row[1]} | reach={row[2]} views={row[3]} engagement={row[4]}"
        for row in top_posts
    )

    format_text = "\n".join(
        f"- {row[0]}: avg_reach={row[1]:.0f} avg_views={row[2]:.0f} "
        f"avg_engagement={row[3]:.0f} count={row[4]}"
        for row in format_averages
    )

    niche = os.environ.get("NICHE", "")
    page_name = os.environ.get("PAGE_NAME", "")

    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=(
            f"You are a social media analyst for {page_name}, a Facebook Page in this niche: {niche}. "
            "Write a concise plain text weekly performance summary and content recommendations "
            "based on the data provided. No markdown, no bullet symbols — plain readable text."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Top 5 posts by reach:\n{top_posts_text}\n\n"
                    f"Format performance averages:\n{format_text}"
                ),
            }
        ],
    )

    return message.content[0].text
