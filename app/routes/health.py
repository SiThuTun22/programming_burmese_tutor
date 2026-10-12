from litestar import get

from app.lib.config import APP_VERSION
from app.schemas import HealthResponse


@get('/health')
async def health() -> HealthResponse:
    response = HealthResponse(status='ok', version=APP_VERSION)
    return response
