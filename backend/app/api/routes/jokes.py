from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import RandomJoke
from app.services.joke_service import JokeFetchError, fetch_random_joke

router = APIRouter(prefix="/api/jokes", tags=["jokes"])


@router.get("/random", response_model=RandomJoke)
def get_random_joke() -> RandomJoke:
    try:
        return fetch_random_joke()
    except JokeFetchError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
