from .scorer import BusinessScore


def render_report(niche: str, location: str, scores: list[BusinessScore]) -> str:
    scores_sorted = sorted(
        scores, key=lambda b: (b.total is None, -(b.total or 0))
    )
    lines = [
        f"# Prospector Scan — {niche}, {location}",
        "",
        f"**Field size:** {len(scores)} businesses",
        f"**Scored on:** {scores[0].scored_dimensions_count if scores else 0} of "
        f"{len(scores[0].dimensions) if scores else 0} dimensions "
        "(Site/booking path and Content freshness need a Places Details "
        "call per business — not included in this pass)",
        "",
        "| Rank | Business | Score | Search presence | Listing | Reviews | Competitiveness |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, b in enumerate(scores_sorted, 1):
        dims = {d.name: d.score for d in b.dimensions}
        total_str = f"{b.total}/{b.scored_dimensions_count * 5}" if b.total is not None else "—"
        lines.append(
            f"| {i} | {b.name} | {total_str} | "
            f"{dims.get('Search presence', '—')} | "
            f"{dims.get('Listing completeness', '—')} | "
            f"{dims.get('Review signal', '—')} | "
            f"{dims.get('Local competitiveness', '—')} |"
        )

    lines.append("")
    lines.append("## Detail")
    for b in scores_sorted:
        lines.append(f"\n### {b.name}")
        for d in b.dimensions:
            score_str = f"{d.score}/5" if d.score is not None else "not scored"
            lines.append(f"- **{d.name}:** {score_str} — {d.basis}")

    return "\n".join(lines)
