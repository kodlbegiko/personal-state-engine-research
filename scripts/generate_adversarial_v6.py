#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks/algorithm-development/adversarial-v6-confirmatory/cases-v1.json"
MANIFEST = ROOT / "benchmarks/algorithm-development/adversarial-v6-confirmatory/manifest-v1.json"
V4_FREEZE = "e6780204686d3de526905eca8f2778c2510b7876"
V4_VALIDATION_RUN = 31392806910

ENTITIES = ["Aster", "Boreal", "Cedar", "Dune", "Ember", "Fjord"]
OTHERS = ["Vega", "Aurora", "Maple", "Vale", "Ash", "Lake"]
PEOPLE = ["Nia", "Omar", "Priya", "Felix", "Maya", "Tariq"]
VALUES = {
    "budget": ["315000", "428000", "96000", "173000", "78000", "251000"],
    "email": ["ops@aster.example", "team@boreal.example", "desk@cedar.example", "hello@dune.example", "service@ember.example", "care@fjord.example"],
    "room": ["Room 417", "Room 208", "Room 31", "Room 8", "Room 64", "Room 112"],
    "serial": ["AS-48291", "BR-55120", "CD-10488", "DN-77231", "EM-66012", "FJ-90317"],
    "sla": ["two hours", "three hours", "four hours", "six hours", "eight hours", "twelve hours"],
    "address": ["84 Pine Avenue", "17 Harbor Road", "202 Cedar Lane", "5 Ridge Street", "91 Ember Way", "33 Fjord Drive"],
}
FIELDS = [
    ("budget", lambda e, v: f"What is Project {e}'s approved budget?", lambda e, v: f"The approved Project {e} budget is {v}.", lambda e, p: f"Project {e} owner is {p}."),
    ("email", lambda e, v: f"What is the {e} account email?", lambda e, v: f"The {e} account email is {v}.", lambda e, p: f"The {e} account phone number is 555-01{len(e):02d}."),
    ("room", lambda e, v: f"What is the {e} review room?", lambda e, v: f"The {e} review room is {v}.", lambda e, p: f"The {e} review begins at 10:00."),
    ("serial", lambda e, v: f"What is device {e}'s serial number?", lambda e, v: f"Device {e} serial number is {v}.", lambda e, p: f"Device {e} warranty expires next year."),
    ("sla", lambda e, v: f"What is the {e} support SLA?", lambda e, v: f"The {e} support SLA is {v}.", lambda e, p: f"The {e} support owner is {p}."),
    ("address", lambda e, v: f"What is the {e} mailing address?", lambda e, v: f"The {e} mailing address is {v}.", lambda e, p: f"The {e} phone number is 555-02{len(e):02d}."),
]


def m(mid: str, text: str, day: int, year: int = 2026, month: int = 7) -> dict:
    return {"id": mid, "text": text, "timestamp": f"{year:04d}-{month:02d}-{day:02d}"}


def case(cid: str, category: str, query: str, texts: list[tuple[str, int]], relevant: list[str]) -> dict:
    return {
        "id": cid,
        "category": category,
        "query": query,
        "memories": [m(f"m{i+1}", text, day) for i, (text, day) in enumerate(texts)],
        "relevant_memory_ids": relevant,
    }


def field_case(index: int, category: str, support_day: int = 10) -> tuple[str, str, str, str, str, str]:
    name, qf, sf, wf = FIELDS[index]
    e, other, person = ENTITIES[index], OTHERS[index], PEOPLE[index]
    value = VALUES[name][index]
    return name, e, other, person, qf(e, value), sf(e, value)


