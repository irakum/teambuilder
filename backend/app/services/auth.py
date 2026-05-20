import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.jwt import create_access_token
from app.models.user import User
from app.repositories.user import UserRepository


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = UserRepository(db)

    def get_google_auth_url(self) -> str:
        """Повертає URL для редіректу на Google."""
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{GOOGLE_AUTH_URL}?{query}"

    async def handle_callback(self, code: str) -> tuple[User, str]:
        """
        Обмінює code на токен Google, отримує дані користувача,
        створює або оновлює запис у БД, повертає (user, jwt_token).
        """
        # 1. Обмінюємо code на access_token
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            })
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data["access_token"]

            # 2. Отримуємо дані користувача
            user_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_resp.raise_for_status()
            user_info = user_resp.json()

        google_id = user_info["sub"]
        email = user_info["email"]
        name = user_info.get("name", email)
        avatar_url = user_info.get("picture")

        # 3. Знаходимо або створюємо користувача
        user = await self.repo.get_by_google_id(google_id)
        if user is None:
            user = await self.repo.create(google_id, email, name, avatar_url)
        else:
            user = await self.repo.update(user, name, avatar_url)

        # 4. Генеруємо JWT
        jwt_token = create_access_token(user.id, user.email)
        return user, jwt_token

    async def get_current_user(self, user_id: str) -> User | None:
        from uuid import UUID
        return await self.repo.get(UUID(user_id))
