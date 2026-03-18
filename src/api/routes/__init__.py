from .core import router as core_router
from .auth import router as auth_router
from .files import router as files_router

__all__ = ["core_router", "auth_router", "files_router"]
