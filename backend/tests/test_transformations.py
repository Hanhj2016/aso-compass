from app.services.scientific_pipeline import _variant_counts


def test_variant_transform_preserves_labels_pathogenic_filter_and_truncation() -> None:
    data = {
        "disease": {
            "evidences": {
                "count": 4,
                "rows": [
                    {
                        "variantFunctionalConsequence": {
                            "id": "SO:0001574",
                            "label": "splice_acceptor_variant",
                        },
                        "clinicalSignificances": ["Pathogenic"],
                        "id": "eva-1",
                        "variantRsId": "rs1",
                        "confidence": "criteria provided, multiple submitters, no conflicts",
                        "evidenceDate": "2024-02-01",
                        "releaseDate": "2024-03-01",
                        "diseaseFromSourceId": "C1",
                        "diseaseFromSource": "Test condition",
                    },
                    {
                        "variantFunctionalConsequence": {"id": "", "label": "missense_variant"},
                        "clinicalSignificances": ["Likely pathogenic"],
                    },
                    {
                        "variantFunctionalConsequence": {"id": "SO:0001587", "label": "stop gained"},
                        "clinicalSignificances": ["Benign"],
                    },
                ],
            }
        }
    }
    result = _variant_counts(data, "ENSG1")
    assert result["evidence_truncated"] is True
    assert result["n_evidence_returned"] == 3
    assert result["n_lof"] == 1
    assert result["n_splice"] == 1
    assert result["n_missense"] == 1
    interpretation = result["clinvar_interpretation"]
    assert interpretation["metadata_status"] == "partial"
    assert interpretation["review_status_counts"] == {
        "criteria provided, multiple submitters, no conflicts": 1
    }
    assert interpretation["review_star_counts"] == {"2": 1}
    assert interpretation["conflict_records"] == 0
    assert interpretation["submitter_count"] is None
    assert interpretation["latest_evidence_date"] == "2024-02-01"
    assert interpretation["representative_records"][0]["rs_id"] == "rs1"
