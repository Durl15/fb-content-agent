import os
import sqlite3
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

DB_PATH = os.getenv("DB_PATH", "content.db")

_DEFAULT_AFFILIATE = {
    "id": 0,
    "name": "General CTA",
    "tracking_url": "https://track.djaiconsulting.com/go/general",
    "cta_template": "Ready to automate your business? Let's connect:",
}


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_affiliates() -> list:
    conn = _db()
    rows = conn.execute(
        "SELECT * FROM affiliate_links WHERE is_active = 1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_best_affiliate(format: str, niche_tag: str) -> dict:
    affiliates = load_affiliates()
    if not affiliates:
        return _DEFAULT_AFFILIATE

    def _score(a):
        clicks = a.get("clicks") or 0
        conversions = a.get("conversions") or 0
        commission = a.get("commission_value") or 0
        return (conversions / max(clicks, 1)) * commission

    # Filter by format and niche_tag compatibility
    compatible = [
        a for a in affiliates
        if format in (a.get("compatible_formats") or "")
        and niche_tag in (a.get("niche_tags") or "")
    ]

    pool = compatible if compatible else affiliates
    return max(pool, key=_score)


def get_rotating_cta(format: str, niche_tag: str) -> str:
    aff = get_best_affiliate(format, niche_tag)
    template = aff.get("cta_template", "Check this out:")
    url = aff.get("tracking_url", "")
    return f"{template} {url}".strip()


def log_click(affiliate_id: int, content_id: int, source: str = "facebook"):
    clicked_at = datetime.now(timezone.utc).isoformat()
    conn = _db()
    conn.execute(
        "INSERT INTO affiliate_clicks (affiliate_id, content_id, clicked_at, source) "
        "VALUES (?, ?, ?, ?)",
        (affiliate_id, content_id, clicked_at, source),
    )
    conn.execute(
        "UPDATE affiliate_links SET clicks = clicks + 1 WHERE id = ?",
        (affiliate_id,),
    )
    conn.commit()
    conn.close()


def log_conversion(affiliate_id: int, content_id: int, commission: float):
    converted_at = datetime.now(timezone.utc).isoformat()
    conn = _db()
    conn.execute(
        "INSERT INTO affiliate_conversions (affiliate_id, content_id, commission, converted_at) "
        "VALUES (?, ?, ?, ?)",
        (affiliate_id, content_id, commission, converted_at),
    )
    conn.execute(
        "UPDATE affiliate_links SET conversions = conversions + 1, "
        "total_revenue = total_revenue + ? WHERE id = ?",
        (commission, affiliate_id),
    )
    conn.commit()
    conn.close()


def get_affiliate_report() -> str:
    conn = _db()
    affiliates = [
        dict(r)
        for r in conn.execute(
            "SELECT name, company, commission_type, commission_value, "
            "clicks, conversions, total_revenue, niche_tags "
            "FROM affiliate_links ORDER BY total_revenue DESC"
        ).fetchall()
    ]
    conn.close()

    if not affiliates:
        return "No affiliate data yet. Run seed_affiliates.py to add starter offers."

    lines = []
    for a in affiliates:
        ctr = f"{(a['conversions'] / max(a['clicks'], 1) * 100):.1f}%"
        lines.append(
            f"- {a['name']} ({a['company']}): {a['clicks']} clicks, "
            f"{a['conversions']} conversions ({ctr}), "
            f"${a['total_revenue']:.2f} revenue | {a['commission_type']} ${a['commission_value']}"
        )

    data_text = "\n".join(lines)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=(
            "You are an affiliate marketing analyst for a Facebook content creator "
            "in the AI business consulting niche. Write a plain text performance summary "
            "(no markdown headers or bullet symbols) covering: top performer by revenue, "
            "top performer by click-through rate, underperforming offers to pause, "
            "and 2-3 specific budget/content reallocation recommendations."
        ),
        messages=[{"role": "user", "content": f"Affiliate performance data:\n{data_text}"}],
    )
    return msg.content[0].text
