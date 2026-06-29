from pydantic import BaseModel

class MatchResult:
    """
    Lightweight model representing the result of comparing two candidate records.
    """
    def __init__(self, matched: bool, score: float, reason: str):
        self.matched = matched
        self.score = score
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "matched": self.matched,
            "score": self.score,
            "reason": self.reason
        }
