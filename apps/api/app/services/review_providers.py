"""Review sources for the Reputation Radar (CL-05): Google Business Profile, Facebook, Yelp.

Each adapter fetches recent reviews and (where the platform allows) posts a public reply.
Yelp's API is read-only (3 most recent excerpts, no reply endpoint) — those replies are
copied by hand.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx

from app.config import Settings
from app.models import Client, ReviewProvider

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GBP_V4 = "https://mybusiness.googleapis.com/v4"
GBP_PERF = "https://businessprofileperformance.googleapis.com/v1"
GBP_ACCOUNTS = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
GBP_INFO = "https://mybusinessbusinessinformation.googleapis.com/v1"
GRAPH = "https://graph.facebook.com/v19.0"
YELP = "https://api.yelp.com/v3"
STARS = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


class ProviderError(Exception):
    pass


@dataclass
class FetchedReview:
    external_id: str
    rating: int
    body: str | None
    reviewer_name: str | None
    reviewed_at: datetime | None
    existing_reply: str | None = None
    reply_target: str | None = None


def _parse_ts(value: str | None, naive_tz: str = "UTC") -> datetime | None:
    """ISO timestamps; naive ones (Yelp's "YYYY-MM-DD HH:MM:SS") are read in ``naive_tz``."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=ZoneInfo(naive_tz))


def _check(res: httpx.Response, who: str) -> dict:
    if res.status_code >= 400:
        raise ProviderError(f"{who} {res.status_code}: {res.text[:300]}")
    return res.json() if res.content else {}


# ------------------------------------------------------------------ Google Business Profile
async def google_access_token(settings: Settings, refresh_token: str) -> str:
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    return _check(res, "Google token")["access_token"]


async def google_exchange_code(settings: Settings, code: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            },
        )
    return _check(res, "Google code exchange")


async def google_list_locations(access_token: str) -> list[dict]:
    """[{name: 'accounts/A/locations/L', title}] — the v4 reviews API needs the account path."""
    headers = {"Authorization": f"Bearer {access_token}"}
    out: list[dict] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        accounts = _check(await client.get(GBP_ACCOUNTS, headers=headers), "GBP accounts")
        for acct in accounts.get("accounts", []):
            locs = _check(
                await client.get(
                    f"{GBP_INFO}/{acct['name']}/locations",
                    headers=headers,
                    params={"readMask": "name,title", "pageSize": 100},
                ),
                "GBP locations",
            )
            for loc in locs.get("locations", []):
                loc_id = loc["name"].split("/")[-1]
                out.append({"name": f"{acct['name']}/locations/{loc_id}", "title": loc.get("title")})
    return out


async def google_fetch_reviews(access_token: str, location: str) -> list[FetchedReview]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = _check(
            await client.get(
                f"{GBP_V4}/{location}/reviews",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"pageSize": 50, "orderBy": "updateTime desc"},
            ),
            "GBP reviews",
        )
    return [
        FetchedReview(
            external_id=r["reviewId"],
            rating=STARS.get(r.get("starRating", ""), 0),
            body=r.get("comment"),
            reviewer_name=(r.get("reviewer") or {}).get("displayName"),
            reviewed_at=_parse_ts(r.get("createTime")),
            existing_reply=(r.get("reviewReply") or {}).get("comment"),
        )
        for r in data.get("reviews", [])
        if STARS.get(r.get("starRating", ""))
    ]


