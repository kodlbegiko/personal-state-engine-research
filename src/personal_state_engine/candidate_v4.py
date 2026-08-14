from __future__ import annotations

import re
from typing import Any

from .candidate_v2 import pse_candidate_v2_rank
from .zero_cost_baselines import _stem, parse_timestamp, tokens

VERDICT_SUPPORTED = "SUPPORTED"
VERDICT_CONTRADICTED = "CONTRADICTED"
VERDICT_INSUFFICIENT = "INSUFFICIENT"

QUESTION_WORDS = {"what", "when", "where", "which", "who", "whose", "how", "does", "do", "did", "is", "are"}
GENERIC_STEMS = {
    _stem(x) for x in {
        "a","an","the","is","are","was","were","be","been","being","what","when","where","which","who","whose","how",
        "does","do","did","to","of","in","on","at","for","from","with","and","or","under","this","that","it","as",
        "user","users","current","latest","now","still","should","used","use","using","please","tell","me",
    }
}
DISCOURSE_STEMS = {_stem(x) for x in {"answer","query","question","keyword","keywords","prompt","instruction","stuffing","decoy","fake","fabricated"}}
UNCERTAIN_STEMS = {_stem(x) for x in {"might","maybe","possibly","possible","tentative","tentatively","could","may","perhaps","estimate","estimated","draft","proposed"}}
CERTAINTY_STEMS = {_stem(x) for x in {"confirmed","confirm","final","definite","official","officially","approved","確定","確認","最終","正式"}}
UPDATE_STEMS = {_stem(x) for x in {"updated","update","replace","replaced","changed","change","stopped","correction","corrected","moved","rescheduled","revoked","now","current","latest","deprecated","rejected"}}

# Generic field-level concepts. Composite fields precede generic fallbacks so
# "phone number" is not treated as evidence for "serial number", etc.
ATTRIBUTE_PATTERNS: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = (
    ("blood_type", (("blood","type"), ("血型",))),
    ("passport_number", (("passport","number"), ("護照","號碼"), ("护照","号码"))),
    ("national_id_number", (("national","id"), ("id","number"), ("身分證","號碼"), ("身份证","号码"))),
    ("registration_number", (("registration","number"), ("registration","plate"), ("車牌",), ("登記","號碼"))),
    ("license_number", (("license","number"), ("licence","number"), ("駕照","號碼"), ("驾照","号码"))),
    ("serial_number", (("serial","number"), ("serial",), ("序號",), ("編號",))),
    ("phone", (("phone","number"), ("phone",), ("telephone",), ("mobile",), ("電話",), ("手機",))),
    ("email", (("email","address"), ("email",), ("e-mail",), ("電子郵件",), ("信箱",))),
    ("wifi_password", (("wifi","password"), ("wi-fi","password"), ("wireless","password"))),
    ("pin", (("pin",), ("passcode",), ("password",), ("密碼",))),
    ("cost_center", (("cost","center"), ("cost","centre"))),
    ("keyboard_layout", (("keyboard","layout"),)),
    ("issuing_authority", (("issuing","authority"), ("issuer",))),
    ("supplier", (("supplier",), ("vendor",))),
    ("approval", (("approve",), ("approved",), ("approves",), ("reviewer",), ("reviewers",))),
    ("timezone", (("timezone",), ("time","zone"))),
    ("insurance_provider", (("insurance","provider"), ("policy",), ("covers",))),
    ("brand", (("brand",),)),
    ("channel", (("channel",), ("channels",))),
    ("version", (("version",),)),
    ("breakfast_policy", (("breakfast","policy"), ("breakfast",))),
    ("maintenance_window", (("maintenance","window"),)),
    ("vpn_gateway", (("vpn","gateway"),)),
    ("mailing_address", (("mailing","address"), ("mailed","to"), ("mail","address"))),
    ("report_format", (("report","format"),)),
    ("sales_total", (("sales","total"),)),
    ("support_sla", (("support","sla"), ("sla",))),
    ("dose", (("dose",), ("dosage",))),
    ("salary", (("salary",), ("wage",), ("薪資",), ("薪水",))),
    ("budget", (("budget",), ("預算",))),
    ("balance", (("balance",), ("餘額",))),
    ("amount", (("amount",), ("total","amount"), ("金額",), ("總額",))),
    ("expiry", (("expire",), ("expires",), ("expired",), ("expiry",), ("warranty","ends"), ("deadline",), ("due",), ("到期",), ("截止",))),
    ("ownership", (("owner",), ("owns",), ("owned",), ("ownership",), ("responsible",), ("負責",), ("負責人",))),
    ("preference", (("prefer",), ("preferred",), ("prefers",), ("preference",), ("favorite",), ("favourite",), ("likes",), ("喜歡",), ("偏好",))),
    ("floor", (("floor",), ("level",), ("樓層",))),
    ("room", (("room",), ("meeting","room"), ("會議室",), ("房間",))),
    ("address", (("address",), ("地址",))),
    ("location", (("location",), ("stored",), ("shelf",), ("cabinet",), ("site",), ("地點",), ("位置",))),
    ("date", (("date",), ("day",), ("scheduled",), ("日期",), ("哪天",))),
    ("time", (("time",), ("window",), ("時間",))),
    ("hint", (("hint",), ("clue",), ("提示",), ("線索",))),
    ("shop", (("shop",), ("store",), ("cafe",), ("coffee","shop"), ("restaurant",), ("咖啡店",), ("商店",), ("餐廳",))),
    ("color", (("color",), ("colour",), ("顏色",))),
    ("quantity", (("count",), ("quantity",), ("many",), ("數量",))),
    ("type", (("type",), ("kind",), ("category",), ("class",), ("類型",), ("種類",))),
    ("format", (("format",),)),
    ("line", (("line",),)),
    ("phrase", (("phrase",), ("keyword",))),
)

