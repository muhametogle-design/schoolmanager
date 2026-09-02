"""API routers - all routers are explicitly registered here.

Registering routers with static imports keeps the module graph explicit and
avoids the circular-import/registration bugs caused by dynamic loader loops.
"""
from app.api import academics, auth, management, students

__all__ = ["auth", "students", "academics", "management"]
