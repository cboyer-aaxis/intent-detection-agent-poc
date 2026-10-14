from functools import lru_cache

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from intent_agent.classifier import Classification, IntentClassifier
from intent_agent.routes import Route

app = FastAPI(title="Intent Detection Agent", version="0.1.0")


class ClassifyRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


@lru_cache
def get_classifier() -> IntentClassifier:
    return IntentClassifier()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/routes")
def routes() -> list[str]:
    return Route.labels()


@app.post("/classify", response_model=Classification)
def classify(req: ClassifyRequest, classifier: IntentClassifier = Depends(get_classifier)) -> Classification:
    return classifier.classify(req.query)
