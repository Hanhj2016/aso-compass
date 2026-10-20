"""Guided Python port of aso_target_finder_v4.R for Google Colab."""

from __future__ import annotations

import math
import re
import time
import warnings
import json
import html
import platform
import hashlib
from importlib.metadata import version as package_version
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"

LOF_SO_IDS = {"SO_0001587", "SO_0001589", "SO_0001574", "SO_0001575", "SO_0002012", "SO_0001893"}
LOF_LABELS = {"stop gained", "frameshift variant", "splice acceptor variant", "splice donor variant", "start lost", "transcript ablation"}
SPLICE_SO_IDS = {"SO_0001574", "SO_0001575"}
SPLICE_LABELS = {"splice acceptor variant", "splice donor variant"}
MISSENSE_SO_IDS = {"SO_0001583", "SO_0001821", "SO_0001822"}
MISSENSE_LABELS = {"missense variant", "inframe insertion", "inframe deletion", "protein altering variant"}
SPLICE_EXTRA_SO_IDS = {"SO_0001630", "SO_0001627", "SO_0001624", "SO_0001623", "SO_0001819"}
SPLICE_EXTRA_LABELS = {"splice region variant", "intron variant", "3 prime utr variant", "5 prime utr variant", "synonymous variant"}
ASO_NAME_PATTERN = r"(^|[-_])(aso|sirna)([-_0-9]|$)|tofersen|tominersen|inotersen|eplontersen|nusinersen|vutrisiran|patisiran|givosiran|lumasiran|inclisiran|casimersen|eteplirsen|golodirsen|viltolarsen"
DRUG_LIKE_TYPES = {"DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"}


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _normalise_so(value: Any) -> str:
    return str(value or "").replace(":", "_")


def _normalise_label(value: Any) -> str:
    return str(value or "").lower().replace("_", " ").strip()


class OpenTargetsError(RuntimeError):
    pass


