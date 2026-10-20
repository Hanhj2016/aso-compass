"""Opt-in bounded live ALS connectivity and schema smoke test."""

from app.core.settings import get_settings
from app.integrations.open_targets import OpenTargetsClient
from app.services.scientific_pipeline import run_pipeline


def main() -> None:
    settings = get_settings()
    parameters = {
        "page_size": 500,
        "min_score": 0.85,
        "min_genetic": 0.80,
        "max_genes_for_variants": 1,
        "max_genes_for_drugs": 1,
        "use_variants": True,
        "use_g2p": True,
        "check_drugs": True,
        "check_trials": True,
        "include_modifiers": True,
        "exclude_approved": False,
        "exclude_aso_precedent": False,
    }

    def progress(stage: str, message: str, current: int | None, total: int | None) -> None:
        print(stage, current, total, message, flush=True)

    rows, metadata, warnings = run_pipeline(
        OpenTargetsClient(
            settings.open_targets_url, settings.http_timeout_seconds, settings.http_retry_total
        ),
        "MONDO_0004976",
        parameters,
        progress,
        settings.clinical_trials_url,
    )
    print(
        {
            "candidates": [(row["gene_symbol"], row["final_call"]) for row in rows],
            "metadata": metadata,
            "warnings": warnings,
        }
    )


if __name__ == "__main__":
    main()
