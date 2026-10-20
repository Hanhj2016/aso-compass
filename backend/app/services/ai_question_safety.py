from __future__ import annotations

import re
import unicodedata
from typing import Literal

from pydantic import BaseModel

MAX_AI_QUESTION_LENGTH = 500
QuestionSafetyCode = Literal[
    "SAFE",
    "EMPTY_QUESTION",
    "QUESTION_TOO_LONG",
    "PATIENT_IDENTIFIABLE",
    "PATIENT_SPECIFIC",
    "CLINICAL_ADVICE",
    "RANKING_OVERRIDE",
    "PROMPT_INJECTION",
]


class QuestionSafetyAssessment(BaseModel):
    allowed: bool
    code: QuestionSafetyCode
    public_message: str


_PATIENT_IDENTIFIABLE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        r"(?<!\d)(?:\+?1[ .-]?)?(?:\(?\d{3}\)?[ .-]?)\d{3}[ .-]?\d{4}(?!\d)",
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b(?:mrn|medical record(?: number)?|patient id)\s*[:#-]?\s*[a-z0-9-]{4,}\b",
        r"\b(?:dob|date of birth)\s*(?:is|:)?\s*\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b",
        r"\bpatient(?:'s)? name\s*(?:is|:)?\s+[a-z][a-z' -]{2,}\b",
        r"\b\d{1,5}\s+[a-z0-9.' -]+\s(?:street|st|road|rd|avenue|ave|drive|dr|lane|ln)\b",
    )
)

_PROMPT_INJECTION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bignore (?:all |any )?(?:previous|prior|above) (?:instructions|rules|prompts)\b",
        r"\b(?:reveal|show|print|repeat) (?:the )?(?:system prompt|developer message|hidden instructions)\b",
        r"\b(?:reveal|show|print|return) (?:the )?(?:api key|openai_api_key|database_url|database password|secret key)\b",
        r"\b(?:bypass|disable|ignore) (?:the )?(?:safety|safeguards|policy|restrictions)\b",
        r"\bpretend (?:that )?you are\b",
        r"\b(?:execute|run) (?:this )?(?:sql|database query)\b",
        r"\b(?:drop|delete|truncate)\s+(?:table|database)\b",
    )
)

_CLINICAL_ADVICE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:dose|dosage|dosing)\b",
        r"\b(?:prescribe|prescription)\b",
        r"\b(?:which|what) (?:drug|medicine|medication|treatment|therapy) should\b",
        r"\bshould (?:i|we|the patient|my child) (?:take|start|stop|use|receive|switch)\b",
        r"\b(?:diagnose|diagnosis|prognosis|treatment plan)\b",
        r"\bis (?:this|it) safe for (?:me|my child|the patient)\b",
    )
)

_PATIENT_SPECIFIC_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:my child|my mother|my father|my spouse|our patient|this patient|the patient)\b",
        r"\b(?:i|i'm|i am|my|me)\b.{0,90}\b(?:diagnosed|diagnosis|symptoms?|mutation|variant|disease|condition|medication|treatment|genetic test|gene test)\b",
        r"\b(?:diagnosed|diagnosis|symptoms?|mutation|variant|disease|condition|medication|treatment)\b.{0,90}\b(?:i|me|my|mine)\b",
    )
)

_RANKING_OVERRIDE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bbest (?:aso )?target\b",
        r"\b(?:rank|place|move)\s+[a-z0-9-]+\s+(?:as |at )?(?:number )?(?:one|1|first)\b",
        r"\b(?:rerank|re-rank)\b",
        r"\boverride\b.{0,50}\b(?:classification|final[_ ]?call|rank|shortlist)\b",
        r"\bchange\b.{0,50}\b(?:classification|final[_ ]?call|rank|shortlist)\b",
        r"\bshortlist\b.{0,50}\b(?:regardless|even if|despite)\b",
    )
)


def _matches_any(question: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(question) is not None for pattern in patterns)


def assess_ai_question(question: str) -> QuestionSafetyAssessment:
    """Classify a question before persistence, evidence retrieval, or an OpenAI request."""

    normalized = unicodedata.normalize("NFKC", question).strip()
    if not normalized:
        return QuestionSafetyAssessment(
            allowed=False,
            code="EMPTY_QUESTION",
            public_message="Enter a question about the saved research evidence.",
        )
    if len(normalized) > MAX_AI_QUESTION_LENGTH:
        return QuestionSafetyAssessment(
            allowed=False,
            code="QUESTION_TOO_LONG",
            public_message=f"Questions must be {MAX_AI_QUESTION_LENGTH} characters or fewer.",
        )
    if _matches_any(normalized, _PATIENT_IDENTIFIABLE_PATTERNS):
        return QuestionSafetyAssessment(
            allowed=False,
            code="PATIENT_IDENTIFIABLE",
            public_message="Do not enter names, contact details, record numbers, or other patient identifiers.",
        )
    if _matches_any(normalized, _PROMPT_INJECTION_PATTERNS):
        return QuestionSafetyAssessment(
            allowed=False,
            code="PROMPT_INJECTION",
            public_message="The question must ask only about the saved research evidence.",
        )
    if _matches_any(normalized, _CLINICAL_ADVICE_PATTERNS):
        return QuestionSafetyAssessment(
            allowed=False,
            code="CLINICAL_ADVICE",
            public_message="Clinical, treatment, and dosing advice is outside this research tool.",
        )
    if _matches_any(normalized, _PATIENT_SPECIFIC_PATTERNS):
        return QuestionSafetyAssessment(
            allowed=False,
            code="PATIENT_SPECIFIC",
            public_message="Ask about the saved public evidence, not an individual patient or diagnosis.",
        )
    if _matches_any(normalized, _RANKING_OVERRIDE_PATTERNS):
        return QuestionSafetyAssessment(
            allowed=False,
            code="RANKING_OVERRIDE",
            public_message="AI cannot select targets or change deterministic classifications and rankings.",
        )
    return QuestionSafetyAssessment(
        allowed=True,
        code="SAFE",
        public_message="Question may proceed to saved-evidence support checks.",
    )
