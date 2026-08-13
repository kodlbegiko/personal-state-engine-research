# Candidate-v6 Architecture Hypothesis Comparison

Status: PRE-IMPLEMENTATION RESEARCH EVIDENCE
Date: 2026-08-13

## Research question

Can a deterministic verifier preserve Candidate-v2 retrieval quality while rejecting meta-discourse/no-value memories by requiring explicit assertion structure rather than residual lexical tokens?

## Hypothesis A — Rule-based assertion grammar only

A finite set of deterministic grammatical templates directly maps text to `(subject, predicate, value, polarity, temporal)`.

Advantages:
- deterministic and cheap;
- easy to unit test;
- explicit value slot prevents many residue errors;
- no external dependency.

Risks:
- template brittleness across paraphrases;
- grammar and discourse-role detection become entangled;
- a growing template list can regress into benchmark-specific patching;
- meta-discourse may still accidentally match an assertion template.

Expected retrieval preservation: medium-high if grammar coverage is sufficient.
Expected no-evidence safety: high on covered patterns, uncertain on unseen discourse forms.

## Hypothesis B — Deterministic proposition graph with typed discourse roles

Every memory is mapped into one or more typed propositions. Discourse type is encoded alongside proposition type and comparable propositions form a graph used for requirement coverage/conflict resolution.

Advantages:
- clean semantic representation;
- contradiction/temporal resolution is explicit;
- extensible to multi-slot queries.

Risks:
- proposition extraction remains the hard problem;
- graph machinery can add complexity without fixing discourse classification;
- greater implementation surface increases failure modes and development overfitting risk.

Expected retrieval preservation: medium.
Expected no-evidence safety: high if extraction is correct.

## Hypothesis C — Two-stage deterministic parser: discourse-role gate + assertion-slot extractor

Stage 1 assigns a deterministic discourse role before any value can be extracted. Roles include assertion, question, agenda item, review/topic, explicit no-value, unresolved/inferential, and unknown. Stage 2 runs only on assertion-like text and extracts a typed `(subject, predicate, object/value, polarity, temporal scope)` structure using bounded patterns and relation aliases. The verifier then evaluates requirement coverage and contradiction using these typed objects.

Advantages:
- directly targets the confirmed Candidate-v5 mechanism;
- meta-discourse cannot become a value because it is rejected before slot extraction;
- separation of discourse classification and assertion extraction is auditable;
- supports fail-closed behavior;
- preserves Candidate-v2 ranking independently;
- deterministic and zero-cost.

Risks:
- discourse-role ordering must be carefully defined;
- implicit assertions outside supported grammar may cause false abstention;
- relation aliases still require bounded maintenance;
- finite grammar coverage may remain a generalization bottleneck.

Expected retrieval preservation: high if assertion grammar covers ordinary declarative evidence.
Expected no-evidence safety: high.

## Hypothesis D — Token-sequence finite-state transducer with typed slots

Use a finite-state machine over normalized tokens to detect subject/relation/copula/value patterns and discourse-prefix/suffix states.

Advantages:
- deterministic;
- explicit state transitions;
- less regex backtracking ambiguity;
- highly auditable.

Risks:
- more engineering complexity than necessary for current benchmark language;
- punctuation and multiword relations complicate token-state design;
- may not outperform a disciplined two-stage parser.

Expected retrieval preservation: high after sufficient grammar work.
Expected no-evidence safety: high.

## Comparison

| Criterion | A Grammar only | B Proposition graph | C Two-stage parser | D FST |
|---|---:|---:|---:|---:|
| targets confirmed failure mechanism | medium | medium | **high** | high |
| determinism | high | high | **high** | high |
| testability | high | high | **high** | high |
| interpretability | high | high | **high** | high |
| fail-closed semantics | medium | high | **high** | high |
| external dependency | none | none | **none** | none |
| computational cost | low | low | **low** | low |
| implementation complexity | low | high | **medium** | high |
| overfitting risk | medium-high | medium | **medium-low** | medium |
| retrieval preservation expectation | medium-high | medium | **high** | high |
| no-evidence safety expectation | high on covered patterns | high | **high** | high |
| extensibility | medium | high | **high** | high |

## Selected architecture

**Hypothesis C: Two-stage deterministic parser — discourse-role gate + assertion-slot extractor.**

### Rationale

Candidate-v5 did not fail because it lacked another relation alias or another blacklist token. It failed because value existence was inferred before establishing that the text was an assertion. The selected architecture reverses that dependency:

1. classify discourse role;
2. only assertion-like text is eligible for value extraction;
3. extract typed assertion slots;
4. compare only compatible evidence objects;
5. preserve Candidate-v2 ranking if and only if required assertions are supported.

This is a genuinely new method identity relative to Candidate-v5 because support is no longer based on residue-set values. The object/value must occupy an explicit assertion slot.

## Initial bounded grammar policy

The first implementation may support deterministic English assertion constructions sufficient for the repository's existing synthetic development style, including:

- `The current <relation> for <subject> is <value>.`
- `<subject> <relation> is <value>.`
- `<subject>'s <relation> is <value>.`
- `<relation> for <subject> changed/updated to <value>.`
- `Correction: <subject> <relation> changed to <value>.`
- explicit negative/no-value constructions handled before positive assertion extraction.

The parser must not treat arbitrary residual nouns as values.

## Pre-registered risk

The principal expected failure mode of Candidate-v6 is false abstention on valid assertions that fall outside the bounded grammar. Development tuning may improve general grammar coverage before freeze, but any repair based on post-freeze protected results is prohibited and requires a new candidate identity.
