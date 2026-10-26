"""Track B assessment service."""

__version__ = "0.1.0"


def main() -> None:
    """Run the API with uvicorn (entry point: `uv run assessment`)."""
    import uvicorn

    from assessment.config import settings

    uvicorn.run(
        "assessment.main:app", host=settings.host, port=settings.port, reload=settings.debug
    )