MONTHS = {
    "january","february","march","april","may","june","july","august","september","october","november","december",
    "jan","feb","mar","apr","jun","jul","aug","sep","sept","oct","nov","dec",
}
DAYPART_GROUPS = {"morning": "morning", "am": "morning", "evening": "evening", "night": "evening", "pm": "evening"}
TEMPORAL_META = {"before","after","during","old","previous","prior"}
MULTI_ANSWER_CUES = {"two","both","jointly","copies"}
VALUE_RE = re.compile(r"(?:\d|[#@:/._-]|[A-Z][A-Z0-9_-]{1,})")

def _stems(text: str) -> list[str]:
    return [_stem(t) for t in tokens(text)]

def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in text)

def _phrase_present(text: str, phrase: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    if any(_contains_cjk(p) for p in phrase):
        return all(p.casefold() in lowered for p in phrase)
    stems = set(_stems(text))
    return all(_stem(p) in stems for p in phrase)

def attribute_signature(text: str) -> set[str]:
    found: set[str] = set()
    for concept, patterns in ATTRIBUTE_PATTERNS:
        if any(_phrase_present(text, pattern) for pattern in patterns):
            found.add(concept)
    if found & {"passport_number","national_id_number","registration_number","license_number","serial_number","phone","email","wifi_password","cost_center","keyboard_layout"}:
        found.discard("type")
    if "wifi_password" in found:
        found.discard("pin")
    return found

def _attribute_match(query: str, memory: str) -> bool:
    requested = attribute_signature(query)
    observed = attribute_signature(memory)
    if requested:
        specific = requested & {
            "blood_type","passport_number","national_id_number","registration_number","license_number","serial_number","phone","email",
            "wifi_password","cost_center","keyboard_layout","issuing_authority","breakfast_policy","maintenance_window",
            "vpn_gateway","mailing_address","report_format","sales_total","support_sla","dose","salary","budget","balance",
        }
        if specific:
            return bool(specific & observed)
        return bool(requested & observed)
    q = {s for s in _stems(query) if s not in GENERIC_STEMS and len(s) > 1}
    m = set(_stems(memory))
    return bool(q & m)

def _proper_anchors(query: str) -> set[str]:
    raw = re.findall(r"[A-Za-z][A-Za-z0-9_-]*", query)
    attrs = {s for _, patterns in ATTRIBUTE_PATTERNS for p in patterns for s in (_stem(x) for x in p if not _contains_cjk(x))}
    anchors = set()
    for i, tok in enumerate(raw):
        low = tok.casefold()
        stem = _stem(low)
        if low in QUESTION_WORDS or stem in GENERIC_STEMS or stem in attrs or low in MONTHS or low in TEMPORAL_META or low in DAYPART_GROUPS:
            continue
        if tok[0].isupper() and i > 0:
            anchors.add(stem)
        elif any(ch.isdigit() for ch in tok) and not tok.isdigit():
            anchors.add(stem)
    return anchors

def _subject_match(query: str, memory: str) -> bool:
    anchors = _proper_anchors(query)
    return not anchors or anchors.issubset(set(_stems(memory)))

CONTEXT_SENSITIVE_ATTRIBUTES = {"line","date","time","location","phrase","type","quantity","color","channel"}

def _context_terms(text: str) -> set[str]:
    stems = set(_stems(text))
    attrs = {s for _, patterns in ATTRIBUTE_PATTERNS for p in patterns for s in (_stem(x) for x in p if not _contains_cjk(x))}
    return {s for s in stems if s not in GENERIC_STEMS and s not in attrs and s not in {_stem(x) for x in MONTHS | set(DAYPART_GROUPS) | TEMPORAL_META} and s not in UPDATE_STEMS and s not in CERTAINTY_STEMS and s not in UNCERTAIN_STEMS and len(s) > 1}

def _context_match(query: str, memory: str) -> bool:
    if _contains_cjk(query):
        return True
    requested = attribute_signature(query)
    if not (requested & CONTEXT_SENSITIVE_ATTRIBUTES):
        return True
    q = _context_terms(query)
    return not q or bool(q & _context_terms(memory))

def _temporal_constraints(text: str) -> dict[str, Any]:
    stems = set(_stems(text))
    months = {m for m in MONTHS if _stem(m) in stems}
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", text))
    dayparts = {DAYPART_GROUPS[t] for t in DAYPART_GROUPS if _stem(t) in stems}
    meta = {t for t in TEMPORAL_META if _stem(t) in stems}
    return {"months": months, "years": years, "dayparts": dayparts, "meta": meta}

def _temporal_match(query: str, memory: str) -> bool:
    q = _temporal_constraints(query)
    m = _temporal_constraints(memory)
    if q["months"] and not q["months"].issubset(m["months"]):
        return False
    if q["years"] and not q["years"].issubset(m["years"]):
        return False
    if q["dayparts"] and not q["dayparts"].issubset(m["dayparts"]):
        return False
    if q["meta"] & {"before","after","during"} and not (q["meta"] & m["meta"]):
        return False
    return True

def query_requires_certainty(query: str) -> bool:
    stems = set(_stems(query))
    lowered = query.casefold()
    return bool(stems & CERTAINTY_STEMS) or any(x in lowered for x in ("確定","確認","最終","正式"))

def memory_is_uncertain(memory: str) -> bool:
    stems = set(_stems(memory))
    lowered = memory.casefold()
    return bool(stems & UNCERTAIN_STEMS) or any(x in lowered for x in ("可能","也許","暫定","大概"))

def question_echo(memory: str, query: str) -> bool:
    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip().casefold().rstrip("?？.!。"))
    return norm(memory) == norm(query)

