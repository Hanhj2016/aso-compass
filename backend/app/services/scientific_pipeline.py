from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from typing import Any

from app.domain.classification import classify_candidates, validate_candidates
from app.domain.enrichment import match_trials_to_genes, parse_trial, summarize_drug_rows
from app.integrations.open_targets import (
    ASSOCIATIONS,
    CONSTRAINTS,
    G2P,
    G2P_BASIC,
    VARIANTS,
    OpenTargetsClient,
)

LOF_IDS = {"SO_0001587", "SO_0001589", "SO_0001574", "SO_0001575", "SO_0002012", "SO_0001893"}
LOF_LABELS = {
    "stop gained",
    "frameshift variant",
    "splice acceptor variant",
    "splice donor variant",
    "start lost",
    "transcript ablation",
}
SPLICE_IDS = {"SO_0001574", "SO_0001575"}
SPLICE_LABELS = {"splice acceptor variant", "splice donor variant"}
MISSENSE_IDS = {"SO_0001583", "SO_0001821", "SO_0001822"}
MISSENSE_LABELS = {"missense variant", "inframe insertion", "inframe deletion", "protein altering variant"}
SPLICE_EXTRA_IDS = {"SO_0001630", "SO_0001627", "SO_0001624", "SO_0001623", "SO_0001819"}
SPLICE_EXTRA_LABELS = {
    "splice region variant",
    "intron variant",
    "3 prime utr variant",
    "5 prime utr variant",
    "synonymous variant",
}


def _score(rows: list[dict[str, Any]] | None) -> float:
    return next(
        (float(row.get("score") or 0) for row in rows or [] if row.get("id") == "genetic_association"), 0
    )


def _variant_counts(data: dict[str, Any], ensembl_id: str) -> dict[str, Any]:
    evidence = (data.get("disease") or {}).get("evidences") or {}
    rows = evidence.get("rows") or []
    result: dict[str, Any] = {
        "ensembl_id": ensembl_id,
        "n_evidence": int(evidence.get("count") or 0),
        "n_evidence_returned": len(rows),
        "evidence_truncated": int(evidence.get("count") or 0) > len(rows),
        "n_lof": 0,
        "n_splice": 0,
        "n_splice_extra": 0,
        "n_missense": 0,
    }
    for row in rows:
        significances = row.get("clinicalSignificances") or []
        if significances and not any(
            re.match(r"^(likely )?pathogenic", str(value).lower().strip()) for value in significances
        ):
            continue
        consequence = row.get("variantFunctionalConsequence") or {}
        so_id = str(consequence.get("id") or "").replace(":", "_")
        label = str(consequence.get("label") or "").lower().replace("_", " ").strip()
        result["n_lof"] += int(so_id in LOF_IDS or label in LOF_LABELS)
        result["n_splice"] += int(so_id in SPLICE_IDS or label in SPLICE_LABELS)
        result["n_splice_extra"] += int(so_id in SPLICE_EXTRA_IDS or label in SPLICE_EXTRA_LABELS)
        result["n_missense"] += int(so_id in MISSENSE_IDS or label in MISSENSE_LABELS)
    return result


def _fetch_drug_batch(
    client: OpenTargetsClient, ids: list[str], field: str, selection: str
) -> list[dict[str, Any]]:
    ids_json = ",".join(json.dumps(identifier) for identifier in ids)
    data, _ = client.query(f"{{targets(ensemblIds:[{ids_json}]){{id {selection}}}}}")
    result = []
    for target in data.get("targets") or []:
        container = target.get(field) or {}
        result.append({"ensembl_id": target.get("id"), **summarize_drug_rows(container.get("rows"))})
    return result


