"""FastAPI web application for the AI Code Review Agent."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional

from config import settings
from core.orchestrator import ReviewOrchestrator
from demo.seed_memories import seed_demo_memories
from demo.sample_diffs import get_demo_pr_info, get_demo_files
from memory.hindsight_manager import HindsightMemoryManager

app = FastAPI(
    title="AI Code Review Agent",
    description="Code review agent with persistent Hindsight memory",
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

# Lazy-initialized orchestrator
_orchestrator: Optional[ReviewOrchestrator] = None


def get_orchestrator() -> ReviewOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ReviewOrchestrator()
    return _orchestrator


class ReviewRequest(BaseModel):
    pr_url: str
    use_memory: bool = True
    post_to_github: bool = False


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the main page."""
    return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "has_github": settings.has_github,
                "has_groq": settings.has_groq,
                "has_google": settings.has_google,
                "has_hindsight": settings.has_hindsight,
            },
        )


@app.post("/review")
def review_pr(request: ReviewRequest):
    """Review a GitHub PR."""
    try:
        orchestrator = get_orchestrator()

        if request.pr_url.strip().lower() == "demo":
            pr_info = get_demo_pr_info()
            files = get_demo_files()
            result = orchestrator.review_synthetic(
                pr_info=pr_info,
                files=files,
                use_memory=request.use_memory,
            )
        else:
            result = orchestrator.review_pr(
                pr_url=request.pr_url,
                use_memory=request.use_memory,
                post_to_github=request.post_to_github,
            )

        return JSONResponse(content=result.model_dump())
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.post("/demo/seed")
def seed_memories():
    """Seed historical team knowledge into Hindsight."""
    try:
        count = seed_demo_memories()
        return {"status": "success", "memories_stored": count}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.post("/demo/review-without-memory")
def demo_without_memory():
    """Run demo review WITHOUT memory."""
    try:
        orchestrator = get_orchestrator()
        pr_info = get_demo_pr_info()
        files = get_demo_files()
        result = orchestrator.review_synthetic(
            pr_info=pr_info, files=files, use_memory=False
        )
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/demo/review-with-memory")
def demo_with_memory():
    """Run demo review WITH memory."""
    try:
        orchestrator = get_orchestrator()
        pr_info = get_demo_pr_info()
        files = get_demo_files()
        result = orchestrator.review_synthetic(
            pr_info=pr_info, files=files, use_memory=True
        )
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "github": settings.has_github,
        "groq": settings.has_groq,
        "google": settings.has_google,
        "llm": settings.has_llm,
        "hindsight": settings.has_hindsight,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
