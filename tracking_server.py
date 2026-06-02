import os
import sqlite3
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

load_dotenv(override=True)

DB_PATH = os.getenv("DB_PATH", "content.db")

app = FastAPI(title="DJ AI Consulting Link Tracker", docs_url=None, redoc_url=None)


@app.get("/go/{slug}")
def redirect_and_track(slug: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Match affiliate by slug in tracking_url
    row = conn.execute(
        "SELECT * FROM affiliate_links WHERE tracking_url LIKE ? AND is_active=1",
        (f"%/{slug}",),
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No active affiliate found for slug '{slug}'")

    aff = dict(row)

    # Log the click — content_id 0 means click came from a direct link (not tracked content)
    conn.execute(
        "INSERT INTO affiliate_clicks (affiliate_id, content_id, clicked_at, source) "
        "VALUES (?, 0, ?, 'facebook')",
        (aff["id"], datetime.now(timezone.utc).isoformat()),
    )
    conn.execute(
        "UPDATE affiliate_links SET clicks = clicks + 1 WHERE id=?",
        (aff["id"],),
    )
    conn.commit()
    conn.close()

    # Redirect to the real affiliate URL (display_url as fallback)
    destination = aff.get("display_url") or aff.get("tracking_url", "/")
    if not destination.startswith("http"):
        destination = "https://" + destination

    return RedirectResponse(url=destination, status_code=302)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tracking_server:app", host="0.0.0.0", port=8003, reload=True)
