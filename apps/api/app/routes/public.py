from __future__ import annotations

import asyncio
import json
import random
import re
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Request, Response
from sqlmodel import Session

from app.crud import list_endpoints
from app.db import get_session
from app.services.mock_generation import preview_from_schema

router = APIRouter()


def _match_path_parameters(request_path: str, pattern: str) -> dict[str, str] | None:
    # Normalize
    request_path = request_path.rstrip("/") or "/"
    pattern = pattern.rstrip("/") or "/"

    parameter_names = re.findall(r"\{([^/}]+)\}", pattern)
    regex = re.sub(r"\{[^/]+\}", r"([^/]+)", pattern)
    regex = f"^{regex}$"
    match = re.match(regex, request_path)
    if not match:
        return None

    return {
        name: unquote(value)
        for name, value in zip(parameter_names, match.groups())
    }


def _pick_response(
    endpoint: Any,
    path_parameters: dict[str, str],
    query_parameters: dict[str, str],
    request_body: Any,
) -> Any:
    return preview_from_schema(
        endpoint.response_schema,
        path_parameters=path_parameters,
        query_parameters=query_parameters,
        request_body=request_body,
        seed_key=endpoint.seed_key,
        identity=f"endpoint:{endpoint.id}:{endpoint.method}:{endpoint.path}",
    )


async def _parse_json_request_body(request: Request) -> Any:
    body = await request.body()
    if not body:
        return None

    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


@router.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def catchall(full_path: str, request: Request, session: Session = Depends(get_session)) -> Response:
    request_path = request.url.path
    method = request.method.upper()

    endpoints = list_endpoints(session, limit=1000)
    match = None
    matched_path_parameters: dict[str, str] = {}
    for endpoint in endpoints:
        if not endpoint.enabled:
            continue
        if endpoint.method.upper() != method:
            continue
        path_parameters = _match_path_parameters(request_path, endpoint.path)
        if path_parameters is None:
            continue

        match = endpoint
        matched_path_parameters = path_parameters
        break

    if not match:
        return Response(status_code=404, content=json.dumps({"error": "Not found"}), media_type="application/json")

    # Simulate latency
    if match.latency_max_ms > 0:
        wait_ms = random.randint(match.latency_min_ms, match.latency_max_ms)
        await asyncio.sleep(wait_ms / 1000.0)

    # Simulate errors
    if match.error_rate > 0 and random.random() < match.error_rate:
        return Response(
            status_code=500,
            content=json.dumps({"error": "Simulated error"}),
            media_type="application/json",
        )

    request_body = await _parse_json_request_body(request)
    query_parameters = {key: value for key, value in request.query_params.items()}
    body = _pick_response(match, matched_path_parameters, query_parameters, request_body)
    return Response(
        status_code=match.success_status_code,
        content=json.dumps(body, default=str),
        media_type="application/json",
    )