def _discover_drug_query(client: OpenTargetsClient) -> tuple[str, str, str]:
    target_fields = client.type_fields("Target")
    if "drugAndClinicalCandidates" in target_fields:
        field, arguments = "drugAndClinicalCandidates", ["", "(size:500)"]
    elif "knownDrugs" in target_fields:
        field, arguments = "knownDrugs", ["(size:200)", ""]
    else:
        raise ValueError("Open Targets exposes no supported target drug field")
    container_type = target_fields[field]
    if not container_type:
        raise ValueError(f"Open Targets did not describe Target.{field}")
    container_fields = client.type_fields(container_type)
    row_type = container_fields.get("rows")
    if not row_type:
        raise ValueError(f"Open Targets did not describe Target.{field}.rows")
    row_fields = client.type_fields(row_type)
    drug_type = row_fields.get("drug")
    if not drug_type:
        raise ValueError(f"Open Targets did not describe Target.{field}.rows.drug")
    drug_fields = client.type_fields(drug_type)
    selected_row = [
        name for name in ("maxClinicalStage", "clinicalStage", "phase", "status") if name in row_fields
    ]
    selected_drug = [
        name
        for name in (
            "id",
            "name",
            "drugType",
            "maximumClinicalStage",
            "maximumClinicalTrialPhase",
            "isApproved",
        )
        if name in drug_fields
    ]
    if "name" not in selected_drug:
        raise ValueError("Open Targets drug type has no name field")
    for argument in arguments:
        selection = f"{field}{argument}{{rows{{{' '.join(selected_row)} drug{{{' '.join(selected_drug)}}}}}}}"
        try:
            _fetch_drug_batch(client, ["ENSG00000142168"], field, selection)
            return field, selection, f"Target.{field}"
        except Exception:
            continue
    raise ValueError("No generated Open Targets drug query was accepted")


def _fetch_trials(
    client: OpenTargetsClient, url: str, condition: str, max_pages: int = 5
) -> tuple[list[dict[str, Any]], list[str]]:
    studies: list[dict[str, Any]] = []
    hashes: list[str] = []
    token: str | None = None
    for _ in range(max_pages):
        params: dict[str, Any] = {
            "query.cond": condition,
            "query.term": "antisense OR oligonucleotide OR siRNA",
            "pageSize": 100,
            "format": "json",
        }
        if token:
            params["pageToken"] = token
        payload, query_hash = client.get_json(url, params)
        hashes.append(query_hash)
        studies.extend(payload.get("studies") or [])
        token = payload.get("nextPageToken")
        if not token:
            break
    return [parse_trial(study) for study in studies], hashes


def _precedent(row: dict[str, Any]) -> str:
    pieces: list[str] = []
    if row.get("aso_drug") not in (None, "-"):
        name = f"{row.get('aso_names')} " if row.get("aso_names") else ""
        pieces.append(f"Drug: {name}({row['aso_drug']})")
    if row.get("aso_trial_n", 0) and row["aso_trial_n"] > 0:
        weak = f"; {int(row['aso_trial_weak'])} via summary text" if row.get("aso_trial_weak", 0) > 0 else ""
        pieces.append(
            f"Trials: {int(row['aso_trial_n'])} (best {row.get('aso_trial_best', 'unknown')}{weak})"
        )
    return " | ".join(pieces)


