from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import httpx


class UpstreamError(RuntimeError):
    pass


class OpenTargetsClient:
    def __init__(
        self,
        endpoint: str,
        timeout: float = 60,
        retries: int = 4,
        session: httpx.Client | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self.retries = retries
        self.session = session or httpx.Client(headers={"User-Agent": "aso-compass-api/0.1"})

    def query(self, query: str, variables: dict[str, Any] | None = None) -> tuple[dict[str, Any], str]:
        variables = variables or {}
        query_hash = hashlib.sha256(
            json.dumps(
                {"endpoint": self.endpoint, "query": query, "variables": variables}, sort_keys=True
            ).encode()
        ).hexdigest()
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.post(
                    self.endpoint,
                    json={"query": query, "variables": variables},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("errors"):
                    raise UpstreamError(
                        " | ".join(str(item.get("message", item)) for item in payload["errors"])
                    )
                return payload.get("data") or {}, query_hash
            except (httpx.HTTPError, ValueError, UpstreamError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.8 * 2**attempt)
        raise UpstreamError(f"Open Targets request failed after retries: {last_error}")

    def get_json(self, url: str, params: dict[str, Any]) -> tuple[dict[str, Any], str]:
        query_hash = hashlib.sha256(
            json.dumps({"url": url, "params": params}, sort_keys=True).encode()
        ).hexdigest()
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json(), query_hash
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.8 * 2**attempt)
        raise UpstreamError(f"JSON request failed after retries: {last_error}")

    @staticmethod
    def _unwrap_type(type_node: dict[str, Any] | None) -> str | None:
        while type_node and not type_node.get("name") and type_node.get("ofType"):
            type_node = type_node["ofType"]
        return type_node.get("name") if type_node else None

    def type_fields(self, type_name: str) -> dict[str, str | None]:
        query = """query TypeFields($name:String!){__type(name:$name){fields{name type{
        kind name ofType{kind name ofType{kind name ofType{kind name}}}}}}}"""
        data, _ = self.query(query, {"name": type_name})
        node = data.get("__type") or {}
        return {field["name"]: self._unwrap_type(field.get("type")) for field in node.get("fields") or []}


ASSOCIATIONS = """query Associations($id:String!,$index:Int!,$size:Int!){
 disease(efoId:$id){id name associatedTargets(page:{index:$index,size:$size}){
 count rows{target{id approvedSymbol approvedName} score datatypeScores{id score}}}}}"""

CONSTRAINTS = """query Constraints($ids:[String!]!){targets(ensemblIds:$ids){
 id geneticConstraint{constraintType oeUpper}}}"""

VARIANTS = """query Evidence($disease:String!,$genes:[String!]!,$size:Int!){
 disease(efoId:$disease){evidences(ensemblIds:$genes,enableIndirect:true,
 datasourceIds:[\"eva\"],size:$size){count rows{variantFunctionalConsequence{id label} clinicalSignificances}}}}"""

G2P = """query G2P($disease:String!,$genes:[String!]!){disease(efoId:$disease){
 evidences(ensemblIds:$genes,enableIndirect:true,datasourceIds:[\"gene2phenotype\"],size:500){
 rows{target{id} variantFunctionalConsequence{id label} allelicRequirements}}}}"""

G2P_BASIC = """query G2P($disease:String!,$genes:[String!]!){disease(efoId:$disease){
 evidences(ensemblIds:$genes,enableIndirect:true,datasourceIds:[\"gene2phenotype\"],size:500){
 rows{target{id} variantFunctionalConsequence{id label}}}}}"""
