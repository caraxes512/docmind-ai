"""Health check endpoint. Deliberately unauthenticated and dependency-free
(no DB/Redis/Qdrant ping) — this answers "is the process alive and serving
requests," which is what container orchestrators need for liveness. A
deeper readiness check (DB reachable, migrations current) is a distinct
concern and would be a separate /health/ready endpoint if this app grows
enough infrastructure to need the distinction (e.g. behind a load balancer
that should stop routing traffic to a instance whose DB connection died,
even though the process itself is still up).
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
