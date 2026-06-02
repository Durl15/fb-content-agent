import sqlite3
from datetime import datetime, timezone

DB_PATH = "content.db"

AFFILIATES = [
    {
        "name": "HubSpot CRM",
        "company": "HubSpot",
        "tracking_url": "https://track.djaiconsulting.com/go/hubspot",
        "display_url": "partnerstack.com/hubspot",
        "commission_type": "cpa",
        "commission_value": 200.00,
        "cta_template": "Manage your business contacts for free — tool I recommend to every SMB client:",
        "niche_tags": "business_software,ai_tools",
        "compatible_formats": "reel_script,carousel,text_post",
    },
    {
        "name": "Monday.com",
        "company": "Monday",
        "tracking_url": "https://track.djaiconsulting.com/go/monday",
        "display_url": "partnerstack.com/monday",
        "commission_type": "cpa",
        "commission_value": 120.00,
        "cta_template": "The project management tool that saved my consulting business 10 hours a week:",
        "niche_tags": "business_software",
        "compatible_formats": "carousel,text_post",
    },
    {
        "name": "Jasper AI",
        "company": "Jasper",
        "tracking_url": "https://track.djaiconsulting.com/go/jasper",
        "display_url": "partnerstack.com/jasper",
        "commission_type": "revenue_share",
        "commission_value": 25.00,
        "cta_template": "AI writing tool I use to generate content 10x faster:",
        "niche_tags": "ai_tools",
        "compatible_formats": "reel_script,text_post",
    },
    {
        "name": "Notion",
        "company": "Notion",
        "tracking_url": "https://track.djaiconsulting.com/go/notion",
        "display_url": "affiliate.notion.so",
        "commission_type": "cpa",
        "commission_value": 50.00,
        "cta_template": "How I organize every client project and consulting workflow:",
        "niche_tags": "business_software,ai_tools",
        "compatible_formats": "carousel,text_post",
    },
    {
        "name": "Calendly",
        "company": "Calendly",
        "tracking_url": "https://track.djaiconsulting.com/go/calendly",
        "display_url": "calendly.com/affiliates",
        "commission_type": "cpa",
        "commission_value": 30.00,
        "cta_template": "Stop the back-and-forth scheduling — book me directly or use my link to set up your own:",
        "niche_tags": "business_software,local_syracuse",
        "compatible_formats": "reel_script,carousel,text_post",
    },
]


def seed():
    conn = sqlite3.connect(DB_PATH)
    created_at = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for a in AFFILIATES:
        existing = conn.execute(
            "SELECT id FROM affiliate_links WHERE name = ?", (a["name"],)
        ).fetchone()
        if existing:
            print(f"  [skip] {a['name']} already exists")
            continue

        conn.execute(
            """INSERT INTO affiliate_links
               (name, company, tracking_url, display_url, commission_type,
                commission_value, cta_template, niche_tags, compatible_formats,
                is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                a["name"], a["company"], a["tracking_url"], a["display_url"],
                a["commission_type"], a["commission_value"], a["cta_template"],
                a["niche_tags"], a["compatible_formats"], created_at,
            ),
        )
        print(f"  [added] {a['name']} — ${a['commission_value']} {a['commission_type']}")
        inserted += 1

    conn.commit()
    conn.close()
    print(f"\nSeeded {inserted} affiliate(s) into {DB_PATH}")


if __name__ == "__main__":
    seed()
