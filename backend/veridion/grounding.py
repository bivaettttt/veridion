import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from itertools import combinations
from typing import Any

NUMBER = r"(\d+(?:[ \u00a0\u202f]\d{3})*(?:[.,]\d+)?)"
CAPACITY = re.compile(
    r"(\d{1,3}(?:[ ,.\u00a0\u202f]\d{3})+|\d+)"
    + r"\s*(?:concurrent users|simultaneous users|одновременн\w* пользовател\w*|пользовател\w*)",
    re.I,
)
CAPACITY_TOPIC = re.compile(
    r"capacity|concurren|simultan|load|нагруз|пользоват|одноврем|пропускн", re.I
)
AVAILABILITY = re.compile(NUMBER + r"\s*%")
AVAILABILITY_TOPIC = re.compile(r"availability|доступност", re.I)
INTERFACE_TOPIC = re.compile(
    r"interface|integrat|интеграц|интерфейс|\bREST\b|\bSOAP\b|webhook", re.I
)
CONTEXT = re.compile(
    r"(?:\b(?:build|release|сборка|релиз)\s+([0-9]+(?:\.[0-9]+)*))", re.I
)
YEAR = re.compile(r"\b(20\d{2}(?:-\d{2}-\d{2})?)\b")
QUALIFIER = re.compile(r"(?:profile|профил\w*)[ :]+([\w-]+)", re.I)


@dataclass(frozen=True)
class Fact:
    subject: str
    property: str
    value: str
    unit: str
    modality: str
    context: str
    polarity: str
    text: str
    chunk_id: str


def decimal(raw: str) -> str:
    value = re.sub(r"\s", "", raw).replace(",", ".")
    return format(Decimal(value).normalize(), "f")


def modality(value: str, category: str) -> str:
    if category in {"meeting", "advisory", "other"}:
        return "unconfirmed"
    if re.search(r"target|require[sdm]|planned|целев|требован|планиру", value, re.I):
        return "requirement"
    if category == "test" and re.search(
        r"test|observed|measured|провер|испытан|измер", value, re.I
    ):
        return "observation"
    if category in {"architecture", "specification"}:
        return "documented"
    return "unconfirmed"


def extract(row: dict[str, Any]) -> list[Fact]:
    facts = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", row["content"]):
        sentence = sentence.strip()
        if not sentence:
            continue
        period = YEAR.search(sentence)
        build = CONTEXT.search(sentence)
        qualifier = QUALIFIER.search(sentence)
        context = (
            " · ".join(match.group(1) for match in [build, period, qualifier] if match)
            or "unspecified"
        )
        kind = modality(sentence, row["category"])
        negated = re.search(r"\b(?:not|no|only|не|только)\b", sentence, re.I)
        # “Only” qualifies the observed boundary. It does not negate the reported measurement.
        polarity = (
            "negative"
            if negated and negated.group().casefold() not in {"only", "только"}
            else "positive"
        )
        common = (kind, context, polarity, sentence, str(row["chunk_id"]))
        for match in CAPACITY.finditer(sentence):
            facts.append(
                Fact(
                    "platform",
                    "concurrent capacity",
                    re.sub(r"[^0-9]", "", match[1]),
                    "users",
                    *common,
                )
            )
        if AVAILABILITY_TOPIC.search(sentence):
            for match in AVAILABILITY.finditer(sentence):
                facts.append(
                    Fact(
                        "platform",
                        "availability",
                        decimal(match[1]),
                        "percent",
                        *common,
                    )
                )
        if INTERFACE_TOPIC.search(sentence):
            for interface in sorted(
                {
                    m.upper()
                    for m in re.findall(
                        r"\b(?:REST|SOAP|webhook|AMQP)\b", sentence, re.I
                    )
                }
            ):
                facts.append(
                    Fact("platform", "interface", interface, "protocol", *common)
                )
    return facts


def comparisons(facts: list[Fact]):
    items = []
    for left, right in combinations(facts, 2):
        if (
            left.chunk_id == right.chunk_id
            or left.property != right.property
            or "unconfirmed" in {left.modality, right.modality}
        ):
            continue
        if left.property == "interface" and left.value != right.value:
            continue
        if left.value == right.value and left.polarity == right.polarity:
            continue
        if left.context != right.context:
            classification, reason = (
                "DIFFERENT_CONTEXT",
                "Different builds, periods or test profiles",
            )
        elif left.modality != right.modality:
            classification, reason = (
                "DIFFERENT_MODALITY",
                "Requirement and observation describe different evidence",
            )
        elif left.context == "unspecified":
            classification, reason = (
                "NEEDS_CONTEXT",
                "The sources omit comparable conditions",
            )
        else:
            classification, reason = (
                "POTENTIAL_CONFLICT",
                "Different values or polarity under matching conditions",
            )
        items.append(
            {
                "type": classification,
                "reason": reason,
                "left": asdict(left),
                "right": asdict(right),
            }
        )
    return items[:30]


