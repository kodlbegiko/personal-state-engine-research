from __future__ import annotations

from datetime import datetime

from .commitments import CommitmentLedger
from .models import Commitment, MemoryRecord
from .proactive import ProactiveController
from .retrieval import RetrievalController
from .store import MemoryStore
from .verification import ActionResult, VerificationLoop


class PersonalStateEngine:
    def __init__(self) -> None:
        self.memories = MemoryStore()
        self.retrieval = RetrievalController(self.memories)
        self.commitments = CommitmentLedger()
        self.proactive = ProactiveController()
        self.verification = VerificationLoop()

    def remember(self, record: MemoryRecord):
        return self.memories.write(record)

    def context(
        self,
        *,
        user_id: str,
        query: str,
        at: datetime | None = None,
        goal_tags: tuple[str, ...] = (),
        project: str | None = None,
        token_budget: int = 512,
    ):
        return self.retrieval.retrieve(
            user_id=user_id,
            query=query,
            at=at,
            goal_tags=goal_tags,
            project=project,
            token_budget=token_budget,
        )

    def add_commitment(self, commitment: Commitment) -> Commitment:
        return self.commitments.add(commitment)

    def check_commitment(self, commitment_id: str, **kwargs):
        item = self.commitments.get(commitment_id)
        if item is None:
            raise KeyError(commitment_id)
        return self.proactive.decide(item, **kwargs)

    def verify_action(self, result: ActionResult):
        return self.verification.verify(result)
