from __future__ import annotations

import asyncio
import logging

from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin

from tutor.config import CORS_ORIGINS

from app.knowledge.store import ingest_knowledge
from app.lib.config import APP_VERSION, get_alchemy_config
from app.lib.security import jwt_auth
from app.routes.auth import auth_router
from app.routes.chat import chat_sessions_router, documents_router, messages_router
from app.routes.health import health

logger = logging.getLogger(__name__)

_ingest_task: asyncio.Task[None] | None = None


async def _run_startup_ingest() -> None:
    try:
        await ingest_knowledge()
    except Exception as error:
        logger.warning('Knowledge ingest on startup skipped: %s', error)


async def on_startup() -> None:
    global _ingest_task
    loop = asyncio.get_running_loop()
    task = loop.create_task(_run_startup_ingest())
    _ingest_task = task


def create_app() -> Litestar:
    alchemy_config = get_alchemy_config()
    alchemy_plugin = SQLAlchemyPlugin(config=alchemy_config)
    openapi_config = OpenAPIConfig(
        title='Agentic Academic Assistant',
        version=APP_VERSION,
        path='/',
        render_plugins=[ScalarRenderPlugin(path='/scalar')],
    )
    cors_config = CORSConfig(
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    app = Litestar(
        plugins=[alchemy_plugin],
        debug=True,
        route_handlers=[health, auth_router, chat_sessions_router, documents_router, messages_router],
        openapi_config=openapi_config,
        cors_config=cors_config,
        on_app_init=[jwt_auth.on_app_init],
        on_startup=[on_startup],
    )
    return app
