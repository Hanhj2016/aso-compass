import json
from pathlib import Path

from app.domain.classification import classify_candidates, validate_candidates


def test_golden_five_tracks_and_precedence() -> None:
    fixture = Path(__file__).parent / "fixtures" / "golden_candidates.json"
    rows = classify_candidates(json.loads(fixture.read_text()))
    by_id = {row["ensembl_id"]: row for row in rows}
    assert [by_id[f"ENSG_{key}"]["final_call"] for key in ("KD", "SPL", "AMB", "MOD", "INS")] == [
        "knockdown",
        "splice/upregulation",
        "ambiguous",
        "modifier",
        "insufficient data",
    ]
    assert by_id["ENSG_G2P"]["final_call"] == "knockdown"
    assert by_id["ENSG_G2P"]["call_source"] == "G2P"
    assert by_id["ENSG_G2P"]["flag"] == "ClinVar and G2P disagree"
    assert by_id["ENSG_CUR"]["final_call"] == "splice/upregulation"
    assert by_id["ENSG_CUR"]["call_source"] == "curated"
    result = validate_candidates(rows)
    assert result["status"] == "PASS"
    assert set(result["track_counts"]) == {
        "knockdown",
        "splice/upregulation",
        "ambiguous",
        "modifier",
        "insufficient data",
    }


def test_threshold_boundaries_match_reference() -> None:
    base = {
        "gene_symbol": "X",
        "gene_name": "X",
        "overall_score": 0.5,
        "genetic_score": 0.5,
        "loeuf": None,
        "n_evidence": 20,
        "n_evidence_returned": 20,
        "evidence_truncated": False,
        "n_splice": 0,
        "n_splice_extra": 0,
        "g2p_mech": None,
        "inheritance": None,
        "strategy": None,
    }
    rows = []
    for ens, lof, missense in [("A", 3, 2), ("B", 5, 15), ("C", 6, 4), ("D", 1, 3)]:
        rows.append({**base, "ensembl_id": ens, "n_lof": lof, "n_missense": missense})
    calls = {row["ensembl_id"]: row["final_call"] for row in classify_candidates(rows)}
    assert calls == {
        "A": "splice/upregulation",
        "B": "knockdown",
        "C": "splice/upregulation",
        "D": "insufficient data",
    }
