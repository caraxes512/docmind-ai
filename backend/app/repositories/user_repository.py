import uuid
from typing import Optional

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_github_id(self, github_id: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.github_id == github_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        email: str,
        hashed_password: Optional[str],
        full_name: Optional[str] = None,
    ) -> User:
        user = User(email=email, hashed_password=hashed_password, full_name=full_name)
        self.db.add(user)
        await self.db.flush()
        return user
