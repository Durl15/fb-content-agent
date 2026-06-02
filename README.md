# FB Content Agent

AI-powered Facebook content pipeline. Uses Claude to generate Reel scripts, carousels, and text posts, then schedules and publishes them to a Facebook Page via the Graph API. Includes a React dashboard and automatic token refresh.

## Features

- Claude generates niche-targeted content (Reel scripts, carousels, text posts)
- Schedule posts across a weekly calendar with configurable time slots
- React dashboard with content grid, inline scheduling, and Post Now
- Token health banner with one-click auto-refresh — no manual token management
- Performance monitoring and AI-generated weekly reports

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Anthropic API key](https://console.anthropic.com)
- Facebook Developer account with a Page you admin

## Setup

**1. Clone and install**

```bash
git clone https://github.com/Durl15/fb-content-agent
cd fb-content-agent
pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp .env.example .env
```

Edit `.env` with your credentials (see [Getting Credentials](#getting-credentials) below).

**3. Initialize the database**

```bash
python init_db.py
```

**4. Install dashboard dependencies**

```bash
cd dashboard && npm install && cd ..
```

## Getting Credentials

### Anthropic API Key
Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) and create a key. Set as `ANTHROPIC_API_KEY`.

### Facebook Credentials

Getting page posting permissions requires a few one-time steps:

**1. Create a Facebook App**
- Go to [developers.facebook.com/apps](https://developers.facebook.com/apps) → Create App
- Select the **"Authenticate and request data from users with Facebook Login"** use case
- Connect your business portfolio

**2. Add posting permissions to the app**
- In your app dashboard → App Review → Permissions and Features
- Add `pages_manage_posts` and `pages_read_engagement`

**3. Link your Page to your Business Portfolio**
- Go to [business.facebook.com](https://business.facebook.com) → Settings → Accounts → Pages → Add Page
- This step is required for `pages_manage_posts` to work

**4. Get your tokens**
- Go to [developers.facebook.com/tools/accesstoken](https://developers.facebook.com/tools/accesstoken/)
- Copy the **User Token** for your app → set as `FB_USER_TOKEN`
- Call `GET https://graph.facebook.com/v19.0/me/accounts?access_token={user_token}` to get your Page token and Page ID

**5. Set remaining values in `.env`**
- `FB_PAGE_ID` — your Page's numeric ID
- `FB_ACCESS_TOKEN` — the Page Access Token from step 4
- `FB_APP_ID` — from your app's Basic Settings
- `FB_APP_SECRET` — from your app's Basic Settings (click Show)
- `FB_USER_TOKEN` — from the Access Token Tool

> **Note:** `FB_APP_SECRET` + `FB_USER_TOKEN` enable the Auto-Refresh button in the dashboard, which automatically rotates tokens when they expire.

## Running

**Start the API backend**

```bash
python -m uvicorn content_api:app --port 8002
```

**Start the React dashboard**

```bash
cd dashboard && npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## CLI Usage

```bash
python main_agent.py --mode generate    # generate 20 content pieces
python main_agent.py --mode schedule    # assign posting times from POST_TIMES
python main_agent.py --mode post        # post anything due now
python main_agent.py --mode monitor     # fetch insights + performance report
python main_agent.py                    # run full pipeline (default)
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/content` | List content (`?status=draft&limit=50`) |
| GET | `/content/{id}` | Single content record |
| POST | `/content/generate` | Generate drafts (`{"count": 10}`) |
| POST | `/content/{id}/schedule` | Schedule a post (`{"scheduled_time": "ISO8601"}`) |
| POST | `/content/{id}/post-now` | Post immediately to Facebook |
| GET | `/performance` | Last 7 days performance log |
| GET | `/report` | AI-generated weekly performance summary |
| GET | `/token-status` | FB token validity and expiry info |
| POST | `/token-refresh` | Exchange user token for fresh page token |

## Configuration

| Variable | Description |
|----------|-------------|
| `FB_PAGE_ID` | Facebook Page numeric ID |
| `FB_ACCESS_TOKEN` | Page Access Token |
| `FB_APP_ID` | Facebook App ID |
| `FB_APP_SECRET` | Facebook App Secret (for auto-refresh) |
| `FB_USER_TOKEN` | User Access Token (for auto-refresh) |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `PAGE_NAME` | Your page name (used in Claude prompts) |
| `NICHE` | Content niche description |
| `POST_TIMES` | Comma-separated posting times, e.g. `09:00,12:00,19:00` |
| `TIMEZONE` | Timezone for scheduling, e.g. `America/New_York` |
| `ALERT_MIN_SCORE` | Minimum engagement score for alerts |

## Token Auto-Refresh

The dashboard shows a warning banner when the Facebook token is near expiry. Clicking **Auto-Refresh** exchanges `FB_USER_TOKEN` for a fresh long-lived user token, fetches a new Page Access Token, and writes both back to `.env` automatically — no server restart needed.

If `FB_APP_SECRET` or `FB_USER_TOKEN` are not set, the button will show an error with instructions to fill them in.

## Author

**Don Johnson** — [@Durl15](https://github.com/Durl15)
