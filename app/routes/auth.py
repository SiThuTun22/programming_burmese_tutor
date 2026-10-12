from __future__ import annotations

from litestar import Request, Router, get, post
from litestar.exceptions import ClientException, NotAuthorizedException

from app.db.models import User
from app.lib.security import hash_password, jwt_auth, user_from_authorization_header, verify_password
from app.repositories import UserRepo, provide_user_repo_dep
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserMe


@post('/register', status_code=201)
async def register(user_repo: UserRepo, data: RegisterRequest) -> UserMe:
    existing = await user_repo.get_one_or_none(email=data.email)
    if existing is not None:
        raise ClientException(status_code=409, detail='Email already registered')
    password_hash = hash_password(data.password)
    user = User(email=data.email, display_name=data.display_name, password_hash=password_hash, is_active=True)
    created = await user_repo.add(user)
    user_me = UserMe(id=created.id, email=created.email, display_name=created.display_name, is_active=created.is_active)
    return user_me


@post('/login', status_code=200)
async def login(user_repo: UserRepo, data: LoginRequest) -> TokenResponse:
    user = await user_repo.get_one_or_none(email=data.email)
    if user is None:
        raise NotAuthorizedException(detail='Invalid email or password')
    is_valid = verify_password(data.password, user.password_hash)
    if not is_valid:
        raise NotAuthorizedException(detail='Invalid email or password')
    if not user.is_active:
        raise NotAuthorizedException(detail='Account is inactive')
    access_token = jwt_auth.create_token(identifier=str(user.id))
    token_response = TokenResponse(access_token=access_token, token_type='bearer')
    return token_response


@get('/me')
async def get_me(request: Request) -> UserMe:
    user = await user_from_authorization_header(request)
    user_me = UserMe(id=user.id, email=user.email, display_name=user.display_name, is_active=user.is_active)
    return user_me


auth_router = Router(
    path='/api/auth',
    route_handlers=[register, login, get_me],
    dependencies={'user_repo': provide_user_repo_dep},
)
