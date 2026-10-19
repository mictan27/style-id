"""OpenAPI helpers. ``python -m styleid_api.openapi`` prints the document; the mobile
app generates its TypeScript client from it, so operation ids are stable camelCase
names derived from the handler function names (``list_closet_garments`` ->
``listClosetGarments``)."""

from __future__ import annotations

import json
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute


def camel_case(snake: str) -> str:
    head, *tail = [p for p in snake.split("_") if p]
    return head + "".join(p[:1].upper() + p[1:] for p in tail)


def operation_id_for(route: APIRoute) -> str:
    """``generate_unique_id_function`` hook: the handler name in camelCase."""
    return camel_case(route.name)


def operation_ids(app: FastAPI) -> dict[str, str]:
    """``{operationId: "METHOD /path"}`` for every operation; raises on a collision.

    Read from the generated document rather than ``app.routes`` so nested routers and
    FastAPI's internal route representation do not matter."""
    seen: dict[str, str] = {}
    doc = app.openapi()
    for path, operations in doc.get("paths", {}).items():
        for method, operation in operations.items():
            op_id = operation.get("operationId")
            if not op_id:
                raise ValueError(f"{method.upper()} {path} has no operationId")
            where = f"{method.upper()} {path}"
            if op_id in seen:
                raise ValueError(f"duplicate operationId {op_id!r}: {seen[op_id]} and {where}")
            seen[op_id] = where
    return seen


def openapi_document(app: FastAPI) -> dict[str, Any]:
    operation_ids(app)  # fail loudly on duplicates before handing the document out
    return app.openapi()


def main() -> None:
    from .main import create_app

    doc = openapi_document(create_app())
    json.dump(doc, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
