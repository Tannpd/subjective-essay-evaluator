# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
import typing
from dataclasses import dataclass


@allow_storage
@dataclass
class EvaluationRecord:
    submission_text: str
    rubric: str
    verdict: str
    score: bigint
    feedback: str


class Contract(gl.Contract):
    evaluations: TreeMap[str, EvaluationRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

    @gl.public.view
    def get_evaluation(self, eval_id: str) -> str:
        if eval_id not in self.evaluations:
            raise gl.vm.UserError("Evaluation record not found")
        
        record = self.evaluations[eval_id]
        return json.dumps({
            "id": eval_id,
            "submission_text": record.submission_text,
            "rubric": record.rubric,
            "verdict": record.verdict,
            "score": int(record.score),
            "feedback": record.feedback
        })

    @gl.public.view
    def get_total_evaluations(self) -> int:
        return int(self.next_id)