def _ignored_value_stems(query: str) -> set[str]:
    ignored = set(_stems(query)) | GENERIC_STEMS | DISCOURSE_STEMS | UNCERTAIN_STEMS | CERTAINTY_STEMS | UPDATE_STEMS
    requested = attribute_signature(query)
    for concept, patterns in ATTRIBUTE_PATTERNS:
        if concept not in requested:
            continue
        for p in patterns:
            ignored |= {_stem(x) for x in p if not _contains_cjk(x)}
    ignored |= {_stem(x) for x in MONTHS | set(DAYPART_GROUPS) | TEMPORAL_META}
    return ignored

def value_tokens(memory: str, query: str) -> set[str]:
    ignored = _ignored_value_stems(query)
    out = {s for s in _stems(memory) if s not in ignored and len(s) > 1}
    for raw in re.findall(r"[A-Za-z0-9#@:/._-]+", memory):
        if VALUE_RE.search(raw) and _stem(raw.casefold()) not in ignored:
            out.add(raw.casefold())
    if _contains_cjk(memory) and not question_echo(memory, query) and memory.strip() != query.strip():
        q_chars = {c for c in query if "\u4e00" <= c <= "\u9fff"}
        extra = {c for c in memory if "\u4e00" <= c <= "\u9fff"} - q_chars
        if extra:
            out.add("CJK_ASSERTED_VALUE")
    return out

