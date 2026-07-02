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
    verdict: str  # EXCELLENT | SATISFACTORY | NEEDS_IMPROVEMENT
    score: bigint
    feedback: str


def _normalize_verdict(verdict: str) -> str:
    v = str(verdict or "").strip().upper()
    if "EXCELLENT" in v:
        return "EXCELLENT"
    if "SATISFACTORY" in v:
        return "SATISFACTORY"
    if "NEEDS_IMPROVEMENT" in v or "IMPROVE" in v or "NEEDS" in v:
        return "NEEDS_IMPROVEMENT"
    return "NEEDS_IMPROVEMENT"


def _normalize_score(score_val: typing.Any) -> int:
    try:
        s = int(score_val)
    except Exception:
        s = 0
    return max(0, min(100, s))


class Contract(gl.Contract):
    evaluations: TreeMap[str, EvaluationRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

    @gl.public.write
    def evaluate_submission(self, submission_text: str, rubric: str) -> None:
        if not submission_text or not submission_text.strip():
            raise gl.vm.UserError("submission_text must not be empty")
        if not rubric or not rubric.strip():
            raise gl.vm.UserError("rubric must not be empty")

        sub_clean = submission_text.strip()
        rub_clean = rubric.strip()

        def leader_fn() -> str:
            prompt = f"""You are an expert educational evaluator grading a student's subjective text submission.
Evaluate the student's submission text using the provided rubric.

STUDENT SUBMISSION:
---
{sub_clean}
---

GRADING RUBRIC:
---
{rub_clean}
---

You must assign:
1. A verdict: Choose EXACTLY one of: "EXCELLENT", "SATISFACTORY", or "NEEDS_IMPROVEMENT".
2. A score: Choose an integer from 0 to 100.
3. Feedback: Provide a constructive, educational feedback comment (maximum 300 characters).

Return ONLY a JSON object with the following schema:
{{
  "verdict": "EXCELLENT" | "SATISFACTORY" | "NEEDS_IMPROVEMENT",
  "score": <integer 0-100>,
  "feedback": "string explaining the rating"
}}"""
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(res, dict):
                res = {}
            
            # Normalize fields to guarantee structured consistency
            verdict = _normalize_verdict(res.get("verdict", "NEEDS_IMPROVEMENT"))
            score = _normalize_score(res.get("score", 0))
            feedback = str(res.get("feedback", "")).strip()[:300]
            if not feedback:
                feedback = "No feedback provided."

            return json.dumps({
                "verdict": verdict,
                "score": score,
                "feedback": feedback
            }, sort_keys=True)

        def validator_fn(leader_res: typing.Any) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leader_res.calldata)
            except Exception:
                return False

            # Extract leader fields
            leader_verdict = _normalize_verdict(leader_data.get("verdict"))
            leader_score = _normalize_score(leader_data.get("score"))

            # Run validator's own local LLM judgment
            try:
                mine_json = leader_fn()
                mine_data = json.loads(mine_json)
            except Exception:
                return False

            mine_verdict = _normalize_verdict(mine_data.get("verdict"))
            mine_score = _normalize_score(mine_data.get("score"))

            # Consensus logic:
            # 1. Verdict category must match exactly
            if leader_verdict != mine_verdict:
                return False

            # 2. Score must be within a close band (absolute difference <= 10)
            if abs(leader_score - mine_score) > 10:
                return False

            return True

        # Run non-deterministic consensus logic
        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        payload = json.loads(raw_result)

        # Store agreed results
        rid = str(self.next_id)
        self.evaluations[rid] = EvaluationRecord(
            submission_text=sub_clean,
            rubric=rub_clean,
            verdict=_normalize_verdict(payload.get("verdict")),
            score=bigint(_normalize_score(payload.get("score"))),
            feedback=str(payload.get("feedback")).strip()[:300]
        )
        self.next_id = self.next_id + bigint(1)

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
