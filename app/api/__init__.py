"""API routers for the NE-ES School Management System.

Explicit static imports only (project architecture rule: no dynamic loading
loops). ``app.main`` wires the routers exported here.
"""

from app.api.finance import router as finance_router
from app.api.management import router as management_router

__all__ = ["finance_router", "management_router"]
