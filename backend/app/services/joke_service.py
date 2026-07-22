from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.models.schemas import RandomJoke

JOKE_API_URL = "https://official-joke-api.appspot.com/random_joke"
REQUEST_TIMEOUT_SECONDS = 5


class JokeFetchError(RuntimeError):
    pass


def fetch_random_joke() -> RandomJoke:
    request = Request(JOKE_API_URL, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise JokeFetchError("Joke service is unavailable right now. Please try again.")
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        raise JokeFetchError("Couldn't fetch a joke right now. Please try again.") from None

    setup = payload.get("setup")
    punchline = payload.get("punchline")
    if not isinstance(setup, str) or not setup.strip() or not isinstance(punchline, str) or not punchline.strip():
        raise JokeFetchError("Joke service returned an unexpected response. Please try again.")

    return RandomJoke(
        setup=setup.strip(),
        punchline=punchline.strip(),
        source="official-joke-api.appspot.com",
    )
