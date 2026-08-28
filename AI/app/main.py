from fastapi import FastAPI

from app.api.agent_tools import router as agent_tools_router
from app.api.health import router as health_router
from app.api.workbooks import router as workbooks_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Excel AI Agent Service",
        description="Python service for Excel workbook analysis",
        version="0.1.0",
    )
    application.include_router(health_router)
    application.include_router(workbooks_router)
    application.include_router(agent_tools_router)
    return application


app = create_app()
