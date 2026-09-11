import argparse
from .places_client import search_niche, get_details
from .scorer import score_business
from .report import render_report


def main():
    parser = argparse.ArgumentParser(description="Run a Prospector visibility scan.")
    parser.add_argument("--niche", required=True, help='e.g. "borehole pump repair"')
    parser.add_argument("--location", required=True, help='e.g. "Roodepoort, Gauteng"')
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--out", default=None, help="Path to write the markdown report")
    parser.add_argument(
        "--full", action="store_true",
        help="Also call Places Details per business for Site/booking path and "
             "Content freshness (all 6 dimensions). Costs one extra API call "
             "per business \u2014 omit for a fast 4-dimension pass."
    )
    args = parser.parse_args()

    places = search_niche(args.niche, args.location, args.max_results)

    scores = []
    for i, p in enumerate(places):
        details = get_details(p["place_id"]) if (args.full and p.get("place_id")) else None
        scores.append(score_business(p, rank=i + 1, field_size=len(places), details=details))

    report = render_report(args.niche, args.location, scores)

    if args.out:
        with open(args.out, "w") as f:
            f.write(report)
        print(f"Report written to {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()
