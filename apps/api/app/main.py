import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.modules.access.router import router as access_router
from app.modules.api import router
from app.modules.attachments.router import router as attachments_router
from app.modules.directory.router import router as directory_router
from app.modules.environment_assignments.router import router as assignment_router
from app.modules.governance.router import router as governance_router
from app.modules.operations.router import router as operations_router
from app.modules.permissions.router import router as permissions_router
from app.modules.platform.router import router as platform_router
from app.modules.system_fields.router import router as system_fields_router

app = FastAPI(title="Case Management API", version="0.1.0")
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(governance_router)
app.include_router(platform_router)
app.include_router(permissions_router)
app.include_router(access_router)
app.include_router(system_fields_router)
app.include_router(operations_router)
app.include_router(attachments_router)
app.include_router(directory_router)
app.include_router(assignment_router)
app.include_router(router)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.exception("Unexpected database integrity error on %s %s: %s",
                     request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=500,
        content={
            "code": "DATABASE_INTEGRITY_ERROR",
            "message": "לא ניתן היה להשלים את הפעולה עקב שגיאת תקינות נתונים.",
            "details": {},
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": "Validation failed", "errors": exc.errors()}),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
