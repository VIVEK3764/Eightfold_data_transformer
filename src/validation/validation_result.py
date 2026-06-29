from typing import List

class ValidationResult:
    """
    Structured validation result representing validity and errors list.
    """
    def __init__(self, valid: bool = True, errors: List[str] = None):
        self.valid = valid
        self.errors = errors if errors is not None else []

    def add_error(self, error_msg: str):
        self.valid = False
        self.errors.append(error_msg)

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors
        }