def _candidate_support(memory: dict[str, Any], query: str) -> tuple[bool, set[str], list[str]]:
    text = memory["text"]
    if question_echo(text, query):
        return False, set(), ["query_echo"]
    if not _attribute_match(query, text):
        return False, set(), ["attribute_mismatch"]
    if not _subject_match(query, text):
        return False, set(), ["subject_mismatch"]
    if not _context_match(query, text):
        return False, set(), ["context_mismatch"]
    if not _temporal_match(query, text):
        return False, set(), ["temporal_mismatch"]
    if query_requires_certainty(query):
        memory_stems = set(_stems(text))
        has_certainty = bool(memory_stems & CERTAINTY_STEMS) or any(x in text.casefold() for x in ("確定","確認","最終","正式"))
        if memory_is_uncertain(text) or not has_certainty:
            return False, set(), ["insufficient_certainty"]
    values = value_tokens(text, query)
    if not values:
        return False, set(), ["no_value_bearing_assertion"]
    return True, values, ["direct_proposition_support"]

def answerability_signature(case: dict[str, Any], ranking: list[str] | None = None) -> dict[str, Any]:
    ranking = ranking if ranking is not None else pse_candidate_v2_rank(case, 5)
    by_id = {m["id"]: m for m in case["memories"]}
    inspected = [by_id[mid] for mid in ranking if mid in by_id]
    supports: list[tuple[dict[str, Any], set[str]]] = []
    rejected: dict[str, list[str]] = {}
    for memory in inspected:
        ok, values, reasons = _candidate_support(memory, case["query"])
        if ok:
            supports.append((memory, values))
        else:
            rejected[memory["id"]] = reasons
    if not supports:
        return {"verdict": VERDICT_INSUFFICIENT, "supported_memory_ids": [], "rejected": rejected, "requested_attributes": sorted(attribute_signature(case["query"]))}
    query_stems = set(_stems(case["query"]))
    multi_answer = bool(query_stems & {_stem(x) for x in MULTI_ANSWER_CUES})
    resolving = [item for item in supports if set(_stems(item[0]["text"])) & (UPDATE_STEMS | CERTAINTY_STEMS)]
    if resolving:
        newest = max(resolving, key=lambda item: parse_timestamp(item[0].get("timestamp")))
        supports = [newest]
    elif len(supports) > 1 and not multi_answer:
        query_temporal = _temporal_constraints(case["query"])
        if not any(query_temporal[key] for key in ("months","years","dayparts","meta")):
            timestamps = {parse_timestamp(item[0].get("timestamp")) for item in supports}
            if len(timestamps) > 1:
                newest_time = max(timestamps)
                supports = [item for item in supports if parse_timestamp(item[0].get("timestamp")) == newest_time]
        if len(supports) > 1:
            normalized_values = [vals for _, vals in supports if vals]
            if len(normalized_values) > 1 and not set.intersection(*normalized_values):
                return {"verdict": VERDICT_CONTRADICTED, "supported_memory_ids": [m["id"] for m, _ in supports], "rejected": rejected, "requested_attributes": sorted(attribute_signature(case["query"]))}
    return {"verdict": VERDICT_SUPPORTED, "supported_memory_ids": [m["id"] for m, _ in supports], "rejected": rejected, "requested_attributes": sorted(attribute_signature(case["query"]))}

def pse_candidate_v4_rank(case: dict[str, Any], k: int = 5) -> list[str]:
    ranking = pse_candidate_v2_rank(case, k)
    signature = answerability_signature(case, ranking)
    return ranking if signature["verdict"] == VERDICT_SUPPORTED else []
