import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(
            id=str(user.id),
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
        )


@router.get("/google")
async def google_login():
    service = AuthService.__new__(AuthService)
    url = service.get_google_auth_url()
    return RedirectResponse(url)


@router.get("/callback")
async def google_callback(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        user, jwt_token = await service.handle_callback(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Помилка авторизації: {str(e)}")

    user_data = json.dumps({
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url or "",
    })
    params = f"token={jwt_token}&user={quote(user_data)}"
    return RedirectResponse(f"http://localhost:5173/login?{params}")


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.from_user(current_user)