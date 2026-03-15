from __future__ import annotations

from fastapi import HTTPException, status


PRIVATE_ADMIN_PREFIX = "/api/admin"
PUBLIC_REFERENCE_PATH = "/api/reference.json"
PUBLIC_ROOT_PATH = "/api"


def normalize_endpoint_method(method: str) -> str:
    return method.strip().upper()


def normalize_endpoint_path(path: str) -> str:
    normalized_path = f"/{path.strip().lstrip('/')}"
    if len(normalized_path) > 1:
        normalized_path = normalized_path.rstrip("/")
    return normalized_path or "/"


def validate_endpoint_path(path: str) -> None:
    if not path.startswith("/api"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Public mock routes must live under /api.",
        )

    if path == PUBLIC_ROOT_PATH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The /api root is reserved for the public landing page.",
        )

    if path == PUBLIC_REFERENCE_PATH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The /api/reference.json path is reserved for the public reference feed.",
        )

    if path == PRIVATE_ADMIN_PREFIX or path.startswith(f"{PRIVATE_ADMIN_PREFIX}/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The /api/admin namespace is reserved for private admin routes.",
        )
