from __future__ import annotations

import uuid

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.security.jwt import Token
from litestar.security.jwt.auth import JWTAuth
from pwdlib import PasswordHash

from app.db.models import User
from app.lib.config import get_alchemy_config, get_jwt_secret
from app.repositories.user import UserRepo

_password_hasher = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    hashed = _password_hasher.hash(plain)
    return hashed


def verify_password(plain: str, hashed: str) -> bool:
    is_valid = _password_hasher.verify(plain, hashed)
    return is_valid


async def user_from_authorization_header(connection: ASGIConnection) -> User:
    auth_header = connection.headers.get(jwt_auth.auth_header)
    if not auth_header:
        raise NotAuthorizedException(detail='Not authenticated')
    encoded_token = auth_header.partition(' ')[-1].strip()
    if not encoded_token:
        raise NotAuthorizedException(detail='Not authenticated')
    token = jwt_auth.token_cls.decode(
        encoded_token=encoded_token,
        secret=jwt_auth.token_secret,
        algorithm=jwt_auth.algorithm,
        audience=jwt_auth.accepted_audiences,
        issuer=jwt_auth.accepted_issuers,
        require_claims=jwt_auth.require_claims,
        verify_exp=jwt_auth.verify_expiry,
        verify_nbf=jwt_auth.verify_not_before,
        strict_audience=jwt_auth.strict_audience,
    )
    user = await retrieve_user_from_token(token, connection)
    if user is None:
        raise NotAuthorizedException(detail='Invalid token')
    return user


async def retrieve_user_from_token(token: Token, connection: ASGIConnection) -> User | None:
    _ = connection
    user_id = uuid.UUID(token.sub)
    alchemy_config = get_alchemy_config()
    session_maker = alchemy_config.create_session_maker()
    async with session_maker() as session:
        repo = UserRepo(session=session)
        user = await repo.get_one_or_none(id=user_id)
    if user is None:
        return None
    if not user.is_active:
        return None
    return user


jwt_auth = JWTAuth[User](
    retrieve_user_handler=retrieve_user_from_token,
    token_secret=get_jwt_secret(),
    exclude=[
        '/health',
        '^/$',
        '/scalar',
        '/openapi.json',
        '/api/auth/login',
        '/api/auth/register',
        '/api/auth/me',
    ],
)
