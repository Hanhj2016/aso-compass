from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


def fetch(url: str, origin: str | None = None) -> Response:
    headers = {"Origin": origin} if origin else {}
    request = Request(url, headers=headers)
    with urlopen(request, timeout=90) as response:  # noqa: S310 - operator-supplied URLs
        return Response(
            status=response.status,
            headers={key.lower(): value for key, value in response.headers.items()},
            body=response.read(),
        )


def require_json(response: Response, expected_status: str) -> dict[str, Any]:
    if response.status != 200:
        raise RuntimeError(f"Expected HTTP 200, received {response.status}")
    payload = json.loads(response.body)
    if not isinstance(payload, dict) or payload.get("status") != expected_status:
        raise RuntimeError(f"Unexpected health response; expected status={expected_status!r}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only deployed ASO Compass smoke checks")
    parser.add_argument("--api-url", required=True, help="Render API origin")
    parser.add_argument("--frontend-url", required=True, help="Hugging Face Space origin")
    parser.add_argument("--allowed-origin", required=True, help="Expected allowed browser origin")
    parser.add_argument(
        "--rejected-origin",
        default="https://unlisted-origin.invalid",
        help="Origin that must not receive a CORS allow header",
    )
    args = parser.parse_args()
    api_url = args.api_url.rstrip("/")
    frontend_url = args.frontend_url.rstrip("/")

    live = require_json(fetch(f"{api_url}/health/live"), "ok")
    require_json(fetch(f"{api_url}/health/ready"), "ready")

    allowed = fetch(f"{api_url}/api/v1/config/public", args.allowed_origin)
    config = json.loads(allowed.body)
    if allowed.headers.get("access-control-allow-origin") != args.allowed_origin:
        raise RuntimeError("Configured frontend origin was not accepted by CORS")
    rejected = fetch(f"{api_url}/api/v1/config/public", args.rejected_origin)
    if "access-control-allow-origin" in rejected.headers:
        raise RuntimeError("An unlisted origin unexpectedly received a CORS allow header")

    forbidden_public_keys = {
        "database_url",
        "openai_api_key",
        "supabase_secret_key",
        "supabase_service_role_key",
    }
    leaked_keys = forbidden_public_keys.intersection(str(key).lower() for key in config)
    if leaked_keys:
        raise RuntimeError("Public configuration exposed a forbidden key name")

    frontend = fetch(frontend_url)
    if frontend.status != 200 or b"ASO Compass" not in frontend.body:
        raise RuntimeError("Frontend did not return the expected ASO Compass document")

    print(
        "Deployment smoke passed: "
        f"API {live.get('version', 'unknown')}, database ready, CORS restricted, frontend reachable."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
