"""Pure v4.1 scientific transformations.

This is a tested port of the classification block in
``reference/engine/aso_target_finder_enhanced.py``. Thresholds and evidence
precedence intentionally remain unchanged.
"""

from __future__ import annotations

from typing import Any

TRACKS = ("knockdown", "splice/upregulation", "ambiguous", "modifier", "insufficient data")
DISCLAIMER = "For hypothesis generation and education only. Not for clinical decision-making."


def _confidence(row: dict[str, Any]) -> tuple[str, str]:
    if row.get("strategy") is not None:
        return (
            "Manual override—verify",
            "A user-supplied manual override determined the mechanism; verify its primary sources.",
        )
    if row.get("evidence_truncated") is True:
        return (
            "Capped evidence—manual review",
            "The EVA response exceeded 500 rows, so the observed consequence fractions may be incomplete.",
        )
    if "disagree" in str(row.get("flag", "")).lower():
        return "Conflicting evidence", "Gene2Phenotype and ClinVar imply different mechanism tracks."
    if row.get("g2p_call") is not None and row.get("clinvar_call") == row.get("g2p_call"):
        return "Convergent G2P + ClinVar", "Independent Gene2Phenotype and ClinVar classifications agree."
    if row.get("g2p_call") is not None:
        return (
            "Gene2Phenotype evidence",
            "The mechanism comes from Gene2Phenotype; review its panel and allelic requirement.",
        )
    if row["final_call"] == "modifier":
        return (
            "Association only",
            "Association evidence exists, but direction and causal mechanism are unknown.",
        )
    n, frac = row.get("n_classified"), row.get("frac_lof")
    if n is None or n < 5:
        return "Insufficient evidence", "Fewer than five classified pathogenic records were available."
    if row["final_call"] == "ambiguous":
        return "Conflicting evidence", "The LoF fraction lies between the automated mechanism thresholds."
    distance = min(abs(frac - 0.25), abs(frac - 0.60)) if frac is not None else 0
    if n >= 20 and distance >= 0.15:
        return (
            "Strong heuristic evidence",
            "At least 20 classified records and the LoF fraction is well beyond a decision threshold.",
        )
    if n >= 10 and distance >= 0.05:
        return (
            "Moderate heuristic evidence",
            "At least 10 classified records and the LoF fraction clears a decision threshold.",
        )
    return (
        "Limited heuristic evidence",
        "The automated call clears a threshold but has limited count or threshold separation.",
    )


