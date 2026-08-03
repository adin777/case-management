from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.modules.api import router
from app.modules.attachments.router import router as attachments_router
from app.modules.governance.router import router as governance_router
from app.modules.operations.router import router as operations_router
from app.modules.permissions.router import router as permissions_router
from app.modules.platform.router import router as platform_router

app = FastAPI(title="Case Management API", version="0.1.0")
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
app.include_router(operations_router)
app.include_router(attachments_router)
app.include_router(router)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_request: Request, _exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409, content={"detail": "A record with the same unique value already exists"}
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
