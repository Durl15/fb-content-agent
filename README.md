# FB Content Agent

AI-powered Facebook content engine. Generates scripts, captions, and carousels
using Claude, then schedules and posts them to a Facebook Page via the Graph API.

## Setup

```
pip install -r requirements.txt
python init_db.py
```

Add credentials to `.env`:

```
FB_PAGE_ID=your_page_id
FB_ACCESS_TOKEN=your_long_lived_page_access_token
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## Get Facebook Credentials

- Go to developers.facebook.com
- Create app, add Pages API product
- Generate long-lived Page Access Token via Graph API Explorer
- Copy Page ID from your Facebook Page About section

## Run Modes

```
python main_agent.py --mode generate    # generate 20 content pieces
python main_agent.py --mode schedule    # assign posting times
python main_agent.py --mode post        # post scheduled content
python main_agent.py --mode monitor     # check performance
python main_agent.py                    # run full pipeline
```

## API Dashboard backend

```
uvicorn content_api:app --reload --port 8002
```

Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | /content?status=draft&limit=50 | List content |
| GET | /content/{id} | Single content record |
| POST | /content/generate | Generate drafts (body: `{"count": 10}`) |
| POST | /content/{id}/schedule | Schedule a post |
| POST | /content/{id}/post-now | Post immediately to Facebook |
| GET | /performance | Last 7 days performance log |
| GET | /report | AI-generated weekly performance report |