def classify_candidate(source: dict[str, Any], loeuf_intolerant: float = 0.60) -> dict[str, Any]:
    row = dict(source)
    n_lof: int | None = row.get("n_lof")
    n_missense: int | None = row.get("n_missense")
    n_splice: int | None = row.get("n_splice")
    n_splice_extra: int | None = row.get("n_splice_extra")
    n_classified = n_lof + n_missense if n_lof is not None and n_missense is not None else None
    frac_lof = n_lof / n_classified if n_classified and n_lof is not None else None
    splice_denom = n_lof + n_splice_extra if n_lof is not None and n_splice_extra is not None else None
    frac_splice = (
        (n_splice + n_splice_extra) / splice_denom
        if splice_denom and n_splice is not None and n_splice_extra is not None
        else None
    )
    no_variants = n_classified == 0 and n_splice_extra == 0

    clinvar = "ambiguous"
    if n_classified is None or n_classified < 5:
        clinvar = "insufficient data"
    elif frac_lof is not None and frac_lof >= 0.60:
        clinvar = "splice/upregulation"
    elif frac_lof is not None and frac_lof <= 0.25:
        clinvar = "knockdown"

    mechanism = row.get("g2p_mech")
    g2p = (
        {"LoF": "splice/upregulation", "GoF/DN": "knockdown", "mixed": "ambiguous"}.get(mechanism)
        if isinstance(mechanism, str)
        else None
    )
    final, source_name = clinvar, "ClinVar"
    if no_variants:
        final, source_name = "modifier", "assoc only"
    if g2p is not None:
        final, source_name = g2p, "G2P"
    if row.get("strategy") in {"knockdown", "splice"}:
        final = "knockdown" if row["strategy"] == "knockdown" else "splice/upregulation"
        source_name = "curated"

    loeuf = row.get("loeuf")
    intolerant = loeuf is not None and loeuf < loeuf_intolerant
    tolerance = "unknown" if loeuf is None else "LoF-intolerant" if intolerant else "LoF-tolerant"
    inheritance = row.get("inheritance") or ""
    flag = ""
    if row.get("strategy") is None and g2p is not None and clinvar != "insufficient data" and clinvar != g2p:
        flag = "ClinVar and G2P disagree"
    elif final == "knockdown" and inheritance == "recessive":
        flag = "recessive (G2P): knockdown unlikely to help"
    elif final == "knockdown" and intolerant:
        flag = "LoF-intolerant: full knockdown risky"
    elif final == "splice/upregulation" and inheritance == "recessive":
        flag = "recessive LoF (G2P); do not knock down"
    elif final == "splice/upregulation" and inheritance == "dominant" and intolerant:
        flag = "dominant LoF (G2P): haploinsufficiency"
    elif final == "splice/upregulation" and inheritance == "dominant":
        flag = "dominant LoF (G2P)"
    elif final == "splice/upregulation" and not inheritance and tolerance == "LoF-tolerant":
        flag = "likely recessive LoF; do not knock down"
    elif final == "splice/upregulation" and not inheritance and intolerant:
        flag = "possible haploinsufficiency"
    elif final == "modifier":
        flag = "association only; effect direction unknown"

    if final == "knockdown" and intolerant:
        note = (
            "Caution: LoF-intolerant gene. Full knockdown may be toxic; consider partial or allele-specific."
        )
    elif final == "knockdown":
        note = "Knockdown plausible if disease mechanism is toxic gain of function."
    elif final == "splice/upregulation" and tolerance == "LoF-tolerant":
        note = "Likely recessive LoF. Do NOT knock down. Splice correction only if variants are splice-site."
    elif final == "splice/upregulation" and intolerant:
        note = "Likely haploinsufficiency. Upregulation or splice correction."
    elif final == "splice/upregulation":
        note = "Likely LoF disease; no constraint data."
    elif final == "ambiguous":
        note = "Mixed variant types. Mechanism unclear; review manually."
    elif final == "modifier":
        note = "Genetic association without variant-level evidence. Mechanism and direction are unknown; review the locus."
    else:
        note = "Too little ClinVar data. Classify manually (repeat expansions and non-coding mechanisms are invisible here)."

    row.update(
        n_classified=n_classified,
        frac_lof=frac_lof,
        frac_splice_related=frac_splice,
        no_variant_evidence=no_variants,
        clinvar_call=clinvar,
        g2p_call=g2p,
        final_call=final,
        call_source=source_name,
        lof_intolerant=intolerant,
        lof_tolerance=tolerance,
        splice_correctable=final == "splice/upregulation" and frac_splice is not None and frac_splice >= 0.30,
        flag=flag,
        note=note,
    )
    row["confidence_tier"], row["confidence_reason"] = _confidence(row)
    row["has_approved_drug"] = row.get("has_approved_drug")
    row["aso_precedent"] = row.get("aso_precedent") or ""
    row["has_aso_precedent"] = bool(row["aso_precedent"])
    row["completeness"] = "capped" if row.get("evidence_truncated") else "complete"
    return row


def classify_candidates(
    rows: list[dict[str, Any]],
    *,
    include_modifiers: bool = True,
    exclude_approved: bool = False,
    exclude_aso_precedent: bool = False,
    drug_lookup_complete: bool = False,
) -> list[dict[str, Any]]:
    classified = [classify_candidate(row) for row in rows]
    if exclude_approved:
        classified = [row for row in classified if row.get("has_approved_drug") is not True]
    allowed = {"knockdown", "splice/upregulation"}
    if include_modifiers:
        allowed.add("modifier")
    shortlist = [row for row in classified if row["final_call"] in allowed]
    if drug_lookup_complete:
        shortlist = [row for row in shortlist if row.get("has_approved_drug") is not True]
    if exclude_aso_precedent:
        shortlist = [row for row in shortlist if not row["has_aso_precedent"]]
    shortlist.sort(
        key=lambda row: (row["final_call"] == "modifier", -row["genetic_score"], -row["overall_score"])
    )
    positions = {row["ensembl_id"]: index for index, row in enumerate(shortlist, 1)}
    for row in classified:
        row["shortlist_position"] = positions.get(row["ensembl_id"])
    return classified


def validate_candidates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [row["ensembl_id"] for row in rows]
    assert len(ids) == len(set(ids)), "Duplicate Ensembl IDs"
    assert all(row["final_call"] in TRACKS for row in rows), "Unknown mechanism track"
    assert all(0 <= row["overall_score"] <= 1 and 0 <= row["genetic_score"] <= 1 for row in rows)
    for row in rows:
        if row.get("evidence_truncated"):
            assert row["n_evidence"] > row["n_evidence_returned"], "Incoherent truncation flag"
    counts = {track: sum(row["final_call"] == track for row in rows) for track in TRACKS}
    assert sum(counts.values()) == len(rows)
    return {"status": "PASS", "candidates": len(rows), "track_counts": counts}
