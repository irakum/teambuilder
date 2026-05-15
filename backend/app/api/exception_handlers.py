from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import NotFoundError, ForbiddenError, BusinessRuleError


def register_exception_handlers(app: FastAPI) -> None:
    """Реєструє глобальні обробники виключень сервісного шару."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, exc: ForbiddenError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(BusinessRuleError)
    async def business_rule_handler(request: Request, exc: BusinessRuleError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
