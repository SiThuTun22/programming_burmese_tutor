from __future__ import annotations

from advanced_alchemy.repository import SQLAlchemyAsyncRepository

from app.db.models import User


class UserRepo(SQLAlchemyAsyncRepository[User]):
    model_type = User