class OpenTargetsClient:
    def __init__(self, endpoint: str = ENDPOINT, timeout: float = 60.0,
                 cache_dir: str | Path | None = None, refresh_cache: bool = False,
                 cache_ttl_hours: float = 24.0):
        self.endpoint = endpoint
        self.timeout = timeout
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.refresh_cache = refresh_cache
        self.cache_ttl_seconds = cache_ttl_hours * 3600
        self.cache_hits = 0
        self.cache_misses = 0
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        retry = Retry(total=4, connect=4, read=4, backoff_factor=0.8,
                      status_forcelist=(429, 500, 502, 503, 504),
                      allowed_methods=frozenset({"POST", "GET"}))
        self.session = requests.Session()
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update({"User-Agent": "aso-target-finder-colab/4.1-guided"})

    def query(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        variables = variables or {}
        cache_path = None
        if self.cache_dir is not None:
            key_data = json.dumps({"endpoint": self.endpoint, "query": query, "variables": variables}, sort_keys=True)
            key = hashlib.sha256(key_data.encode()).hexdigest()
            cache_path = self.cache_dir / f"{key}.json"
            fresh = cache_path.exists() and (time.time() - cache_path.stat().st_mtime <= self.cache_ttl_seconds)
            if fresh and not self.refresh_cache:
                self.cache_hits += 1
                return json.loads(cache_path.read_text())
        self.cache_misses += 1
        try:
            response = self.session.post(
                self.endpoint,
                json={"query": query, "variables": variables},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise OpenTargetsError(f"Open Targets request failed: {exc}") from exc
        if payload.get("errors"):
            messages = " | ".join(str(e.get("message", e)) for e in payload["errors"])
            raise OpenTargetsError(f"GraphQL error: {messages}")
        data = payload.get("data") or {}
        if cache_path is not None:
            cache_path.write_text(json.dumps(data))
        return data

    def get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Cached/retried JSON GET, used for ClinicalTrials.gov."""
        cache_path = None
        if self.cache_dir is not None:
            key_data = json.dumps({"url": url, "params": params}, sort_keys=True)
            cache_path = self.cache_dir / f"get_{hashlib.sha256(key_data.encode()).hexdigest()}.json"
            fresh = cache_path.exists() and time.time() - cache_path.stat().st_mtime <= self.cache_ttl_seconds
            if fresh and not self.refresh_cache:
                self.cache_hits += 1
                return json.loads(cache_path.read_text())
        self.cache_misses += 1
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise OpenTargetsError(f"JSON request failed: {exc}") from exc
        if cache_path is not None:
            cache_path.write_text(json.dumps(payload))
        return payload

    @staticmethod
    def _unwrap_type(type_node: dict[str, Any] | None) -> str | None:
        while type_node and not type_node.get("name") and type_node.get("ofType"):
            type_node = type_node["ofType"]
        return type_node.get("name") if type_node else None

    def type_fields(self, type_name: str) -> dict[str, str | None]:
        query = """query TypeFields($name: String!) {
          __type(name: $name) { fields { name type { kind name ofType { kind name ofType { kind name ofType { kind name } } } } } }
        }"""
        node = self.query(query, {"name": type_name}).get("__type") or {}
        return {f["name"]: self._unwrap_type(f.get("type")) for f in node.get("fields") or []}


def _datatype_score(rows: list[dict[str, Any]] | None, wanted: str) -> float:
    for row in rows or []:
        if row.get("id") == wanted:
            return float(row.get("score") or 0)
    return 0.0


def _stage_rank(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(min(math.floor(value), 4))
    text = str(value).upper()
    if "APPROV" in text or "MARKET" in text:
        return 4.0
    digits = [int(x) for x in re.findall(r"\d+", text)]
    if digits:
        return float(min(max(digits), 4))
    if any(x in text for x in ("PRECLIN", "EARLY", "UNKNOWN", "NOT")):
        return 0.0
    return None


def _stage_label(rank: float | None) -> str:
    if rank is None or pd.isna(rank): return "Unknown stage"
    if rank >= 4: return "Approved"
    if rank >= 3: return "Phase 3"
    if rank >= 2: return "Phase 2"
    if rank >= 1: return "Phase 1"
    return "Early"


def _summarise_drug_rows(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    empty = {"n_drugs": 0, "drug_max_stage": None, "drug_status": "None found",
             "approved_drugs": "", "has_approved_drug": False,
             "oligo_drug": "-", "oligo_names": "", "aso_drug": "-", "aso_names": ""}
    records: list[dict[str, Any]] = []
    for row in rows or []:
        drug = row.get("drug") or {}
        name = drug.get("name")
        if not name:
            continue
        ranks = [_stage_rank(row.get(k)) for k in ("maxClinicalStage", "clinicalStage", "phase")]
        ranks += [_stage_rank(drug.get(k)) for k in ("maximumClinicalStage", "maximumClinicalTrialPhase")]
        if drug.get("isApproved") is True:
            ranks.append(4.0)
        ranks = [r for r in ranks if r is not None]
        records.append({"name": str(name), "type": str(drug.get("drugType") or ""),
                        "rank": max(ranks) if ranks else None})
    if not records:
        return empty
    per_drug: dict[str, dict[str, Any]] = {}
    for record in records:
        old = per_drug.get(record["name"])
        if old is None or ((record["rank"] is not None) and (old["rank"] is None or record["rank"] > old["rank"])):
            per_drug[record["name"]] = record
    drugs = list(per_drug.values())
    valid = [d["rank"] for d in drugs if d["rank"] is not None]
    top = max(valid) if valid else None
    top_names = [d["name"] for d in drugs if top is None or d["rank"] == top]
    shown = ", ".join(top_names[:2]) + (f" (+{len(top_names)-2})" if len(top_names) > 2 else "")
    approved = [d["name"] for d in drugs if d["rank"] is not None and d["rank"] >= 4]
    oligo_rows = [d for d in drugs if re.search(r"oligonucleotide|antisense|sirna", d["type"], re.I)]
    aso_rows = [d for d in oligo_rows if re.search(ASO_NAME_PATTERN, d["name"], re.I)]
    oligos = [d["rank"] for d in oligo_rows]
    oligo_valid = [r for r in oligos if r is not None]
    oligo_rank = max(oligo_valid) if oligo_valid else (None if oligos else "absent")
    return {"n_drugs": len(drugs), "drug_max_stage": _stage_label(top),
            "drug_status": f"{_stage_label(top)}: {shown}",
            "approved_drugs": "; ".join(approved[:5]),
            "has_approved_drug": bool(approved),
            "oligo_drug": "-" if oligo_rank == "absent" else _stage_label(oligo_rank),
            "oligo_names": ", ".join(d["name"] for d in oligo_rows[:2]),
            "aso_drug": _stage_label(max((d["rank"] for d in aso_rows if d["rank"] is not None), default=None)) if aso_rows else "-",
            "aso_names": ", ".join(d["name"] for d in aso_rows[:2])}


def _discover_drug_query(client: OpenTargetsClient) -> dict[str, str]:
    target_fields = client.type_fields("Target")
    if "drugAndClinicalCandidates" in target_fields:
        field, args = "drugAndClinicalCandidates", ["", "(size: 500)"]
    elif "knownDrugs" in target_fields:
        field, args = "knownDrugs", ["(size: 200)", ""]
    else:
        raise OpenTargetsError("Target has neither drugAndClinicalCandidates nor knownDrugs")
    container_fields = client.type_fields(target_fields[field])
    row_type = container_fields.get("rows")
    if not row_type:
        raise OpenTargetsError(f"No rows field under Target.{field}")
    row_fields = client.type_fields(row_type)
    drug_type = row_fields.get("drug")
    if not drug_type:
        raise OpenTargetsError(f"No drug field in Target.{field}.rows")
    drug_fields_all = client.type_fields(drug_type)
    row_scalars = [x for x in ("maxClinicalStage", "clinicalStage", "phase", "status") if x in row_fields]
    drug_fields = [x for x in ("id", "name", "drugType", "maximumClinicalStage", "maximumClinicalTrialPhase", "isApproved") if x in drug_fields_all]
    if "name" not in drug_fields:
        raise OpenTargetsError("Drug type has no name field")
    for arg in args:
        selection = f'{field}{arg} {{ rows {{ {" ".join(row_scalars)} drug {{ {" ".join(drug_fields)} }} }} }}'
        setup = {"field": field, "selection": selection, "label": f"Target.{field}"}
        try:
            _fetch_drugs_batch(client, ["ENSG00000142168"], setup)
            return setup
        except OpenTargetsError:
            pass
    raise OpenTargetsError("None of the generated drug queries were accepted by the API")


def _fetch_drugs_batch(client: OpenTargetsClient, ids: list[str], setup: dict[str, str]) -> list[dict[str, Any]]:
    ids_json = ",".join(f'"{x}"' for x in ids)
    query = f'{{ targets(ensemblIds: [{ids_json}]) {{ id {setup["selection"]} }} }}'
    result = []
    for target in client.query(query).get("targets") or []:
        field = target.get(setup["field"]) or {}
        result.append({"ensembl_id": target.get("id"), **_summarise_drug_rows(field.get("rows"))})
    return result


def _fetch_variant_counts(client: OpenTargetsClient, disease_id: str, ens_id: str, evidence_size: int = 500) -> dict[str, Any]:
    query = """query Evidence($disease: String!, $genes: [String!]!, $size: Int!) {
      disease(efoId: $disease) { evidences(ensemblIds: $genes, enableIndirect: true,
        datasourceIds: ["eva"], size: $size) { count rows {
          variantFunctionalConsequence { id label } clinicalSignificances
        } } }
    }"""
    ev = ((client.query(query, {"disease": disease_id, "genes": [ens_id], "size": evidence_size}).get("disease") or {}).get("evidences") or {})
    evidence_rows = ev.get("rows") or []
    total = int(ev.get("count") or 0)
    out = {"ensembl_id": ens_id, "n_evidence": total,
           "n_evidence_returned": len(evidence_rows),
           "evidence_truncated": total > len(evidence_rows),
           "n_lof": 0, "n_splice": 0, "n_splice_extra": 0, "n_missense": 0}
    for row in evidence_rows:
        sigs = row.get("clinicalSignificances") or []
        if sigs and not any(re.match(r"^(likely )?pathogenic", str(x).lower().strip()) for x in sigs):
            continue
        consequence = row.get("variantFunctionalConsequence") or {}
        so_id = _normalise_so(consequence.get("id"))
        label = _normalise_label(consequence.get("label"))
        out["n_lof"] += int(so_id in LOF_SO_IDS or label in LOF_LABELS)
        out["n_splice"] += int(so_id in SPLICE_SO_IDS or label in SPLICE_LABELS)
        out["n_splice_extra"] += int(so_id in SPLICE_EXTRA_SO_IDS or label in SPLICE_EXTRA_LABELS)
        out["n_missense"] += int(so_id in MISSENSE_SO_IDS or label in MISSENSE_LABELS)
    return out


def _fetch_g2p_batch(client: OpenTargetsClient, disease_id: str, ids: list[str]) -> list[dict[str, Any]]:
    def request(with_allelic: bool) -> list[dict[str, Any]]:
        extra = "allelicRequirements" if with_allelic else ""
        query = f'''{{ disease(efoId: "{disease_id}") {{ evidences(ensemblIds: {json.dumps(ids)},
          enableIndirect: true, datasourceIds: ["gene2phenotype"], size: 500) {{ rows {{
          target {{ id }} variantFunctionalConsequence {{ id label }} {extra} }} }} }} }}'''
        return (((client.query(query).get("disease") or {}).get("evidences") or {}).get("rows") or [])
    try:
        rows = request(True)
    except OpenTargetsError:
        rows = request(False)
    grouped: dict[str, list[dict[str, bool]]] = {}
    for row in rows:
        ens = (row.get("target") or {}).get("id")
        if not ens:
            continue
        cons = row.get("variantFunctionalConsequence") or {}
        text = f"{cons.get('id', '')} {cons.get('label', '')}".lower()
        allelic = " ".join(map(str, row.get("allelicRequirements") or [])).lower()
        grouped.setdefault(ens, []).append({
            "lof": bool(re.search(r"so[_:]0002054|loss.of.function", text)),
            "gof_dn": bool(re.search(r"so[_:]0002053|gain.of.function|so[_:]0002052|dominant.negative", text)),
            "biallelic": "biallelic" in allelic, "monoallelic": "monoallelic" in allelic,
        })
    result = []
    for ens, recs in grouped.items():
        lof, gof = any(x["lof"] for x in recs), any(x["gof_dn"] for x in recs)
        bi, mono = any(x["biallelic"] for x in recs), any(x["monoallelic"] for x in recs)
        result.append({"ensembl_id": ens,
                       "g2p_mech": "mixed" if lof and gof else "LoF" if lof else "GoF/DN" if gof else pd.NA,
                       "inheritance": "both" if bi and mono else "recessive" if bi else "dominant" if mono else pd.NA})
    return result


def _parse_trial(study: dict[str, Any]) -> dict[str, Any]:
    ps = study.get("protocolSection") or {}
    ident = ps.get("identificationModule") or {}
    interventions = (ps.get("armsInterventionsModule") or {}).get("interventions") or []
    names, types = [], []
    for item in interventions:
        names.extend([item.get("name") or "", *(item.get("otherNames") or [])])
        types.append(str(item.get("type") or "").upper())
    phases = [str(x).upper() for x in (ps.get("designModule") or {}).get("phases") or []]
    nums = [int(x) for phase in phases for x in re.findall(r"\d+", phase)]
    is_drug = bool(interventions) and (not any(types) or any(x in DRUG_LIKE_TYPES for x in types))
    status = str((ps.get("statusModule") or {}).get("overallStatus") or "unknown").lower().replace("_", " ")
    title = ident.get("briefTitle") or ""
    return {"nct": ident.get("nctId") or "", "title": title, "status": status,
            "phase": "Ph" + "/".join(map(str, nums)) if nums else "Ph?",
            "phase_max": max(nums) if nums else math.nan, "is_drug": is_drug,
            "interventions": ", ".join(dict.fromkeys(x for x in names if x)),
            "text": " ".join([title, ident.get("officialTitle") or "", *names]),
            "summary": (ps.get("descriptionModule") or {}).get("briefSummary") or ""}


def _fetch_aso_trials(client: OpenTargetsClient, condition: str, max_pages: int = 5) -> list[dict[str, Any]]:
    studies, token = [], None
    for _ in range(max_pages):
        params = {"query.cond": condition, "query.term": "antisense OR oligonucleotide OR siRNA",
                  "pageSize": 100, "format": "json"}
        if token:
            params["pageToken"] = token
        payload = client.get_json("https://clinicaltrials.gov/api/v2/studies", params)
        studies.extend(payload.get("studies") or [])
        token = payload.get("nextPageToken")
        if not token:
            break
    return [_parse_trial(x) for x in studies]


def _match_trials_to_genes(trials: list[dict[str, Any]], symbols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    symbols = list(dict.fromkeys(str(x) for x in symbols if len(str(x)) >= 3 and re.match(r"^[A-Za-z0-9]+$", str(x))))
    matches, trial_records = [], []
    ordered = sorted(trials, key=lambda x: (-(x["phase_max"] if pd.notna(x["phase_max"]) else -1), x["nct"]))
    for trial in ordered:
        strong_tokens = set(re.split(r"[^A-Za-z0-9]+", trial["text"]))
        weak_tokens = set(re.split(r"[^A-Za-z0-9]+", trial["summary"]))
        strong = [s for s in symbols if s in strong_tokens or s.upper() in strong_tokens]
        weak = [s for s in symbols if (s in weak_tokens or s.upper() in weak_tokens) and s not in strong]
        trial_records.append({k: trial[k] for k in ("nct", "phase", "status", "is_drug", "interventions", "title")})
        if trial["is_drug"]:
            for symbol in strong + weak:
                matches.append({"gene_symbol": symbol, "weak": symbol in weak, **trial})
    gene_records = []
    for symbol in symbols:
        hits = [x for x in matches if x["gene_symbol"] == symbol]
        if hits:
            best = hits[0]
            gene_records.append({"gene_symbol": symbol, "aso_trial_n": len(hits),
                                 "aso_trial_weak": sum(x["weak"] for x in hits),
                                 "aso_trial_best": f"{best['phase']} {best['status']}",
                                 "aso_trial_ids": ", ".join(x["nct"] for x in hits[:3])})
    return pd.DataFrame(gene_records), pd.DataFrame(trial_records)


def _fetch_constraints(client: OpenTargetsClient, ids: list[str]) -> list[dict[str, Any]]:
    query = """query Constraints($ids: [String!]!) { targets(ensemblIds: $ids) {
      id geneticConstraint { constraintType oeUpper }
    } }"""
    rows = []
    for target in client.query(query, {"ids": ids}).get("targets") or []:
        lof = [x.get("oeUpper") for x in target.get("geneticConstraint") or [] if x.get("constraintType") == "lof"]
        rows.append({"ensembl_id": target.get("id"), "loeuf": float(lof[0]) if lof and lof[0] is not None else math.nan})
    found = {x["ensembl_id"] for x in rows}
    rows.extend({"ensembl_id": x, "loeuf": math.nan} for x in ids if x not in found)
    return rows


def _fetch_association_page(client: OpenTargetsClient, disease_id: str, index: int, size: int) -> dict[str, Any]:
    query = """query Associations($id: String!, $index: Int!, $size: Int!) {
      disease(efoId: $id) { id name associatedTargets(page: {index: $index, size: $size}) {
        count rows { target { id approvedSymbol approvedName } score datatypeScores { id score } }
      } }
    }"""
    disease = client.query(query, {"id": disease_id, "index": index, "size": size}).get("disease")
    if not disease:
        raise ValueError(f"Open Targets returned no disease for ID {disease_id!r}")
    return disease


def _safe_merge(left: pd.DataFrame, right: pd.DataFrame, on: str) -> pd.DataFrame:
    return left.merge(right, on=on, how="left") if not right.empty else left


def _confidence_call(row: pd.Series) -> tuple[str, str]:
    """Educational confidence tier; not a calibrated probability."""
    if pd.notna(row.get("strategy")):
        return ("Manual override—verify",
                "A user-supplied manual override determined the mechanism; verify its primary sources.")
    truncated = row.get("evidence_truncated")
    if pd.notna(truncated) and bool(truncated):
        return ("Capped evidence—manual review",
                "The EVA response exceeded 500 rows, so the observed consequence fractions may be incomplete.")
    n = row.get("n_classified")
    frac = row.get("frac_lof")
    final = row.get("final_call")
    if "disagree" in str(row.get("flag", "")).lower():
        return ("Conflicting evidence", "Gene2Phenotype and ClinVar imply different mechanism tracks.")
    if pd.notna(row.get("g2p_call")) and row.get("clinvar_call") == row.get("g2p_call"):
        return ("Convergent G2P + ClinVar", "Independent Gene2Phenotype and ClinVar classifications agree.")
    if pd.notna(row.get("g2p_call")):
        return ("Gene2Phenotype evidence", "The mechanism comes from Gene2Phenotype; review its panel and allelic requirement.")
    if final == "modifier":
        return ("Association only", "Association evidence exists, but direction and causal mechanism are unknown.")
    if pd.isna(n) or n < 5:
        return ("Insufficient evidence", "Fewer than five classified pathogenic records were available.")
    if final == "ambiguous":
        return ("Conflicting evidence", "The LoF fraction lies between the automated mechanism thresholds.")
    distance = min(abs(float(frac) - 0.25), abs(float(frac) - 0.60)) if pd.notna(frac) else 0
    if n >= 20 and distance >= 0.15:
        return ("Strong heuristic evidence",
                "At least 20 classified records and the LoF fraction is well beyond a decision threshold.")
    if n >= 10 and distance >= 0.05:
        return ("Moderate heuristic evidence",
                "At least 10 classified records and the LoF fraction clears a decision threshold.")
    return ("Limited heuristic evidence",
            "The automated call clears a threshold but has limited count or threshold separation.")


@dataclass
class ASOResult:
    disease: str
    disease_id: str
    tables: dict[str, pd.DataFrame]
    output_dir: Path | None
    metadata: dict[str, Any]


def run_aso(
    disease_id: str,
    min_score: float = 0.20,
    min_genetic: float = 0.10,
    loeuf_intolerant: float = 0.60,
    use_variants: bool = True,
    use_g2p: bool = True,
    check_drugs: bool = True,
    check_trials: bool = True,
    exclude_approved: bool = False,
    exclude_aso_precedent: bool = False,
    include_modifiers: bool = True,
    save_csv: bool = True,
    output_dir: str | Path | None = None,
    curated: pd.DataFrame | None = None,
    *,
    max_genes_for_variants: int = 300,
    max_genes_for_drugs: int = 300,
    page_size: int = 100,
    request_delay: float = 0.2,
    run_mode: str = "full",
    cache_dir: str | Path | None = None,
    refresh_cache: bool = False,
    cache_ttl_hours: float = 24.0,
    progress: Callable[[str], None] = print,
    client: OpenTargetsClient | None = None,
) -> ASOResult:
    """Run the ASO target finder and return all result tables.

    The two max_genes_* parameters expose fixed R constants for controlled
    smoke tests. Keep both at 300 for behavior matching the original program.
    """
    if not isinstance(disease_id, str) or not disease_id.strip():
        raise ValueError("disease_id must be a non-empty string")
    disease_id = disease_id.strip().replace(":", "_")
    if run_mode not in {"quick", "full"}:
        raise ValueError("run_mode must be 'quick' or 'full'")
    output_path = Path(output_dir) if output_dir is not None else Path.cwd() / disease_id
    if run_mode == "quick":
        max_genes_for_variants = min(max_genes_for_variants, 25)
        max_genes_for_drugs = min(max_genes_for_drugs, 25)
        progress("QUICK MODE: variant/drug enrichment is capped at 25 genes and is incomplete.")
    resolved_cache = Path(cache_dir) if cache_dir is not None else Path.cwd() / ".aso_cache"
    client = client or OpenTargetsClient(cache_dir=resolved_cache, refresh_cache=refresh_cache,
                                         cache_ttl_hours=cache_ttl_hours)
    t0 = time.time()

    if curated is None:
        curated = pd.DataFrame(columns=["gene_symbol", "strategy", "precedent"])
    else:
        curated = curated.copy()
        for column in ("strategy", "precedent"):
            if column not in curated:
                curated[column] = pd.NA
        curated = curated[["gene_symbol", "strategy", "precedent"]]

    progress(f"[1/6] Fetching gene associations for {disease_id} ...")
    first = _fetch_association_page(client, disease_id, 0, page_size)
    assoc = first["associatedTargets"]
    total = int(assoc.get("count") or 0)
    if total == 0:
        raise ValueError(f"0 associated targets found for {disease_id}")
    raw_rows = list(assoc.get("rows") or [])
    for index in range(1, math.ceil(total / page_size)):
        raw_rows.extend(_fetch_association_page(client, disease_id, index, page_size)["associatedTargets"].get("rows") or [])
        time.sleep(request_delay)
    records = []
    for row in raw_rows:
        target = row.get("target") or {}
        records.append({"gene_symbol": target.get("approvedSymbol"), "gene_name": target.get("approvedName"),
                        "ensembl_id": target.get("id"), "overall_score": float(row.get("score") or 0),
                        "genetic_score": _datatype_score(row.get("datatypeScores"), "genetic_association")})
    master = pd.DataFrame(records)
    master = master[(master.overall_score >= min_score) & (master.genetic_score >= min_genetic)].sort_values("overall_score", ascending=False).reset_index(drop=True)
    if master.empty:
        raise ValueError("No genes passed the score thresholds; lower min_score/min_genetic")
    progress(f"      {total} genes linked; {len(master)} pass the score filters")
    try:
        version = client.query("{ meta { dataVersion { year month iteration } } }")["meta"]["dataVersion"]
        ot_version = ".".join(str(version[x]) for x in ("year", "month", "iteration") if version.get(x) is not None)
    except Exception as exc:
        warnings.warn(f"Could not retrieve Open Targets version: {exc}")
        ot_version = "unknown"

    progress("[2/6] Fetching gene constraint (LOEUF) ...")
    constraint_rows = []
    for batch in _chunks(master.ensembl_id.tolist(), 50):
        try:
            constraint_rows.extend(_fetch_constraints(client, batch))
        except Exception as exc:
            warnings.warn(f"Constraint lookup failed for a batch: {exc}")
            constraint_rows.extend({"ensembl_id": x, "loeuf": math.nan} for x in batch)
        time.sleep(request_delay)
    constraints = pd.DataFrame(constraint_rows)

    variant_rows = []
    if use_variants:
        ids = master.ensembl_id.head(max_genes_for_variants).tolist()
        progress(f"[3/6] Classifying mechanism from ClinVar variants ({len(ids)} genes) ...")
        for i, ens_id in enumerate(ids, 1):
            try:
                variant_rows.append(_fetch_variant_counts(client, disease_id, ens_id))
            except Exception as exc:
                warnings.warn(f"Variant lookup failed for {ens_id}: {exc}")
            if i % 25 == 0:
                progress(f"      {i} / {len(ids)}")
            time.sleep(request_delay)
    else:
        progress("[3/6] Skipping ClinVar variant classification")
    variants = pd.DataFrame(
        variant_rows,
        columns=["ensembl_id", "n_evidence", "n_evidence_returned", "evidence_truncated",
                 "n_lof", "n_splice", "n_splice_extra", "n_missense"],
    )
    truncated_count = int(variants["evidence_truncated"].fillna(False).sum()) if not variants.empty else 0
    if truncated_count:
        warnings.warn(
            f"{truncated_count} gene(s) exceeded the per-gene EVA evidence cap of 500. "
            "Consequence fractions use only returned rows; inspect evidence_truncated."
        )

    g2p_rows: list[dict[str, Any]] = []
    if use_g2p:
        progress("[4/6] Fetching Gene2Phenotype mechanism and inheritance ...")
        for batch in _chunks(master.ensembl_id.head(max_genes_for_variants).tolist(), 25):
            try:
                g2p_rows.extend(_fetch_g2p_batch(client, disease_id, batch))
            except Exception as exc:
                warnings.warn(f"Gene2Phenotype lookup failed for a batch: {exc}")
            time.sleep(request_delay)
    else:
        progress("[4/6] Skipping Gene2Phenotype")
    g2p = pd.DataFrame(g2p_rows, columns=["ensembl_id", "g2p_mech", "inheritance"])

    drug_rows: list[dict[str, Any]] = []
    drug_source = "not checked"
    if check_drugs:
        progress("[5/6] Looking up approved / clinical / antisense drugs ...")
        try:
            setup = _discover_drug_query(client)
            drug_source = setup["label"]
            ids = master.ensembl_id.head(max_genes_for_drugs).tolist()
            for batch in _chunks(ids, 25):
                drug_rows.extend(_fetch_drugs_batch(client, batch, setup))
                time.sleep(request_delay)
        except Exception as exc:
            warnings.warn(f"Drug lookup failed: {exc}")
            drug_source = "lookup failed"
    else:
        progress("[5/6] Skipping drug lookup")
    drugs = pd.DataFrame(drug_rows)

    gene_trials = pd.DataFrame(columns=["gene_symbol", "aso_trial_n", "aso_trial_weak", "aso_trial_best", "aso_trial_ids"])
    trials_table = pd.DataFrame(columns=["nct", "phase", "status", "is_drug", "interventions", "title"])
    if check_trials:
        progress("[6/6] Searching ClinicalTrials.gov for ASO/oligonucleotide trials ...")
        try:
            trials = _fetch_aso_trials(client, first["name"])
            gene_trials, trials_table = _match_trials_to_genes(trials, master.gene_symbol.dropna().tolist())
        except Exception as exc:
            warnings.warn(f"ClinicalTrials.gov lookup failed: {exc}")
    else:
        progress("[6/6] Skipping ClinicalTrials.gov")

    progress("Building report ...")
    master = _safe_merge(master, constraints, "ensembl_id")
    master = _safe_merge(master, variants, "ensembl_id")
    master = _safe_merge(master, g2p, "ensembl_id")
    master = _safe_merge(master, drugs, "ensembl_id")
    master = _safe_merge(master, gene_trials, "gene_symbol")
    master = master.merge(curated, on="gene_symbol", how="left")
    if "drug_status" not in master: master["drug_status"] = pd.NA
    if "has_approved_drug" not in master: master["has_approved_drug"] = pd.NA
    master["drug_status"] = master["drug_status"].fillna("lookup failed" if drug_source == "lookup failed" else "not checked")
    master["lof_intolerant"] = master["loeuf"].notna() & (master["loeuf"] < loeuf_intolerant)
    master["lof_tolerance"] = "LoF-tolerant"
    master.loc[master["loeuf"].isna(), "lof_tolerance"] = "unknown"
    master.loc[master["lof_intolerant"], "lof_tolerance"] = "LoF-intolerant"
    for col in ("n_lof", "n_missense", "n_splice", "n_splice_extra"):
        if col not in master: master[col] = math.nan
    for col in ("g2p_mech", "inheritance", "aso_drug", "aso_names", "oligo_drug", "oligo_names",
                "aso_trial_n", "aso_trial_weak", "aso_trial_best", "aso_trial_ids"):
        if col not in master: master[col] = pd.NA
    master["n_classified"] = master["n_lof"] + master["n_missense"]
    master["frac_lof"] = master["n_lof"] / master["n_classified"].where(master["n_classified"] > 0)
    denom = master["n_lof"] + master["n_splice_extra"]
    master["frac_splice_related"] = (master["n_splice"] + master["n_splice_extra"]) / denom.where(denom > 0)
    master["no_variant_evidence"] = master["n_classified"].eq(0) & master["n_splice_extra"].eq(0)
    master["clinvar_call"] = "ambiguous"
    master.loc[master["n_classified"].isna() | (master["n_classified"] < 5), "clinvar_call"] = "insufficient data"
    master.loc[master["n_classified"].ge(5) & master["frac_lof"].ge(0.60), "clinvar_call"] = "splice/upregulation"
    master.loc[master["n_classified"].ge(5) & master["frac_lof"].le(0.25), "clinvar_call"] = "knockdown"
    master["g2p_call"] = pd.NA
    master.loc[master["g2p_mech"].eq("LoF"), "g2p_call"] = "splice/upregulation"
    master.loc[master["g2p_mech"].eq("GoF/DN"), "g2p_call"] = "knockdown"
    master.loc[master["g2p_mech"].eq("mixed"), "g2p_call"] = "ambiguous"
    master["final_call"] = master["clinvar_call"]
    master.loc[master["no_variant_evidence"], "final_call"] = "modifier"
    master.loc[master["g2p_call"].notna(), "final_call"] = master.loc[master["g2p_call"].notna(), "g2p_call"]
    master.loc[master["strategy"].eq("knockdown"), "final_call"] = "knockdown"
    master.loc[master["strategy"].eq("splice"), "final_call"] = "splice/upregulation"
    master["call_source"] = "ClinVar"
    master.loc[master["final_call"].eq("modifier"), "call_source"] = "assoc only"
    master.loc[master["g2p_call"].notna(), "call_source"] = "G2P"
    master.loc[master["strategy"].notna(), "call_source"] = "curated"
    master["splice_correctable"] = master["final_call"].eq("splice/upregulation") & master["frac_splice_related"].ge(0.30)

    def flag(row: pd.Series) -> str:
        if pd.isna(row.strategy) and pd.notna(row.g2p_call) and row.clinvar_call != "insufficient data" and row.clinvar_call != row.g2p_call: return "ClinVar and G2P disagree"
        inheritance = str(row.inheritance) if pd.notna(row.inheritance) else ""
        if row.final_call == "knockdown" and inheritance == "recessive": return "recessive (G2P): knockdown unlikely to help"
        if row.final_call == "knockdown" and row.lof_intolerant: return "LoF-intolerant: full knockdown risky"
        if row.final_call == "splice/upregulation" and inheritance == "recessive": return "recessive LoF (G2P); do not knock down"
        if row.final_call == "splice/upregulation" and inheritance == "dominant" and row.lof_intolerant: return "dominant LoF (G2P): haploinsufficiency"
        if row.final_call == "splice/upregulation" and inheritance == "dominant": return "dominant LoF (G2P)"
        if row.final_call == "splice/upregulation" and pd.isna(row.inheritance) and row.lof_tolerance == "LoF-tolerant": return "likely recessive LoF; do not knock down"
        if row.final_call == "splice/upregulation" and pd.isna(row.inheritance) and row.lof_intolerant: return "possible haploinsufficiency"
        if row.final_call == "modifier": return "association only; effect direction unknown"
        return ""
    def note(row: pd.Series) -> str:
        if row.final_call == "knockdown" and row.lof_intolerant: return "Caution: LoF-intolerant gene. Full knockdown may be toxic; consider partial or allele-specific."
        if row.final_call == "knockdown": return "Knockdown plausible if disease mechanism is toxic gain of function."
        if row.final_call == "splice/upregulation" and row.lof_tolerance == "LoF-tolerant": return "Likely recessive LoF. Do NOT knock down. Splice correction only if variants are splice-site."
        if row.final_call == "splice/upregulation" and row.lof_intolerant: return "Likely haploinsufficiency. Upregulation or splice correction."
        if row.final_call == "splice/upregulation": return "Likely LoF disease; no constraint data."
        if row.final_call == "ambiguous": return "Mixed variant types. Mechanism unclear; review manually."
        if row.final_call == "modifier": return "Genetic association without variant-level evidence. Mechanism and direction are unknown; review the locus."
        return "Too little ClinVar data. Classify manually (repeat expansions and non-coding mechanisms are invisible here)."
    master["flag"] = master.apply(flag, axis=1)
    master["note"] = master.apply(note, axis=1)
    def precedent(row: pd.Series) -> str:
        pieces = []
        if pd.notna(row.aso_drug) and row.aso_drug != "-":
            pieces.append(f"Drug: {str(row.aso_names) + ' ' if pd.notna(row.aso_names) and row.aso_names else ''}({row.aso_drug})")
        if pd.notna(row.aso_trial_n) and row.aso_trial_n > 0:
            weak = f"; {int(row.aso_trial_weak)} via summary text" if pd.notna(row.aso_trial_weak) and row.aso_trial_weak > 0 else ""
            pieces.append(f"Trials: {int(row.aso_trial_n)} (best {row.aso_trial_best}{weak})")
        if pd.notna(row.precedent) and str(row.precedent): pieces.append(f"Manual: {row.precedent}")
        return " | ".join(pieces)
    master["aso_precedent"] = master.apply(precedent, axis=1)
    master["has_aso_precedent"] = master["aso_precedent"].str.len().gt(0)
    confidence = master.apply(_confidence_call, axis=1)
    master["confidence_tier"] = [x[0] for x in confidence]
    master["confidence_reason"] = [x[1] for x in confidence]
    if exclude_approved:
        master = master[~master["has_approved_drug"].eq(True)].copy()

    tables = {
        "all": master,
        "knockdown": master[master.final_call.eq("knockdown")].copy(),
        "splice": master[master.final_call.eq("splice/upregulation")].copy(),
        "ambiguous": master[master.final_call.eq("ambiguous")].copy(),
        "modifier": master[master.final_call.eq("modifier")].copy(),
        "insufficient": master[master.final_call.eq("insufficient data")].copy(),
        "controls": master[master.has_aso_precedent].copy(),
        "trials": trials_table,
    }
    calls = ["knockdown", "splice/upregulation"] + (["modifier"] if include_modifiers else [])
    shortlist = master[master.final_call.isin(calls)].copy()
    if drug_source not in ("not checked", "lookup failed"):
        shortlist = shortlist[~shortlist.has_approved_drug.eq(True)]
    if exclude_aso_precedent:
        shortlist = shortlist[~shortlist.has_aso_precedent]
    shortlist["_tier"] = shortlist.final_call.eq("modifier").astype(int)
    tables["shortlist"] = shortlist.sort_values(["_tier", "genetic_score", "overall_score"], ascending=[True, False, False]).drop(columns="_tier")

    csv_names = {"all": "all_candidates_annotated.csv", "knockdown": "knockdown_candidates.csv",
                 "splice": "splice_upregulation_candidates.csv", "ambiguous": "ambiguous_candidates.csv",
                 "modifier": "modifier_candidates.csv", "insufficient": "insufficient_data.csv", "controls": "positive_controls.csv",
                 "shortlist": "priority_shortlist.csv"}
    track_summary = pd.DataFrame(
        {"track": ["knockdown", "splice/upregulation", "ambiguous", "modifier", "insufficient data"],
         "genes": [len(tables["knockdown"]), len(tables["splice"]),
                   len(tables["ambiguous"]), len(tables["modifier"]), len(tables["insufficient"])]}
    )
    metadata = {
        "implementation": "aso_target_finder_python_enhanced",
        "implementation_version": "4.1-guided",
        "run_date": date.today().isoformat(),
        "open_targets_release": ot_version,
        "endpoint": client.endpoint,
        "drug_source": drug_source,
        "trial_source": "ClinicalTrials.gov API v2" if check_trials else "not checked",
        "linked_genes": total,
        "passing_genes": len(master),
        "evidence_cap_per_gene": 500,
        "evidence_truncated_genes": int(master.get("evidence_truncated", pd.Series(dtype=bool)).fillna(False).sum()),
        "track_counts": {row.track: int(row.genes) for row in track_summary.itertuples(index=False)},
        "elapsed_minutes": round((time.time() - t0) / 60, 2),
        "parameters": {
            "min_score": min_score, "min_genetic": min_genetic,
            "loeuf_intolerant": loeuf_intolerant, "use_variants": use_variants, "use_g2p": use_g2p,
            "check_drugs": check_drugs, "check_trials": check_trials, "exclude_approved": exclude_approved,
            "exclude_aso_precedent": exclude_aso_precedent, "include_modifiers": include_modifiers,
            "max_genes_for_variants": max_genes_for_variants,
            "max_genes_for_drugs": max_genes_for_drugs, "page_size": page_size,
            "request_delay": request_delay, "min_variants": 5,
            "lof_fraction_high": 0.60, "lof_fraction_low": 0.25,
            "splice_site_fraction": 0.30, "enable_indirect_evidence": True,
            "run_mode": run_mode, "cache_ttl_hours": cache_ttl_hours,
        },
        "cache": {"directory": str(resolved_cache), "refresh_requested": refresh_cache,
                  "hits": int(getattr(client, "cache_hits", 0)),
                  "misses": int(getattr(client, "cache_misses", 0))},
        "runtime": {
            "python": platform.python_version(),
            "pandas": package_version("pandas"),
            "requests": package_version("requests"),
        },
        "caveats": [
            "Hypothesis generation only; not a clinical decision tool.",
            "Any user-supplied manual overrides require primary-source verification.",
            "Gene2Phenotype calls depend on its current panels and allelic-requirement annotations.",
            "Missense-heavy evidence does not establish gain of function.",
            "Drug approval is target-centric and may be for another indication.",
            "ClinicalTrials.gov matching is text-based; summary-text-only gene matches are weak evidence.",
            "enableIndirect=true includes ontology-related disease evidence.",
            "Genes exceeding the EVA evidence cap use a truncated consequence sample.",
        ],
    }
    result = ASOResult(first["name"], disease_id, tables, output_path if save_csv else None, metadata)
    if save_csv:
        output_path.mkdir(parents=True, exist_ok=True)
        for key, filename in csv_names.items():
            tables[key].to_csv(output_path / filename, index=False)
        if not trials_table.empty:
            trials_table.to_csv(output_path / "aso_trials_for_condition.csv", index=False)
        track_summary.to_csv(output_path / "run_summary.csv", index=False)
        (output_path / "run_metadata.json").write_text(json.dumps(metadata, indent=2))
        write_concise_report(result)
    progress(f"Finished in {metadata['elapsed_minutes']} min")
    return result


def result_summary(result: ASOResult) -> pd.DataFrame:
    """Return the compact mechanism-track count table."""
    return pd.DataFrame(
        [{"track": track, "genes": int(count)}
         for track, count in result.metadata["track_counts"].items()]
    )


def gene_evidence_view(result: ASOResult, gene_symbol: str) -> pd.DataFrame:
    """Return an auditable, one-row gene evidence card for notebook display."""
    matches = result.tables["all"][result.tables["all"]["gene_symbol"].str.upper() == gene_symbol.upper()]
    if matches.empty:
        raise KeyError(f"{gene_symbol!r} is not present in this run")
    columns = [x for x in (
        "gene_symbol", "gene_name", "ensembl_id", "final_call", "confidence_tier",
        "confidence_reason", "call_source", "overall_score", "genetic_score", "loeuf",
        "lof_tolerance", "n_evidence", "n_evidence_returned", "evidence_truncated",
        "n_lof", "n_splice", "n_splice_extra", "n_missense", "frac_lof", "frac_splice_related",
        "g2p_mech", "inheritance", "clinvar_call", "drug_status", "oligo_drug", "aso_drug",
        "aso_precedent", "aso_trial_n", "aso_trial_weak", "aso_trial_ids", "precedent", "flag", "note",
    ) if x in matches]
    return matches[columns].head(1).T.rename(columns={matches.index[0]: "value"})


def write_concise_report(result: ASOResult, file: str | Path | None = None, top_n: int = 15) -> Path:
    """Write a standalone HTML summary independent of notebook console output."""
    if result.output_dir is None and file is None:
        raise ValueError("Provide file when result.output_dir is unavailable")
    path = Path(file) if file is not None else result.output_dir / "concise_report.html"
    shortlist = result.tables["shortlist"].head(top_n).copy()
    wanted = [x for x in ("gene_symbol", "final_call", "confidence_tier", "call_source", "overall_score",
                           "genetic_score", "g2p_mech", "inheritance", "loeuf", "n_lof", "n_missense",
                           "evidence_truncated", "drug_status", "aso_precedent", "flag") if x in shortlist]
    caveats = "".join(f"<li>{html.escape(str(x))}</li>" for x in result.metadata["caveats"])
    summary_html = result_summary(result).to_html(index=False, border=0, escape=True)
    shortlist_html = shortlist[wanted].to_html(index=False, border=0, escape=True, table_id="shortlist") if wanted else "<p>None</p>"
    details_cols = [x for x in ("gene_symbol", "confidence_reason", "note") if x in shortlist]
    details_html = shortlist[details_cols].to_html(index=False, border=0, escape=True) if details_cols else "<p>None</p>"
    body = f"""<!doctype html><html><head><meta charset="utf-8"><title>ASO Target Finder report</title>
<style>body{{font:15px system-ui;max-width:1180px;margin:32px auto;padding:0 18px;color:#18202a}}table{{border-collapse:collapse;width:100%;margin:12px 0 28px}}th,td{{border:1px solid #ccd3da;padding:7px;text-align:left;vertical-align:top}}th{{background:#eef3f7;position:sticky;top:0}}code{{background:#f3f5f7;padding:2px 4px}}.warn{{background:#fff4d6;padding:14px;border-left:5px solid #e6a700}}input{{padding:8px;width:min(420px,90%);margin:8px 0}}</style></head><body>
<h1>ASO Target Finder: {html.escape(result.disease)}</h1>
<p><b>Disease ID:</b> <code>{html.escape(result.disease_id)}</code><br>
<b>Run date:</b> {html.escape(result.metadata['run_date'])}<br>
<b>Open Targets release:</b> {html.escape(str(result.metadata['open_targets_release']))}<br>
<b>Passing genes:</b> {result.metadata['passing_genes']}</p>
<div class="warn"><b>Research-use warning:</b> hypothesis generation only. Review every candidate, G2P/ClinVar disagreement, weak trial match, and manual override.</div>
<h2>Track summary</h2>{summary_html}
<h2>Priority shortlist (top {top_n})</h2><p><input id="filter" placeholder="Filter genes, tracks, confidence or drug status"></p>{shortlist_html}
<h2>Why each confidence tier was assigned</h2>{details_html}
<h2>How to interpret this report</h2>
<dl><dt><b>LoF</b></dt><dd>Loss of function; it does not automatically imply that upregulation is feasible.</dd>
<dt><b>GoF hypothesis</b></dt><dd>A missense-heavy pattern can motivate review for toxic gain of function, but does not prove it.</dd>
<dt><b>G2P</b></dt><dd>Gene2Phenotype mechanism and inheritance annotations take precedence over the ClinVar count heuristic.</dd>
<dt><b>Modifier</b></dt><dd>Association evidence without enough directional variant evidence; do not infer knockdown or upregulation.</dd>
<dt><b>ASO precedent</b></dt><dd>Combines Open Targets drug records with text-matched interventional ClinicalTrials.gov studies; summary-only matches are weak.</dd>
<dt><b>LOEUF</b></dt><dd>Constraint metric used here as a safety flag, not as the mechanism classifier.</dd>
<dt><b>Indirect evidence</b></dt><dd>The queries include ontology-related diseases, improving recall while reducing specificity.</dd>
<dt><b>Confidence tier</b></dt><dd>A transparent heuristic for triage, not a calibrated probability.</dd></dl>
<h2>Important caveats</h2><ul>{caveats}</ul>
<script>document.getElementById('filter').addEventListener('input',function(){{let q=this.value.toLowerCase();document.querySelectorAll('#shortlist tbody tr').forEach(r=>r.style.display=r.innerText.toLowerCase().includes(q)?'':'none')}})</script>
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


def validate_result(result: ASOResult) -> dict[str, Any]:
    """Return machine-readable invariants; raises AssertionError on failure."""
    t = result.tables
    track_total = sum(len(t[k]) for k in ("knockdown", "splice", "ambiguous", "modifier", "insufficient"))
    assert track_total == len(t["all"]), "Track counts do not sum to all candidates"
    assert t["all"]["ensembl_id"].notna().all(), "Missing Ensembl IDs"
    assert t["all"]["ensembl_id"].is_unique, "Duplicate Ensembl IDs"
    assert t["all"]["overall_score"].between(0, 1).all(), "Invalid overall scores"
    assert t["all"]["genetic_score"].between(0, 1).all(), "Invalid genetic scores"
    if "evidence_truncated" in t["all"]:
        flagged = t["all"]["evidence_truncated"].fillna(False)
        assert (t["all"].loc[flagged, "n_evidence"] > t["all"].loc[flagged, "n_evidence_returned"]).all(), "Incoherent truncation flags"
    assert result.metadata.get("open_targets_release"), "Missing Open Targets release metadata"
    assert result.metadata.get("parameters"), "Missing parameter metadata"
    assert t["all"]["confidence_tier"].notna().all(), "Missing confidence tiers"
    assert "cache" in result.metadata, "Missing cache metadata"
    return {"status": "PASS", "candidates": len(t["all"]), "tracks_total": track_total,
            "unique_ensembl_ids": int(t["all"]["ensembl_id"].nunique()),
            "evidence_truncated_genes": int(result.metadata.get("evidence_truncated_genes", 0)),
            "metadata_present": True}
