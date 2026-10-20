from app.domain.enrichment import match_trials_to_genes, parse_trial, summarize_drug_rows


def test_drug_summary_matches_reference_deduplication_and_aso_detection() -> None:
    rows = [
        {
            "maxClinicalStage": 4,
            "drug": {"name": "TOFERSEN", "drugType": "Antisense oligonucleotide", "isApproved": True},
        },
        {
            "maxClinicalStage": 2,
            "drug": {"name": "TOFERSEN", "drugType": "Antisense oligonucleotide"},
        },
        {"clinicalStage": 3, "drug": {"name": "SMALL-1", "drugType": "Small molecule"}},
    ]
    result = summarize_drug_rows(rows)
    assert result["n_drugs"] == 2
    assert result["drug_status"] == "Approved: TOFERSEN"
    assert result["approved_drugs"] == "TOFERSEN"
    assert result["aso_drug"] == "Approved"
    assert result["aso_names"] == "TOFERSEN"


def test_trial_parser_and_matching_distinguish_strong_and_summary_only_hits() -> None:
    strong = parse_trial(
        {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT1", "briefTitle": "SOD1 antisense study"},
                "armsInterventionsModule": {"interventions": [{"name": "tofersen", "type": "DRUG"}]},
                "designModule": {"phases": ["PHASE2"]},
                "statusModule": {"overallStatus": "RECRUITING"},
            }
        }
    )
    weak = parse_trial(
        {
            "protocolSection": {
                "identificationModule": {"nctId": "NCT2", "briefTitle": "Oligonucleotide study"},
                "armsInterventionsModule": {"interventions": [{"name": "candidate", "type": "DRUG"}]},
                "descriptionModule": {"briefSummary": "Designed for SOD1-associated ALS."},
                "designModule": {"phases": ["PHASE1"]},
            }
        }
    )
    matches, records = match_trials_to_genes([weak, strong], ["SOD1", "AB"])
    assert len(records) == 2
    assert matches["SOD1"]["aso_trial_n"] == 2
    assert matches["SOD1"]["aso_trial_weak"] == 1
    assert matches["SOD1"]["aso_trial_best"].startswith("Ph2")
