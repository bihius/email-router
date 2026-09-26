"""Department choice from Laya, a non-autoregressive System One decision model.

Laya does not generate text. It answers a typed `choice` question whose options are
the catalog names, so the result is always a valid department plus a probability.
"""

import httpx

from app.config import laya_url
from app.departments import DEPARTMENTS, Department, get_department

QUESTION = {
    "department": {
        "type": "choice",
        "instructions": "Which department should handle the ticket in `body`?",
        "criteria": {item.name: item.description for item in DEPARTMENTS},
    }
}


def choose_department(text: str) -> tuple[Department, float]:
    """Return the chosen department and the probability Laya gave it."""
    response = httpx.post(
        f"{laya_url()}/v1/systemone",
        # The multilingual checkpoint reads Polish; the English one would guess.
        json={"state": {"body": text}, "questions": QUESTION, "model": "multilingual"},
        timeout=60,
    )
    response.raise_for_status()
    answer = response.json()["answers"]["department"]
    # `probabilities` is the distribution over options; Laya's `confidence` field is
    # an entropy score for the whole distribution, not the chance the choice is right.
    choice = answer["choice"]
    return get_department(choice), float(answer["probabilities"][choice])
