# Candidate-v5 Failure Taxonomy for Candidate-v6

Status: PRE-IMPLEMENTATION RESEARCH EVIDENCE
Date: 2026-08-13

The purpose of this taxonomy is to convert Candidate-v5 negative evidence into testable mechanism hypotheses without tuning Candidate-v5 or treating historical validation cases as fresh confirmatory evidence.

## Confirmed protected-validation mechanism

Candidate-v5 protected validation produced two false abstentions and two no-evidence false retrievals. Post-hoc diagnosis identified `discourse_residue_misclassified_as_answer_value` as the primary remaining mechanism. The structural defect is that Candidate-v5 infers values from lexical residue after subtracting query and non-value stems. A discourse word that survives that subtraction can become a fake value-bearing proposition.

## Failure families

| ID | Family | Symptom | Root-cause hypothesis | Candidate-v5 behavior | Desired Candidate-v6 behavior | Testable acceptance condition |
|---|---|---|---|---|---|---|
| A | discourse residue | meta text creates support/conflict | leftover discourse token is treated as value | may support or contradict | classify discourse role; object=None | meta-only memory never creates answer support |
| B | query echo | repeated question looks evidential | lexical overlap plus residual punctuation/token | may create proposition after wording variation | QUESTION/META role | query echo and paraphrased echo abstain |
| C | agenda-only mention | agenda term becomes value | no explicit assertion slot required | may create fake value | AGENDA_ITEM, object=None | agenda-only mention cannot support/contradict |
| D | review-topic mention | review/topic text becomes value | topic noun survives residue filter | may create fake support | REVIEW_TOPIC, object=None | review-only mention abstains |
| E | explicit no-value | `no recorded value` still overlaps relation | negative/no-value semantics not first-class | may falsely retrieve | NO_VALUE_RECORDED | explicit absence always yields no support |
| F | wrong subject | correct relation/value for other entity | subject alignment may be incomplete | usually filtered, but anchor coverage is heuristic | require subject match | wrong subject cannot support |
| G | wrong relation/predicate | same subject, unrelated attribute | relation aliases can overlap or be too coarse | may confuse nearby relation | typed predicate slot | wrong predicate cannot support |
| H | wrong value | invalid/corrected value looks explicit | value validity is lexical | may support unless negative markers catch it | NEGATED_VALUE / invalid assertion | explicitly invalid value cannot support |
| I | partial proposition | subject/relation mentioned without object | residual text can create object | may falsely support | assertion requires explicit object/value slot | relation-only statement abstains |
| J | stale evidence | historical assertion answers current query | stale/current policy depends on markers | filtered when marker recognized | temporal scope first-class | stale-only current query abstains |
| K | current-vs-historical conflict | old and current values appear contradictory | proposition comparison may ignore scope | can false-contradict | compare only temporally comparable assertions | explicit current supersedes historical |
| L | temporal near-match | nearby date/daypart treated as exact | lexical temporal overlap insufficient | may support wrong period | typed temporal constraints | incompatible temporal scope abstains |
| M | unsupported inference | likely/probably becomes answer | uncertainty marker list is finite | may support unlisted inference wording | assertion status UNRESOLVED/UNKNOWN | inferential text cannot support definitive query |
| N | near duplicate | rephrased query gains residual token | echo detector threshold/blacklist finite | may create fake value | discourse classification before value extraction | paraphrase-only memory abstains |
| O | contradictory assertions | two explicit values for same slot | contradiction detection uses residue sets | may over/under detect | typed comparable value objects | true same-slot conflict -> CONTRADICTED |
| P | unresolved contradiction | conflict is discussed but not resolved | discourse may look like resolution | may select a proposition | UNRESOLVED blocks support | unresolved conflict abstains |
| Q | unsupported multi-hop composition | separate facts imply answer not stated | coverage graph can compose too freely | may synthesize unsupported support | no composition without explicit required assertion | indirect implication abstains |
| R | negative assertion | `X is not Y` exposes Y token | polarity not explicit in proposition object | may support Y | NEGATED_VALUE polarity | negated value never supports positive query |
| S | relation mention without value | attribute is discussed but no answer given | relation coverage plus residue can pass | may false retrieve | object/value required | relation-only discourse abstains |
| T | value mention without relation | answer-looking token appears elsewhere | ranking overlap can surface value | may pass if relation alias accidentally present | subject+predicate+object all required | bare value without predicate abstains |
| U | same subject / wrong attribute | entity matches strongly | subject anchor dominates lexical evidence | can retrieve wrong field | exact predicate compatibility | wrong field abstains |
| V | same attribute / wrong subject | relation/value look perfect | weak entity anchor | may retrieve other entity | explicit subject slot match | wrong entity abstains |

## Historical regression mapping

The following Candidate-v5 protected failures are historical diagnostics only:

- `validation-a-013`: wrong-relation distractor plus agenda/question discourse caused false abstention.
- `validation-a-014`: same mechanism for a different requested relation.
- `validation-n-045`: high-overlap no-value review/topic text caused false retrieval.
- `validation-n-046`: same high-overlap no-value mechanism for another relation.

If equivalent patterns are represented in Candidate-v6 development tests, they must be newly authored synthetic variants and labeled `HISTORICAL_FAILURE_REGRESSION_ONLY`; they are not fresh validation evidence.

## Development-failure lessons inherited from Candidate-v5

Candidate-v5 development history also established a methodological lesson: blacklist repair can become brittle. A query-echo failure survived an initial repair because punctuation altered stemming (`repeated:`). Candidate-v6 therefore should not solve the protected-validation mechanism by appending `agenda`, `review`, `topic`, and similar words to a larger `NON_VALUE_STEMS` set. The architecture must determine whether text occupies an assertion structure before extracting an object/value.

## Mechanism-to-design requirements

Candidate-v6 must satisfy all of the following before it can be considered a distinct method identity:

1. Discourse-role classification happens before evidence support is granted.
2. A support proposition requires subject, predicate, and explicit object/value.
3. Meta roles have `object_or_value = None` even if the text contains high lexical overlap.
4. Polarity and explicit absence are represented separately from positive assertion.
5. Temporal scope is part of comparability and conflict resolution.
6. Contradiction is only evaluated between comparable positive value assertions for the same subject/predicate/scope.
7. Candidate-v2 ranking is preserved unchanged when Candidate-v6 returns SUPPORTED.
8. Parse uncertainty fails closed.