def run_pipeline(
    client: OpenTargetsClient,
    disease_id: str,
    parameters: dict[str, Any],
    progress: Callable[[str, str, int | None, int | None], None],
    clinical_trials_url: str = "https://clinicaltrials.gov/api/v2/studies",
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    page_size = parameters["page_size"]
    progress("associations", "Fetching Open Targets associations", 0, None)
    first, first_hash = client.query(ASSOCIATIONS, {"id": disease_id, "index": 0, "size": page_size})
    disease = first.get("disease")
    if not disease:
        raise ValueError(f"Open Targets returned no disease for {disease_id}")
    association = disease["associatedTargets"]
    total = int(association.get("count") or 0)
    raw = list(association.get("rows") or [])
    for page in range(1, math.ceil(total / page_size)):
        data, _ = client.query(ASSOCIATIONS, {"id": disease_id, "index": page, "size": page_size})
        raw.extend(data["disease"]["associatedTargets"].get("rows") or [])
        progress(
            "associations", "Fetching Open Targets associations", min((page + 1) * page_size, total), total
        )
    candidates: list[dict[str, Any]] = []
    for item in raw:
        target = item.get("target") or {}
        record: dict[str, Any] = {
            "ensembl_id": str(target.get("id") or ""),
            "gene_symbol": str(target.get("approvedSymbol") or ""),
            "gene_name": target.get("approvedName"),
            "overall_score": float(item.get("score") or 0),
            "genetic_score": _score(item.get("datatypeScores")),
        }
        if (
            record["overall_score"] >= parameters["min_score"]
            and record["genetic_score"] >= parameters["min_genetic"]
        ):
            candidates.append(record)
    candidates.sort(key=lambda row: -row["overall_score"])
    if not candidates:
        raise ValueError("No genes passed the score thresholds")

    warnings: list[str] = []
    ids: list[str] = [str(row["ensembl_id"]) for row in candidates[: parameters["max_genes_for_variants"]]]
    constraint_by_id: dict[str, float | None] = {}
    progress("constraints", "Fetching gene constraint", 0, len(ids))
    for start in range(0, len(ids), 50):
        batch = ids[start : start + 50]
        try:
            data, _ = client.query(CONSTRAINTS, {"ids": batch})
            for target in data.get("targets") or []:
                values = [
                    x.get("oeUpper")
                    for x in target.get("geneticConstraint") or []
                    if x.get("constraintType") == "lof"
                ]
                constraint_by_id[target["id"]] = (
                    float(values[0]) if values and values[0] is not None else None
                )
        except Exception:
            warnings.append(
                f"Constraint lookup failed for a batch of {len(batch)} genes; values remain unknown."
            )
        progress("constraints", "Fetching gene constraint", min(start + len(batch), len(ids)), len(ids))

    variants: dict[str, dict[str, Any]] = {}
    if parameters["use_variants"]:
        for index, ensembl_id in enumerate(ids, 1):
            try:
                data, _ = client.query(VARIANTS, {"disease": disease_id, "genes": [ensembl_id], "size": 500})
                variants[ensembl_id] = _variant_counts(data, ensembl_id)
            except Exception:
                warnings.append(
                    f"Variant lookup failed for {ensembl_id}; evidence remains unknown, not negative."
                )
            progress("variants", "Classifying ClinVar evidence", index, len(ids))

    g2p_by_id: dict[str, dict[str, str | None]] = {}
    if parameters["use_g2p"]:
        for start in range(0, len(ids), 25):
            batch = ids[start : start + 25]
            try:
                try:
                    data, _ = client.query(G2P, {"disease": disease_id, "genes": batch})
                except Exception:
                    data, _ = client.query(G2P_BASIC, {"disease": disease_id, "genes": batch})
                rows = ((data.get("disease") or {}).get("evidences") or {}).get("rows") or []
                grouped: dict[str, list[dict[str, Any]]] = {}
                for item in rows:
                    target_id = (item.get("target") or {}).get("id")
                    if target_id:
                        grouped.setdefault(str(target_id), []).append(item)
                for ens, evidence_rows in grouped.items():
                    text = " ".join(
                        str(item.get("variantFunctionalConsequence") or {}).lower() for item in evidence_rows
                    )
                    allelic = " ".join(
                        str(item.get("allelicRequirements") or []).lower() for item in evidence_rows
                    )
                    lof = bool(re.search(r"so[_:]0002054|loss.of.function", text))
                    gof = bool(
                        re.search(r"so[_:]0002053|gain.of.function|so[_:]0002052|dominant.negative", text)
                    )
                    g2p_by_id[ens] = {
                        "g2p_mech": "mixed" if lof and gof else "LoF" if lof else "GoF/DN" if gof else None,
                        "inheritance": "both"
                        if "biallelic" in allelic and "monoallelic" in allelic
                        else "recessive"
                        if "biallelic" in allelic
                        else "dominant"
                        if "monoallelic" in allelic
                        else None,
                    }
            except Exception:
                warnings.append(
                    f"Gene2Phenotype lookup failed for a batch of {len(batch)} genes; evidence remains unknown."
                )
            progress("g2p", "Fetching Gene2Phenotype evidence", min(start + len(batch), len(ids)), len(ids))

    drug_by_id: dict[str, dict[str, Any]] = {}
    drug_source = "not checked"
    if parameters.get("check_drugs", True):
        progress("drugs", "Fetching target drug and oligonucleotide precedent", 0, None)
        try:
            field, selection, drug_source = _discover_drug_query(client)
            drug_ids = [
                str(row["ensembl_id"]) for row in candidates[: parameters.get("max_genes_for_drugs", 300)]
            ]
            for start in range(0, len(drug_ids), 25):
                batch = drug_ids[start : start + 25]
                for result in _fetch_drug_batch(client, batch, field, selection):
                    drug_by_id[str(result.pop("ensembl_id"))] = result
                progress(
                    "drugs",
                    "Fetching target drug and oligonucleotide precedent",
                    min(start + len(batch), len(drug_ids)),
                    len(drug_ids),
                )
        except Exception:
            drug_source = "lookup failed"
            warnings.append("Open Targets drug lookup failed; drug evidence remains unknown, not negative.")

    trials_by_symbol: dict[str, dict[str, Any]] = {}
    trial_records: list[dict[str, Any]] = []
    trial_hashes: list[str] = []
    trial_source = "not checked"
    if parameters.get("check_trials", True):
        progress("trials", "Searching ClinicalTrials.gov for oligonucleotide trials", 0, None)
        try:
            trials, trial_hashes = _fetch_trials(
                client, clinical_trials_url, str(disease.get("name") or disease_id)
            )
            trials_by_symbol, trial_records = match_trials_to_genes(
                trials, [str(row["gene_symbol"]) for row in candidates]
            )
            trial_source = "ClinicalTrials.gov API v2"
        except Exception:
            trial_source = "lookup failed"
            warnings.append("ClinicalTrials.gov lookup failed; trial evidence remains unknown, not negative.")

    for row in candidates:
        ens = str(row["ensembl_id"])
        row.update(
            {
                "loeuf": constraint_by_id.get(ens),
                "n_evidence": None,
                "n_evidence_returned": None,
                "evidence_truncated": None,
                "n_lof": None,
                "n_splice": None,
                "n_splice_extra": None,
                "n_missense": None,
                "g2p_mech": None,
                "inheritance": None,
                "strategy": None,
                "drug_status": "not checked",
                "has_approved_drug": None,
                "aso_precedent": "",
            }
        )
        row.update(variants.get(ens, {}))
        row.update(g2p_by_id.get(ens, {}))
        if ens in drug_by_id:
            row.update(drug_by_id[ens])
        elif drug_source == "lookup failed":
            row["drug_status"] = "lookup failed"
        row.update(trials_by_symbol.get(str(row["gene_symbol"]), {}))
        row["aso_precedent"] = _precedent(row)
    classified = classify_candidates(
        candidates,
        include_modifiers=parameters["include_modifiers"],
        exclude_approved=parameters["exclude_approved"],
        exclude_aso_precedent=parameters["exclude_aso_precedent"],
        drug_lookup_complete=drug_source not in {"not checked", "lookup failed"},
    )
    validation = validate_candidates(classified)
    try:
        meta, _ = client.query("{meta{dataVersion{year month iteration}}}")
        version = (meta.get("meta") or {}).get("dataVersion") or {}
        release = (
            ".".join(
                str(version[key]) for key in ("year", "month", "iteration") if version.get(key) is not None
            )
            or "unknown"
        )
    except Exception:
        release = "unknown"
        warnings.append("Open Targets release lookup failed; release metadata remains unknown.")
    metadata = {
        "disease_label": disease.get("name"),
        "open_targets_release": release,
        "linked_genes": total,
        "passing_genes": len(classified),
        "association_query_hash": first_hash,
        "evidence_cap_per_gene": 500,
        "evidence_truncated_genes": sum(row.get("evidence_truncated") is True for row in classified),
        "drug_source": drug_source,
        "trial_source": trial_source,
        "trial_query_hashes": trial_hashes,
        "condition_trial_count": len(trial_records),
    }
    return classified, {**metadata, "validation": validation}, warnings
