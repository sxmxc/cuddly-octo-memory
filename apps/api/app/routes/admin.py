from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session

from app.config import Settings
from app.crud import (
    create_endpoint,
    delete_endpoint,
    get_endpoint,
    list_endpoints,
    update_endpoint,
)
from app.db import get_session
from app.schemas import EndpointCreate, EndpointRead, EndpointUpdate, PreviewRequest, PreviewResponse
from app.services.mock_generation import preview_from_schema
from app.services.schema_contract import normalize_schema_for_builder

router = APIRouter()
security = HTTPBasic()
settings = Settings()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)) -> None:
    if (
        credentials.username != settings.admin_username
        or credentials.password != settings.admin_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def _normalize_request_schema(schema: dict | None) -> dict:
    return normalize_schema_for_builder(schema or {}, property_name="root", include_mock=False)


def _normalize_response_schema(schema: dict | None) -> dict:
    return normalize_schema_for_builder(schema or {}, property_name="root", include_mock=True)


@router.get("/endpoints", response_model=list[EndpointRead])
def list_all_endpoints(session: Session = Depends(get_session), _: None = Depends(require_admin)):
    return list_endpoints(session)


@router.get("/endpoints/{endpoint_id}", response_model=EndpointRead)
def read_endpoint(endpoint_id: int, session: Session = Depends(get_session), _: None = Depends(require_admin)):
    endpoint = get_endpoint(session, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return endpoint


@router.post("/endpoints", response_model=EndpointRead, status_code=status.HTTP_201_CREATED)
def create_new_endpoint(endpoint_in: EndpointCreate, session: Session = Depends(get_session), _: None = Depends(require_admin)):
    payload = endpoint_in.model_copy(
        update={
            "request_schema": _normalize_request_schema(endpoint_in.request_schema),
            "response_schema": _normalize_response_schema(endpoint_in.response_schema),
        }
    )
    return create_endpoint(session, payload)


@router.put("/endpoints/{endpoint_id}", response_model=EndpointRead)
def update_existing_endpoint(
    endpoint_id: int,
    endpoint_in: EndpointUpdate,
    session: Session = Depends(get_session),
    _: None = Depends(require_admin),
):
    endpoint = get_endpoint(session, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    updates = endpoint_in.model_dump(exclude_unset=True)
    if "request_schema" in updates:
        updates["request_schema"] = _normalize_request_schema(endpoint_in.request_schema)
    if "response_schema" in updates:
        updates["response_schema"] = _normalize_response_schema(endpoint_in.response_schema)
    return update_endpoint(session, endpoint, EndpointUpdate(**updates))


@router.delete("/endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_endpoint(endpoint_id: int, session: Session = Depends(get_session), _: None = Depends(require_admin)):
    endpoint = get_endpoint(session, endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    delete_endpoint(session, endpoint)


@router.post("/endpoints/preview-response", response_model=PreviewResponse)
def preview_response(payload: PreviewRequest, _: None = Depends(require_admin)):
    return PreviewResponse(
        preview=preview_from_schema(
            _normalize_response_schema(payload.response_schema),
            seed_key=payload.seed_key,
            identity="preview",
        ),
    )
