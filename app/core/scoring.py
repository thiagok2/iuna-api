"""
Scoring weights and valid action constants.
"""

SCORE_WEIGHTS: dict[str, float] = {
    "click": 1.0,
    "add_to_chat": 3.0,
    "download": 2.0,
    "share": 2.0,
}

VALID_ACTIONS: frozenset[str] = frozenset(SCORE_WEIGHTS.keys())