async def google_reply(access_token: str, location: str, review_id: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        _check(
            await client.put(
                f"{GBP_V4}/{location}/reviews/{review_id}/reply",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": text},
            ),
            "GBP reply",
        )


PERF_METRICS = {
    "BUSINESS_IMPRESSIONS_DESKTOP_MAPS": "impressions",
    "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH": "impressions",
    "BUSINESS_IMPRESSIONS_MOBILE_MAPS": "impressions",
    "BUSINESS_IMPRESSIONS_MOBILE_SEARCH": "impressions",
    "BUSINESS_DIRECTION_REQUESTS": "gbp_direction_requests",
    "CALL_CLICKS": "clicks",
    "WEBSITE_CLICKS": "clicks",
}


async def google_fetch_performance(
    access_token: str, location: str, start: date, end: date
) -> dict[date, dict[str, int]]:
    """Daily impressions / direction requests / clicks from the Performance API."""
    loc_id = location.split("/")[-1]
    params: list[tuple[str, str | int]] = [("dailyMetrics", m) for m in PERF_METRICS]
    for prefix, d in (("dailyRange.startDate", start), ("dailyRange.endDate", end)):
        params += [(f"{prefix}.year", d.year), (f"{prefix}.month", d.month), (f"{prefix}.day", d.day)]
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = _check(
            await client.get(
                f"{GBP_PERF}/locations/{loc_id}:fetchMultiDailyMetricsTimeSeries",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            ),
            "GBP performance",
        )
    out: dict[date, dict[str, int]] = {}
    for group in data.get("multiDailyMetricTimeSeries", []):
        for series in group.get("dailyMetricTimeSeries", []):
            column = PERF_METRICS.get(series.get("dailyMetric", ""))
            if not column:
                continue
            for point in (series.get("timeSeries") or {}).get("datedValues", []):
                dd = point.get("date") or {}
                key = date(dd["year"], dd["month"], dd["day"])
                day = out.setdefault(key, {"impressions": 0, "gbp_direction_requests": 0, "clicks": 0})
                day[column] += int(point.get("value") or 0)
    return out


# ------------------------------------------------------------------ Facebook (Page ratings)
async def facebook_fetch_reviews(page_id: str, page_token: str) -> list[FetchedReview]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = _check(
            await client.get(
                f"{GRAPH}/{page_id}/ratings",
                params={
                    "access_token": page_token,
                    "fields": "created_time,rating,recommendation_type,review_text,"
                    "reviewer{name},open_graph_story{id}",
                    "limit": 50,
                },
            ),
            "Facebook ratings",
        )
    out = []
    for r in data.get("data", []):
        story = (r.get("open_graph_story") or {}).get("id")
        # Facebook replaced stars with recommend / don't recommend
        rating = r.get("rating") or (5 if r.get("recommendation_type") == "positive" else 2)
        out.append(
            FetchedReview(
                external_id=story or f"{page_id}:{r.get('created_time')}",
                rating=int(rating),
                body=r.get("review_text"),
                reviewer_name=(r.get("reviewer") or {}).get("name"),
                reviewed_at=_parse_ts(r.get("created_time")),
                reply_target=story,
            )
        )
    return out


async def facebook_reply(page_token: str, story_id: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        _check(
            await client.post(
                f"{GRAPH}/{story_id}/comments", data={"message": text, "access_token": page_token}
            ),
            "Facebook reply",
        )


# ------------------------------------------------------------------ Yelp (read-only)
async def yelp_fetch_reviews(api_key: str, business_id: str) -> list[FetchedReview]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        data = _check(
            await client.get(
                f"{YELP}/businesses/{business_id}/reviews",
                headers={"Authorization": f"Bearer {api_key}"},
            ),
            "Yelp reviews",
        )
    return [
        FetchedReview(
            external_id=r["id"],
            rating=int(r.get("rating") or 0),
            body=r.get("text"),
            reviewer_name=(r.get("user") or {}).get("name"),
            reviewed_at=_parse_ts(r.get("time_created"), naive_tz="America/Los_Angeles"),  # Yelp: PST
        )
        for r in data.get("reviews", [])
        if r.get("rating")
    ]


def provider_can_reply(provider: ReviewProvider) -> bool:
    return provider != ReviewProvider.yelp


def configured_providers(client: Client, settings: Settings, creds: dict[str, dict]) -> list[str]:
    out = []
    if client.gbp_location_id and creds.get("google", {}).get("refresh_token"):
        out.append("google")
    if client.facebook_page_id and creds.get("facebook", {}).get("page_access_token"):
        out.append("facebook")
    if client.yelp_business_id and settings.yelp_api_key:
        out.append("yelp")
    return out
