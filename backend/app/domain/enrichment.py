"""Pure drug and trial transformations ported from the v4.1 reference engine."""

from __future__ import annotations

import math
import re
from typing import Any

ASO_NAME_PATTERN = (
    r"(^|[-_])(aso|sirna)([-_0-9]|$)|tofersen|tominersen|inotersen|eplontersen|"
    r"nusinersen|vutrisiran|patisiran|givosiran|lumasiran|inclisiran|casimersen|"
    r"eteplirsen|golodirsen|viltolarsen"
)
DRUG_LIKE_TYPES = {"DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"}


def stage_rank(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not math.isnan(float(value)):
        return float(min(math.floor(float(value)), 4))
    text = str(value).upper()
    if "APPROV" in text or "MARKET" in text:
        return 4.0
    digits = [int(item) for item in re.findall(r"\d+", text)]
    if digits:
        return float(min(max(digits), 4))
    if any(item in text for item in ("PRECLIN", "EARLY", "UNKNOWN", "NOT")):
        return 0.0
    return None


def stage_label(rank: float | None) -> str:
    if rank is None or math.isnan(rank):
        return "Unknown stage"
    if rank >= 4:
        return "Approved"
    if rank >= 3:
        return "Phase 3"
    if rank >= 2:
        return "Phase 2"
    if rank >= 1:
        return "Phase 1"
    return "Early"


def summarize_drug_rows(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    empty = {
        "n_drugs": 0,
        "drug_max_stage": None,
        "drug_status": "None found",
        "approved_drugs": "",
        "has_approved_drug": False,
        "oligo_drug": "-",
        "oligo_names": "",
        "aso_drug": "-",
        "aso_names": "",
    }
    records: list[dict[str, Any]] = []
    for row in rows or []:
        drug = row.get("drug") or {}
        name = drug.get("name")
        if not name:
            continue
        ranks = [stage_rank(row.get(key)) for key in ("maxClinicalStage", "clinicalStage", "phase")]
        ranks += [stage_rank(drug.get(key)) for key in ("maximumClinicalStage", "maximumClinicalTrialPhase")]
        if drug.get("isApproved") is True:
            ranks.append(4.0)
        valid = [rank for rank in ranks if rank is not None]
        records.append(
            {
                "name": str(name),
                "type": str(drug.get("drugType") or ""),
                "rank": max(valid) if valid else None,
            }
        )
    if not records:
        return empty
    per_drug: dict[str, dict[str, Any]] = {}
    for record in records:
        old = per_drug.get(record["name"])
        if old is None or (
            record["rank"] is not None and (old["rank"] is None or record["rank"] > old["rank"])
        ):
            per_drug[record["name"]] = record
    drugs = list(per_drug.values())
    valid_ranks = [drug["rank"] for drug in drugs if drug["rank"] is not None]
    top = max(valid_ranks) if valid_ranks else None
    top_names = [drug["name"] for drug in drugs if top is None or drug["rank"] == top]
    shown = ", ".join(top_names[:2]) + (f" (+{len(top_names) - 2})" if len(top_names) > 2 else "")
    approved = [drug["name"] for drug in drugs if drug["rank"] is not None and drug["rank"] >= 4]
    oligos = [drug for drug in drugs if re.search(r"oligonucleotide|antisense|sirna", drug["type"], re.I)]
    aso = [drug for drug in oligos if re.search(ASO_NAME_PATTERN, drug["name"], re.I)]
    oligo_ranks = [drug["rank"] for drug in oligos if drug["rank"] is not None]
    oligo_label = stage_label(max(oligo_ranks)) if oligo_ranks else ("Unknown stage" if oligos else "-")
    aso_ranks = [drug["rank"] for drug in aso if drug["rank"] is not None]
    return {
        "n_drugs": len(drugs),
        "drug_max_stage": stage_label(top),
        "drug_status": f"{stage_label(top)}: {shown}",
        "approved_drugs": "; ".join(approved[:5]),
        "has_approved_drug": bool(approved),
        "oligo_drug": oligo_label,
        "oligo_names": ", ".join(drug["name"] for drug in oligos[:2]),
        "aso_drug": stage_label(max(aso_ranks)) if aso_ranks else ("Unknown stage" if aso else "-"),
        "aso_names": ", ".join(drug["name"] for drug in aso[:2]),
    }


def parse_trial(study: dict[str, Any]) -> dict[str, Any]:
    protocol = study.get("protocolSection") or {}
    identity = protocol.get("identificationModule") or {}
    interventions = (protocol.get("armsInterventionsModule") or {}).get("interventions") or []
    names: list[str] = []
    types: list[str] = []
    for item in interventions:
        names.extend([item.get("name") or "", *(item.get("otherNames") or [])])
        types.append(str(item.get("type") or "").upper())
    phases = [str(value).upper() for value in (protocol.get("designModule") or {}).get("phases") or []]
    numbers = [int(value) for phase in phases for value in re.findall(r"\d+", phase)]
    status = str((protocol.get("statusModule") or {}).get("overallStatus") or "unknown")
    title = identity.get("briefTitle") or ""
    return {
        "nct": identity.get("nctId") or "",
        "title": title,
        "status": status.lower().replace("_", " "),
        "phase": "Ph" + "/".join(map(str, numbers)) if numbers else "Ph?",
        "phase_max": max(numbers) if numbers else None,
        "is_drug": bool(interventions)
        and (not any(types) or any(value in DRUG_LIKE_TYPES for value in types)),
        "interventions": ", ".join(dict.fromkeys(value for value in names if value)),
        "text": " ".join([title, identity.get("officialTitle") or "", *names]),
        "summary": (protocol.get("descriptionModule") or {}).get("briefSummary") or "",
    }


def match_trials_to_genes(
    trials: list[dict[str, Any]], symbols: list[str]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    valid_symbols = list(
        dict.fromkeys(
            str(symbol)
            for symbol in symbols
            if len(str(symbol)) >= 3 and re.match(r"^[A-Za-z0-9]+$", str(symbol))
        )
    )
    matches: list[dict[str, Any]] = []
    ordered = sorted(
        trials, key=lambda row: (-(row["phase_max"] if row["phase_max"] is not None else -1), row["nct"])
    )
    records = [
        {key: trial[key] for key in ("nct", "phase", "status", "is_drug", "interventions", "title")}
        for trial in ordered
    ]
    for trial in ordered:
        strong_tokens = set(re.split(r"[^A-Za-z0-9]+", trial["text"]))
        weak_tokens = set(re.split(r"[^A-Za-z0-9]+", trial["summary"]))
        strong = [
            symbol for symbol in valid_symbols if symbol in strong_tokens or symbol.upper() in strong_tokens
        ]
        weak = [
            symbol
            for symbol in valid_symbols
            if (symbol in weak_tokens or symbol.upper() in weak_tokens) and symbol not in strong
        ]
        if trial["is_drug"]:
            matches.extend(
                {"gene_symbol": symbol, "weak": symbol in weak, **trial} for symbol in strong + weak
            )
    result: dict[str, dict[str, Any]] = {}
    for symbol in valid_symbols:
        hits = [row for row in matches if row["gene_symbol"] == symbol]
        if hits:
            best = hits[0]
            result[symbol] = {
                "aso_trial_n": len(hits),
                "aso_trial_weak": sum(bool(row["weak"]) for row in hits),
                "aso_trial_best": f"{best['phase']} {best['status']}",
                "aso_trial_ids": ", ".join(row["nct"] for row in hits[:3]),
            }
    return result, records
