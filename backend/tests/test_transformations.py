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
