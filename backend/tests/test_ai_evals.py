from app.evals.ai_outputs import evaluate_case, load_dataset, main, run_dataset


def test_review_ready_ai_fixture_suite_passes_deterministic_graders() -> None:
    dataset = load_dataset()
    result = run_dataset(dataset)

    assert result.passed
    assert result.case_count == 6
    assert result.passed_count == 6
    assert result.pending_scientific_review_count == 6
    assert not result.scientific_review_complete
    assert {case.feature for case in dataset.cases} == {
        "candidate_explanation",
        "run_summary",
        "candidate_comparison",
    }
    tags = {tag for case in dataset.cases for tag in case.tags}
    assert {
        "all_tracks",
        "association_only",
        "missingness",
        "no_winner",
        "therapeutic_precedent",
        "truncation",
        "upstream_failure",
    } <= tags


def test_eval_grader_rejects_unverified_source() -> None:
    case = load_dataset().cases[0].model_copy(deep=True)
    case.output["decision_basis"][0]["source_ids"] = ["invented:source"]

    result = evaluate_case(case)

    assert not result.passed
    grounding = next(check for check in result.checks if check.name == "source_grounding")
    assert not grounding.passed
    assert grounding.detail == "AI_SOURCE_VALIDATION_FAILED"


def test_eval_grader_rejects_recommendation_language() -> None:
    case = load_dataset().cases[0].model_copy(deep=True)
    case.output["summary"] += " The best target is this candidate."

    result = evaluate_case(case)

    assert not result.passed
    safety = next(check for check in result.checks if check.name == "safety_boundaries")
    assert not safety.passed
    assert "best target is" in safety.detail


def test_eval_grader_rejects_changed_run_counts() -> None:
    case = next(case for case in load_dataset().cases if case.case_id == "summary_all_tracks_quick_mode")
    changed = case.model_copy(deep=True)
    changed.output["track_breakdown"][0]["count"] = 99

    result = evaluate_case(changed)

    assert not result.passed
    counts = next(check for check in result.checks if check.name == "deterministic_track_counts")
    assert not counts.passed


def test_eval_grader_rejects_changed_candidate_identity() -> None:
    case = next(case for case in load_dataset().cases if case.case_id == "compare_modifier_vs_insufficient")
    changed = case.model_copy(deep=True)
    changed.output["candidate_summaries"][1]["gene_symbol"] = "GENEC"

    result = evaluate_case(changed)

    assert not result.passed
    grounding = next(check for check in result.checks if check.name == "source_grounding")
    assert not grounding.passed
    assert grounding.detail == "AI_CANDIDATE_VALIDATION_FAILED"


def test_strict_cli_gate_distinguishes_engineering_pass_from_pending_review(capsys) -> None:
    assert main([]) == 0
    capsys.readouterr()
    assert main(["--require-scientific-review"]) == 2
