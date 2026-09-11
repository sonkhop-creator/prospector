"""
Thin wrapper around the Google Places API (New).

Requires an env var GOOGLE_PLACES_API_KEY with Places API (New) enabled
in Google Cloud Console. Run this locally / in Claude Code on your own
machine — this file makes real network calls, which the sandbox this
was drafted in can't reach.
"""

import os
import requests

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

FIELD_MASK_SEARCH = (
    "places.id,places.displayName,places.formattedAddress,places.rating,"
    "places.userRatingCount,places.regularOpeningHours,places.priceLevel,"
    "places.internationalPhoneNumber,places.location"
)
FIELD_MASK_DETAILS = "id,websiteUri,reviews,regularOpeningHours"


def _api_key() -> str:
    key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not key:
        raise RuntimeError(
            "Set GOOGLE_PLACES_API_KEY in your environment before running a scan."
        )
    return key


def search_niche(niche: str, location: str, max_results: int = 20) -> list[dict]:
    """e.g. search_niche('borehole pump repair', 'Roodepoort, Gauteng')"""
    resp = requests.post(
        PLACES_TEXT_SEARCH_URL,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": _api_key(),
            "X-Goog-FieldMask": FIELD_MASK_SEARCH,
        },
        json={"textQuery": f"{niche} in {location}", "maxResultCount": max_results},
        timeout=15,
    )
    resp.raise_for_status()
    places = resp.json().get("places", [])
    return [_normalize(p) for p in places]


def get_details(place_id: str) -> dict:
    """Second call per business — needed for website + review recency."""
    resp = requests.get(
        PLACES_DETAILS_URL.format(place_id=place_id),
        headers={
            "X-Goog-Api-Key": _api_key(),
            "X-Goog-FieldMask": FIELD_MASK_DETAILS,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def _normalize(p: dict) -> dict:
    """Map the new Places API's shape onto the flat dict scorer.py expects."""
    hours = p.get("regularOpeningHours", {}).get("weekdayDescriptions")
    return {
        "name": p.get("displayName", {}).get("text", "Unknown"),
        "place_id": p.get("id"),
        "address": p.get("formattedAddress"),
        "rating": p.get("rating"),
        "rating_count": p.get("userRatingCount", 0),
        "phone_number": p.get("internationalPhoneNumber"),
        "weekday_hours": hours,
        "price_level": p.get("priceLevel"),
    }
