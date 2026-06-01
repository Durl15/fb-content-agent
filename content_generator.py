import json
import os
import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

_client = None


def _parse(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def generate_topics(niche: str, count: int) -> list:
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=(
            f"You are a social media strategist for a Facebook Page in this niche. "
            f"Generate {count} content topics optimized for Facebook Reels and carousel posts. "
            f"Return ONLY a JSON array of objects: "
            f'[{{"title": ..., "format": ..., "hook": ..., "key_points": ..., "cta": ...}}] '
            f"where format is one of: reel_script, carousel, text_post"
        ),
        messages=[{"role": "user", "content": f"Niche: {niche}"}],
    )
    return _parse(message.content[0].text)


def generate_reel_script(topic: dict) -> dict:
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=(
            "You are a short-form video scriptwriter. Write a 60-second Facebook Reel script "
            "with a 3-second hook, value delivery, and CTA. "
            "Return ONLY JSON: "
            '{"hook": ..., "body": ..., "cta": ..., "caption": ..., "hashtags": ..., "duration_seconds": ...}'
        ),
        messages=[{"role": "user", "content": json.dumps(topic)}],
    )
    return _parse(message.content[0].text)


def generate_carousel(topic: dict) -> dict:
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=(
            "You are a carousel post designer. Write a 5-slide Facebook carousel. "
            "Return ONLY JSON: "
            '{"slides": [{"headline": ..., "body": ...}], "caption": ..., "hashtags": ...}'
        ),
        messages=[{"role": "user", "content": json.dumps(topic)}],
    )
    return _parse(message.content[0].text)


def generate_text_post(topic: dict) -> dict:
    client = _get_client()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=(
            "You are a Facebook copywriter. Write an engaging text post with a strong hook "
            "first line, value, and CTA under 300 words. "
            "Return ONLY JSON: "
            '{"post_text": ..., "hashtags": ...}'
        ),
        messages=[{"role": "user", "content": json.dumps(topic)}],
    )
    return _parse(message.content[0].text)