def build() -> list[dict]:
    cases: list[dict] = []
    aid = 1
    nid = 1

    # 60 answerable: 10 mechanism-agnostic families x 6 cases.
    for i in range(6):
        name, e, other, person, q, support = field_case(i, "single_support")
        other_support = FIELDS[i][2](other, VALUES[name][i])
        wrong = FIELDS[i][3](e, person)
        texts = [(support, 10), (wrong, 11), (other_support, 12), (f"{e} review is scheduled next week.", 13), (f"{e} owner is {person}.", 14)]
        cases.append(case(f"ADV6-A-{aid:03d}", "single_support", q, texts, ["m1"])); aid += 1

    for i, e in enumerate(ENTITIES):
        q = f"Which two reviewers approved Project {e}?"
        texts = [(f"Reviewer {PEOPLE[i]} approved Project {e}.", 10), (f"Reviewer {PEOPLE[(i+1)%6]} approved Project {e}.", 10), (f"Project {e} budget is {VALUES['budget'][i]}.", 11), (f"Reviewer {PEOPLE[i]} approved Project {OTHERS[i]}.", 12), (f"Project {e} owner is {PEOPLE[(i+2)%6]}.", 13)]
        cases.append(case(f"ADV6-A-{aid:03d}", "multi_support", q, texts, ["m1", "m2"])); aid += 1

    update_specs = [
        ("owner", lambda e: f"Who is the current owner of Project {e}?", lambda e, old: f"Project {e} owner was {old}.", lambda e, new: f"Project {e} owner was updated to {new}, who is the current owner."),
        ("email", lambda e: f"What is the current {e} account email?", lambda e, old: f"{e} account email was old@{e.lower()}.example.", lambda e, new: f"{e} account email was updated to current@{e.lower()}.example and is current."),
        ("room", lambda e: f"What is the current {e} meeting room?", lambda e, old: f"{e} meeting room was Room {old}.", lambda e, new: f"{e} meeting room moved to Room {new} and is current."),
        ("budget", lambda e: f"What is the current {e} project budget?", lambda e, old: f"{e} project budget was {old}.", lambda e, new: f"{e} project budget changed to {new} and is current."),
        ("dose", lambda e: f"What is the current morning dose of {e}med?", lambda e, old: f"The morning dose of {e}med was {old} mg.", lambda e, new: f"The morning dose of {e}med was updated to {new} mg and is current."),
        ("format", lambda e: f"What is the current {e} report format?", lambda e, old: f"{e} report format was {old}.", lambda e, new: f"{e} report format changed to {new} and is current."),
    ]
    olds = [PEOPLE[0], "old", "4", "140000", "5", "PDF"]
    news = [PEOPLE[1], "new", "18", "155000", "7.5", "CSV"]
    for i, (_, qf, oldf, newf) in enumerate(update_specs):
        e = ENTITIES[i]
        q = qf(e)
        texts = [(oldf(e, olds[i]), 1), (newf(e, news[i]), 20), (f"{e} owner is {PEOPLE[i]}.", 21), (f"{e} review occurs Friday.", 22), (f"{OTHERS[i]} has a similar update.", 23)]
        cases.append(case(f"ADV6-A-{aid:03d}", "temporal_update", q, texts, ["m2"])); aid += 1

    confirmed_specs = [
        ("conference venue", ["East Hall", "West Hall", "North Center"]),
        ("training room", ["Room A", "Room B", "Room C"]),
        ("supplier", ["Helix", "Vertex", "Meridian"]),
        ("maintenance window", ["Saturday morning", "Sunday morning", "Sunday 02:00-04:00"]),
        ("VPN gateway", ["vpn-a.example", "vpn-b.example", "vpn-c.example"]),
        ("report format", ["DOCX", "PDF", "CSV"]),
    ]
    for i, (field, vals) in enumerate(confirmed_specs):
        e = ENTITIES[i]
        q = f"What is the confirmed {e} {field}?"
        texts = [(f"The {e} {field} might be {vals[0]}.", 1), (f"The {e} {field} might be {vals[1]}.", 2), (f"The confirmed {e} {field} is {vals[2]}.", 5), (f"{e} owner is {PEOPLE[i]}.", 6), (f"{vals[2]} is mentioned in the logistics file.", 7)]
        cases.append(case(f"ADV6-A-{aid:03d}", "contradiction_resolved", q, texts, ["m3"])); aid += 1

    for i in range(6):
        name, e, other, person, q, support = field_case(i, "duplicate_distractor")
        wrong = FIELDS[i][3](e, person)
        texts = [(support, 10), (wrong, 11), (wrong, 11), (f"{e} review is Thursday.", 12), (FIELDS[i][2](other, VALUES[name][i]), 13)]
        cases.append(case(f"ADV6-A-{aid:03d}", "duplicate_distractor", q, texts, ["m1"])); aid += 1

    for i in range(6):
        name, e, other, person, q, support = field_case(i, "lexical_overlap_distractor")
        no_value = f"The {e} {name} question was discussed, but this note records no final {name} value."
        texts = [(support, 10), (no_value, 20), (FIELDS[i][3](e, person), 21), (FIELDS[i][2](other, VALUES[name][i]), 22), (f"The {e} {name} review remains on the agenda.", 23)]
        cases.append(case(f"ADV6-A-{aid:03d}", "lexical_overlap_distractor", q, texts, ["m1"])); aid += 1

    stale_specs = [
        (lambda e: f"Who is the current owner of Project {e}?", lambda e: f"In 2024, Project {e} owner was {PEOPLE[0]}.", lambda e: f"Project {e} owner was replaced by {PEOPLE[1]} in 2026; {PEOPLE[1]} is current."),
        (lambda e: f"What is the current {e} account email?", lambda e: f"In 2024, {e} account email was old@{e.lower()}.example.", lambda e: f"{e} account email changed to current@{e.lower()}.example in 2026 and is current."),
        (lambda e: f"What is the current {e} room?", lambda e: f"In 2025, {e} room was Room 1.", lambda e: f"{e} room moved to Room 9 in 2026; Room 9 is current."),
        (lambda e: f"What is the current {e} budget?", lambda e: f"In 2025, {e} budget was 40000.", lambda e: f"{e} budget changed to 47000 in 2026 and is current."),
        (lambda e: f"What is the current {e} mailing address?", lambda e: f"In 2024, {e} mailing address was 10 Old Road.", lambda e: f"{e} mailing address was updated to 22 New Street in 2026 and is current."),
        (lambda e: f"What is the current morning dose of {e}med?", lambda e: f"In 2025, the morning dose of {e}med was 2 mg.", lambda e: f"The morning dose of {e}med changed to 3 mg in 2026 and is current."),
    ]
    for i, (qf, oldf, currentf) in enumerate(stale_specs):
        e = ENTITIES[i]
        texts = [(oldf(e), 1), (currentf(e), 15), (f"{e} owner is {PEOPLE[i]}.", 16), (f"{e} archive contains older notes.", 17), (f"{OTHERS[i]} has a similar field.", 18)]
        cases.append(case(f"ADV6-A-{aid:03d}", "stale_evidence", qf(e), texts, ["m2"])); aid += 1

    for i in range(6):
        name, e, other, person, q, support = field_case(i, "recency_trap")
        wrong = FIELDS[i][3](e, person)
        texts = [(support, 1), (f"{wrong[:-1]} changed yesterday.", 25), (f"{e} meeting moved today.", 26), (FIELDS[i][2](other, VALUES[name][i]), 27), (f"{e} {name} review is next week.", 28)]
        cases.append(case(f"ADV6-A-{aid:03d}", "recency_trap", q, texts, ["m1"])); aid += 1

    for i in range(6):
        e = ENTITIES[i]
        q = f"Who is the current owner of Project {e}?"
        texts = [(f"Session 1 note: Project {e} owner was {PEOPLE[i]}.", 1), (f"Session 5 update: Project {e} owner changed to {PEOPLE[(i+1)%6]}, who is current.", 22), (f"Session 2: Project {e} budget is {VALUES['budget'][i]}.", 10), (f"Session 4: Project {e} meeting is Friday.", 20), (f"Project {OTHERS[i]} owner is {PEOPLE[(i+1)%6]}.", 23)]
        cases.append(case(f"ADV6-A-{aid:03d}", "multi_session_evidence", q, texts, ["m2"])); aid += 1

    paraphrases = [
        ("Which address should mail for the Aster office go to?", "The Aster mailing address is 84 Pine Avenue."),
        ("How quickly must the Boreal support team respond?", "The Boreal support SLA is three hours."),
        ("Which inbox belongs to the Cedar account?", "The Cedar account email is desk@cedar.example."),
        ("When is the Dune warranty over?", "Device Dune warranty expires on October 9, 2026."),
        ("Who is responsible for Project Ember right now?", "Project Ember owner changed to Maya, who is current."),
        ("Where are the Fjord blueprints kept?", "The Fjord blueprints are stored on shelf H3."),
    ]
    for i, (q, support) in enumerate(paraphrases):
        texts = [(support, 10), (f"{ENTITIES[i]} owner is {PEOPLE[i]}.", 11), (f"{OTHERS[i]} has a similar record.", 12), (f"{ENTITIES[i]} review is next week.", 13), (f"A different field for {ENTITIES[i]} was updated.", 14)]
        cases.append(case(f"ADV6-A-{aid:03d}", "paraphrased_query", q, texts, ["m1"])); aid += 1

    # 30 no-evidence: 10 families x 3 cases. None contain a supporting proposition.
    for i in range(3):
        e, other, person = ENTITIES[i], OTHERS[i], PEOPLE[i]
        name, qf, sf, wf = FIELDS[i]
        q = qf(e, VALUES[name][i])
        texts = [(wf(e, person), 10), (f"{e} deadline is September {i+2}.", 11), (f"The {e} {name} field is not recorded.", 12), (sf(other, VALUES[name][i]), 13), (f"{e} review is complete.", 14)]
        cases.append(case(f"ADV6-N-{nid:03d}", "same_subject_wrong_attribute", q, texts, [])); nid += 1

    for i in range(3, 6):
        e, other, person = ENTITIES[i], OTHERS[i], PEOPLE[i]
        name, qf, sf, wf = FIELDS[i]
        q = qf(e, VALUES[name][i])
        texts = [(sf(other, VALUES[name][i]), 10), (wf(e, person), 11), (f"The {e} {name} field is pending.", 12), (sf(ENTITIES[(i+1)%6], VALUES[name][i]), 13), (f"{e} contract is active.", 14)]
        cases.append(case(f"ADV6-N-{nid:03d}", "same_relation_wrong_subject", q, texts, [])); nid += 1

    for i in range(3):
        name, e, other, person, q, support = field_case(i, "high_lexical_overlap")
        texts = [(f"The {e} {name} question remains unanswered; no {name} value is recorded.", 10), (f"The {e} {name} workflow is documented.", 11), (FIELDS[i][3](e, person), 12), (FIELDS[i][2](other, VALUES[name][i]), 13), (f"{e} finance notes contain no final answer.", 14)]
        cases.append(case(f"ADV6-N-{nid:03d}", "high_lexical_overlap", q, texts, [])); nid += 1

    echoes = [
        ("What is the private archive PIN?", ["What is the private archive PIN?", "The archive is on floor 2.", "Archive access training is Friday.", "PIN rotation policy is monthly.", "No PIN value is recorded here."]),
        ("Where is the red binder stored?", ["Where is the red binder stored?", "The blue binder is stored on shelf B2.", "Red binder inventory is pending.", "Shelf map was updated.", "No storage location for the red binder is recorded."]),
        ("What is the Nimbus Wi-Fi password?", ["What is the Nimbus Wi-Fi password?", "Nimbus Wi-Fi network name is NimbusNet.", "Wireless maintenance is Sunday.", "Password rotation policy is monthly.", "No password value is stored here."]),
    ]
    for q, lines in echoes:
        cases.append(case(f"ADV6-N-{nid:03d}", "query_echo", q, [(t, 10+j) for j, t in enumerate(lines)], [])); nid += 1

    stale_no = [
        ("Who owns Project Quartz now?", ["In 2024, Project Quartz owner was Mira; later ownership is not recorded.", "Quartz budget is 81000.", "Quartz current-owner review is pending.", "Mira now owns Project Topaz.", "Quartz archive contains 2024 notes."]),
        ("What is the current Redwood account email?", ["In 2023, Redwood account email was old@redwood.example; no newer address is recorded.", "Redwood phone is 555-0166.", "Redwood email update is pending.", "Pine account email is current@pine.example.", "Redwood contract is active."]),
        ("What is the current Silver room?", ["In 2025, Silver room was Room 6; later room assignments are not recorded.", "Silver meeting is Thursday.", "Silver room update is pending.", "Gold room is Room 9.", "Silver owner is Pia."]),
    ]
    for q, lines in stale_no:
        cases.append(case(f"ADV6-N-{nid:03d}", "stale_only_evidence", q, [(t, 10+j) for j, t in enumerate(lines)], [])); nid += 1

    conflicts = [
        ("What is the confirmed Willow training room?", ["A current note says Willow training room is Room A.", "Another current note says Willow training room is Room B.", "Neither note is marked final or superseded.", "Willow starts at nine.", "Room A has a projector."]),
        ("What is the confirmed Xeno supplier?", ["A current procurement note lists Xeno supplier Helix.", "A second current procurement note lists Xeno supplier Vertex.", "No approval or resolution is recorded.", "Xeno budget is 42000.", "Supplier review is Friday."]),
        ("What is the confirmed Yonder report format?", ["A current note says Yonder report format is PDF.", "Another current note says Yonder report format is CSV.", "No final decision is recorded.", "Yonder owner is Vic.", "Report deadline is Monday."]),
    ]
    for q, lines in conflicts:
        cases.append(case(f"ADV6-N-{nid:03d}", "contradictory_unresolved_evidence", q, [(t, 10+j) for j, t in enumerate(lines)], [])); nid += 1

    partial = [
        ("What is my passport number?", ["My passport renewal appointment is August 22.", "The passport expires next year.", "The issuing office is downtown.", "A passport number is required on the form, but no number is recorded.", "My travel date is September 3."]),
        ("What is the office Wi-Fi password?", ["The office Wi-Fi network name is StudioNet.", "Password rotation happens monthly.", "The router is in the server room.", "The password field is intentionally omitted from this note.", "Guest Wi-Fi is available."]),
        ("What is the Acme cost center?", ["Acme owner is Jo.", "Acme budget is 90000.", "Cost-center review is next week.", "The cost-center field has not been assigned.", "Acme headquarters is downtown."]),
    ]
    for q, lines in partial:
        cases.append(case(f"ADV6-N-{nid:03d}", "partial_evidence", q, [(t, 10+j) for j, t in enumerate(lines)], [])); nid += 1

    plausible = [
        ("What is my blood type?", ["I donated blood last month.", "The donation was accepted.", "The clinic is on Main Street.", "My blood-type card is not in these records.", "The next donation is in October."]),
        ("What is the laptop keyboard layout?", ["The laptop model is ThinkPad T14.", "The laptop was purchased in Taiwan.", "The OS language is English.", "Keyboard-layout details were not recorded.", "The warranty is active."]),
        ("What is the vehicle registration number?", ["The vehicle is a blue sedan.", "Insurance is active.", "Registration renewal is due in November.", "The registration number itself is not recorded.", "Parking permit is valid."]),
    ]
    for q, lines in plausible:
        cases.append(case(f"ADV6-N-{nid:03d}", "plausible_unsupported_inference", q, [(t, 10+j) for j, t in enumerate(lines)], [])); nid += 1

    temporal = [
        ("What was the April sales total?", ["March sales total was 88000.", "May sales total was 93000.", "April sales meeting occurred on April 30, but no total was recorded.", "April budget was 87000.", "Q2 report is pending."]),
        ("Who owned Project Zenith in February 2026?", ["Project Zenith owner was Aya in January 2026.", "Project Zenith owner was Ben in March 2026.", "A February review occurred, but ownership was not recorded.", "Zenith budget is 73000.", "Zenith deadline is June."]),
        ("What was the evening dose of Medora on July 5?", ["The evening dose of Medora on July 4 was 20 mg.", "The evening dose of Medora on July 6 was 25 mg.", "A July 5 medication note exists but no dose is recorded.", "The morning dose on July 5 was 10 mg.", "Medora refill is Friday."]),
    ]
    for q, lines in temporal:
        cases.append(case(f"ADV6-N-{nid:03d}", "temporal_near_match", q, [(t, 10+j) for j, t in enumerate(lines)], [])); nid += 1

    near = [
        ("What is the Orion office mailing address?", ["Orion office mailing schedule is Tuesday.", "Orion office email address is office@orion.example.", "Orion shipping address is not recorded.", "Orion office address-change form is blank.", "Orion owner is Lan."]),
        ("What is the Pixel support contract expiry date?", ["Pixel support contract owner is Ezra.", "Pixel support contract renewal process starts in October.", "Pixel warranty expiry is December 1, 2026.", "Pixel support contract expiry field is blank.", "Pixel SLA is four hours."]),
        ("What is the Raven approved supplier?", ["Raven supplier review is approved to begin.", "Raven supplier shortlist contains three names but no selection.", "Raven procurement owner is Emi.", "Raven budget is 51000.", "No approved supplier is recorded."]),
    ]
    for q, lines in near:
        cases.append(case(f"ADV6-N-{nid:03d}", "near_duplicate_non_answer", q, [(t, 10+j) for j, t in enumerate(lines)], [])); nid += 1

    assert aid == 61, aid
    assert nid == 31, nid
    assert len(cases) == 90
    assert sum(bool(c["relevant_memory_ids"]) for c in cases) == 60
    assert sum(not c["relevant_memory_ids"] for c in cases) == 30
    expected = {
        "single_support": 6, "multi_support": 6, "temporal_update": 6, "contradiction_resolved": 6,
        "duplicate_distractor": 6, "lexical_overlap_distractor": 6, "stale_evidence": 6, "recency_trap": 6,
        "multi_session_evidence": 6, "paraphrased_query": 6,
        "same_subject_wrong_attribute": 3, "same_relation_wrong_subject": 3, "high_lexical_overlap": 3,
        "query_echo": 3, "stale_only_evidence": 3, "contradictory_unresolved_evidence": 3,
        "partial_evidence": 3, "plausible_unsupported_inference": 3, "temporal_near_match": 3,
        "near_duplicate_non_answer": 3,
    }
    assert Counter(c["category"] for c in cases) == Counter(expected)
    assert len({c["id"] for c in cases}) == 90
    return cases


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    cases = build()
    payload = {
        "schema_version": "adversarial-v6-confirmatory-v1",
        "status": "FROZEN_CANDIDATE_AGNOSTIC_DATASET_BEFORE_STAGE1",
        "candidate_v4_freeze_commit": V4_FREEZE,
        "created_after_candidate_v4_validation_run": V4_VALIDATION_RUN,
        "case_count": 90,
        "answerable_case_count": 60,
        "no_evidence_case_count": 30,
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = Counter(c["category"] for c in cases)
    manifest = {
        "schema_version": "adversarial-v6-confirmatory-manifest-v1",
        "status": "FROZEN_BEFORE_ANY_SYSTEM_EXECUTION",
        "dataset_path": str(OUT.relative_to(ROOT)),
        "dataset_sha256": sha256(OUT),
        "total_cases": 90,
        "answerable_cases": 60,
        "no_evidence_cases": 30,
        "category_counts": dict(sorted(counts.items())),
        "mechanism_agnostic": True,
        "candidate_v4_freeze_commit": V4_FREEZE,
        "candidate_v4_source_sha256": "b57af79b3ef91497a4d3df373a990f0daa76a21c4daf87c7dd27f1c258c6d344",
        "candidate_v4_config_sha256": "a6341817ed382423a4d48d5df890765bb59f887655f16bd0e0647b89e3379606",
        "candidate_v4_validation_run": V4_VALIDATION_RUN,
        "candidate_v4_validation_artifact_id": 9064343914,
        "candidate_v4_validation_artifact_digest": "sha256:79a14acbbb50d7ce53a18f5655d09c73dd4a10e37aeeb2d1039c407eac3d61a3",
        "adversarial_v5_reused": False,
        "sealed_final_source_used": False,
        "new_monetary_cost_usd": 0.0,
        "generation_rule": "Deterministic category templates fixed from the preregistered v6 family matrix; no system was executed against these cases before this manifest was written.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"dataset_sha256": manifest["dataset_sha256"], "cases": 90, "answerable": 60, "no_evidence": 30}, sort_keys=True))


if __name__ == "__main__":
    main()
