"""
Prospector scoring engine.

Scores a business on the same six dimensions as the manual Phiri Digital
Strategy Local Visibility Audit. Three dimensions are computable from the
Google Places Nearby/Text Search response alone. The other three require a
Places Details call (for `website`, review timestamps, and category/hours
completeness beyond what Nearby Search returns) — those are stubbed here
and marked NOT_SCORED until wired to Details.

This is intentionally honest about what's real: a score of None means
"not enough data yet," not zero.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DimensionScore:
    name: str
    score: Optional[float]  # 0-5, or None if not computed
    basis: str              # what it was computed from, for transparency


@dataclass
class BusinessScore:
    name: str
    place_id: str
    dimensions: list = field(default_factory=list)

    @property
    def total(self) -> Optional[float]:
        scored = [d.score for d in self.dimensions if d.score is not None]
        if not scored:
            return None
        return round(sum(scored), 1)

    @property
    def max_possible(self) -> int:
        return len(self.dimensions) * 5

    @property
    def scored_dimensions_count(self) -> int:
        return len([d for d in self.dimensions if d.score is not None])


def _tier(value: float, breakpoints: list, scores: list) -> int:
    """Map a value to a score band. breakpoints ascending, scores same length+0 floor."""
    for bp, sc in zip(breakpoints, scores):
        if value <= bp:
            return sc
    return scores[-1]


def score_search_presence(rating_count: int) -> DimensionScore:
    """Proxy for findability: how many people have engaged enough to review."""
    s = _tier(rating_count, [0, 3, 10, 30, 100], [0, 1, 2, 3, 4])
    if rating_count > 100:
        s = 5
    return DimensionScore(
        name="Search presence",
        score=s,
        basis=f"{rating_count} reviews on record"
    )


def score_review_signal(rating: Optional[float], rating_count: int) -> DimensionScore:
    """Trust signal — rating value, discounted when the sample is thin."""
    if rating is None or rating_count == 0:
        return DimensionScore("Review signal", 0, "no rating on record")
    raw = rating  # already 0-5
    if rating_count < 3:
        raw = min(raw, 2.5)  # cap confidence on a 1-2 review average
    return DimensionScore(
        name="Review signal",
        score=round(raw, 1),
        basis=f"{rating}\u2605 across {rating_count} reviews"
    )


def score_listing_completeness(phone: Optional[str], weekday_hours: Optional[list],
                                price_level) -> DimensionScore:
    """Proxy for how filled-out the Business Profile is."""
    s = 0
    basis_bits = []
    if phone:
        s += 2
        basis_bits.append("phone listed")
    else:
        basis_bits.append("no phone")
    if weekday_hours and len(weekday_hours) >= 7:
        s += 2
        basis_bits.append("full weekly hours")
    elif weekday_hours:
        s += 1
        basis_bits.append("partial hours")
    else:
        basis_bits.append("no hours listed")
    if price_level is not None:
        s += 1
        basis_bits.append("price level set")
    return DimensionScore("Listing completeness", min(s, 5), ", ".join(basis_bits))


def score_local_competitiveness(rank: int, field_size: int) -> DimensionScore:
    """Where this business sits relative to the rest of the surveyed field."""
    pct = rank / field_size
    if pct <= 0.2:
        s = 5
    elif pct <= 0.4:
        s = 4
    elif pct <= 0.6:
        s = 3
    elif pct <= 0.8:
        s = 2
    else:
        s = 1
    return DimensionScore(
        name="Local competitiveness",
        score=s,
        basis=f"ranked {rank} of {field_size} in this scan"
    )


NOT_SCORED_WEBSITE = DimensionScore(
    "Site / booking path", None,
    "requires Places Details API call (website field) \u2014 not queried in this pass"
)
NOT_SCORED_FRESHNESS = DimensionScore(
    "Content freshness", None,
    "requires review timestamps from Places Details \u2014 not queried in this pass"
)


def score_content_freshness(reviews: Optional[list]) -> DimensionScore:
    """reviews: the 'reviews' list from a Places Details response. Each
    review (new Places API) has a 'publishTime' ISO8601 string. Freshness
    is judged by the single most recent review \u2014 a business with one
    review from last week is more 'alive' than one with fifty from 2019."""
    import datetime

    if not reviews:
        return DimensionScore("Content freshness", 0, "no reviews with timestamps found")

    newest = None
    for r in reviews:
        ts = r.get("publishTime")
        if not ts:
            continue
        try:
            dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if newest is None or dt > newest:
            newest = dt

    if newest is None:
        return DimensionScore("Content freshness", 0, "reviews present but no parseable timestamps")

    age_days = (datetime.datetime.now(datetime.timezone.utc) - newest).days
    if age_days <= 30:
        s = 5
    elif age_days <= 90:
        s = 4
    elif age_days <= 180:
        s = 3
    elif age_days <= 365:
        s = 2
    elif age_days <= 730:
        s = 1
    else:
        s = 0
    return DimensionScore(
        "Content freshness", s, f"most recent review {age_days} days ago"
    )


def score_site_booking_path(website_uri: Optional[str]) -> DimensionScore:
    """Real signal once Details has been called: does a working site/booking
    link exist at all, and is it a real site vs. a social-only presence."""
    if not website_uri:
        return DimensionScore("Site / booking path", 0, "no website on file")
    social_only = any(
        d in website_uri.lower()
        for d in ["facebook.com", "instagram.com", "wa.me", "linktr.ee"]
    )
    if social_only:
        return DimensionScore(
            "Site / booking path", 2, f"social-only presence ({website_uri})"
        )
    return DimensionScore(
        "Site / booking path", 5, f"has a standalone website ({website_uri})"
    )


def score_business(place: dict, rank: int, field_size: int,
                    details: Optional[dict] = None) -> BusinessScore:
    """place: a dict matching the fields returned by the places_search tool /
    Google Places API (name, place_id, rating, rating_count, phone_number,
    weekday_hours, price_level).
    details: optional dict from places_client.get_details() — if provided,
    Site/booking path is scored for real instead of left NOT_SCORED.
    """
    bs = BusinessScore(name=place["name"], place_id=place.get("place_id", ""))
    website_dim = (
        score_site_booking_path(details.get("websiteUri"))
        if details is not None
        else NOT_SCORED_WEBSITE
    )
    freshness_dim = (
        score_content_freshness(details.get("reviews"))
        if details is not None
        else NOT_SCORED_FRESHNESS
    )
    bs.dimensions = [
        score_search_presence(place.get("rating_count", 0) or 0),
        score_listing_completeness(
            place.get("phone_number"),
            place.get("weekday_hours"),
            place.get("price_level"),
        ),
        score_review_signal(place.get("rating"), place.get("rating_count", 0) or 0),
        website_dim,
        freshness_dim,
        score_local_competitiveness(rank, field_size),
    ]
    return bs