def assess(question: str, hits: list[dict[str, Any]]):
    all_facts = [fact for hit in hits for fact in extract(hit)]
    if CAPACITY_TOPIC.search(question):
        property_name = "concurrent capacity"
    elif AVAILABILITY_TOPIC.search(question):
        property_name = "availability"
    elif INTERFACE_TOPIC.search(question):
        property_name = "interface"
    else:
        property_name = ""
    facts = [fact for fact in all_facts if fact.property == property_name]
    conflicts = comparisons(facts)
    capacity = CAPACITY.search(question)
    availability = (
        AVAILABILITY.search(question) if property_name == "availability" else None
    )
    protocol = re.search(r"\b(?:REST|SOAP|webhook|AMQP)\b", question, re.I)
    requested = None
    if capacity and property_name == "concurrent capacity":
        requested = re.sub(r"[^0-9]", "", capacity[1])
    elif availability:
        requested = decimal(availability[1])
    elif protocol and property_name == "interface":
        requested = protocol[0].upper()
    verified_facts = [
        fact
        for fact in facts
        if fact.modality == "observation"
        or (property_name == "interface" and fact.modality == "documented")
    ]
    question_context = CONTEXT.search(question)
    if question_context:
        verified_facts = [
            fact
            for fact in verified_facts
            if fact.context.split(" · ")[0] == question_context[1]
        ]
    support = [
        fact
        for fact in verified_facts
        if fact.polarity == "positive"
        and (requested is None or fact.value == requested)
    ]
    oppose = [
        fact
        for fact in verified_facts
        if fact.polarity == "negative" and fact.value == requested
    ]
    matching_conflict = any(item["type"] == "POTENTIAL_CONFLICT" for item in conflicts)
    if (support and oppose) or (matching_conflict and support):
        status = "MIXED_EVIDENCE"
        summary = "Comparable sources disagree. Review the evidence under the matching conditions."
    elif support:
        status = "SUPPORTED_BY_SOURCES"
        summary = "The retrieved evidence supports the claim within the conditions recorded below."
    elif oppose:
        status = "CONTRADICTED_BY_SOURCES"
        summary = "Retrieved evidence explicitly denies the requested claim under the recorded conditions."
    else:
        status = "INSUFFICIENT_EVIDENCE"
        summary = "The retrieved sources do not establish the requested claim."
    if property_name == "concurrent capacity" and requested and not support:
        observed = sorted(
            {fact.value for fact in verified_facts if fact.polarity == "positive"},
            key=Decimal,
        )
        target = any(
            fact.value == requested and fact.modality == "requirement" for fact in facts
        )
        if target and observed:
            summary = (
                f"{requested} concurrent users is a stated requirement. Retrieved tests report "
                f"{', '.join(observed)} concurrent users. The target remains unverified."
            )
    claim = {
        "text": question,
        "subject": "platform" if property_name else None,
        "property": property_name or None,
        "requested": requested,
        "status": status,
        "support": [asdict(fact) for fact in support],
        "opposition": [asdict(fact) for fact in oppose],
        "evidence": [asdict(fact) for fact in facts],
        "reason": summary,
    }
    return {
        "summary": summary,
        "assessment": status,
        "claims": [claim],
        "contradictions": conflicts,
        "citation_chunks": list(
            dict.fromkeys(
                fact.chunk_id for fact in facts if fact.modality != "unconfirmed"
            )
        ),
    }


GAP_LANGUAGE = re.compile(
    r"insufficient|unknown|unverified|not (?:yet )?(?:established|verified|tested|confirmed|demonstrated)"
    r"|evidence (?:does not|doesn't) establish|недостаточ|не подтвержд|не провер|не установлен",
    re.I,
)
UNSUPPORTED_INFERENCE = re.compile(
    r"\bmaximum\b|\bupper bound\b|\bat most\b|\blimited to\b|\b(?:does|did) not (?:meet|support)"
    r"|максимум|не поддержива|предел нагрузки",
    re.I,
)


def preserves_evidence_gap(summary: str) -> bool:
    return bool(GAP_LANGUAGE.search(summary)) and not UNSUPPORTED_INFERENCE.search(
        summary
    )
