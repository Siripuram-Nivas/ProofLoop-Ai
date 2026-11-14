from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from ..config import settings


ACTION_CREATE_VERIFICATION_JOB = (
    "fz_af_30a013b9_230d_4c3c_86d3_a26d9e5acd1e"
)

LOGIN_MUTATION = """
mutation Login($email: String!, $password: String!, $register: Boolean!) {
  authenticateWithEmail(email: $email, password: $password, register: $register) {
    account { id email username permissionRoles }
    jwt { token }
  }
}
"""

CREATE_JOB_MUTATION = f"""
mutation CreateVerificationJob(
  $title: String
  $workspace_id: bigint
  $input_type: String
  $original_text: String
  $original_url: String
  $uploaded_file_url: String
) {{
  {ACTION_CREATE_VERIFICATION_JOB}(
    title: $title
    workspace_id: $workspace_id
    input_type: $input_type
    original_text: $original_text
    original_url: $original_url
    uploaded_file_url: $uploaded_file_url
  )
}}
"""

JOB_FIELDS = """
  id title input_type status current_stage error_message
  original_text original_url uploaded_file_url
  created_at updated_at started_at completed_at
  workspace_id created_by_id metadata
  claims {
    id claim_text normalized_text category verification_status claim_order
    entities context_notes created_at updated_at
    evidence_items {
      id stance exact_excerpt locator explanation relevance_score metadata
      claim_id source_id
      source { id url title publisher domain source_type publication_date retrieved_at access_status }
    }
  }
  sources {
    id url title publisher domain source_type publication_date retrieved_at
    access_status metadata
  }
  contradictions {
    id summary severity status explanation resolution_note
    claim_a_id claim_b_id evidence_a_id evidence_b_id metadata
  }
  proof_reports {
    id version overall_status summary report_content limitations generated_at is_current
  }
  audit_logs { id action entity_type entity_id details occurred_at actor_id }
"""

LIST_JOB_SUMMARIES_QUERY = """
query ListJobSummaries($where: verification_job_bool_exp!, $limit: Int!, $offset: Int!) {
  verification_job(
    where: $where
    order_by: {created_at: desc}
    limit: $limit
    offset: $offset
  ) {
    id title input_type status current_stage error_message
    created_at updated_at started_at completed_at
    workspace_id created_by_id metadata
  }
  verification_job_aggregate(where: $where) { aggregate { count } }
}
"""

GET_JOB_QUERY = f"""
query GetJob($where: verification_job_bool_exp!) {{
  verification_job(where: $where, limit: 1) {{
    {JOB_FIELDS}
  }}
}}
"""

LIST_WORKSPACES_QUERY = """
query ListWorkspaces($where: workspace_bool_exp!) {
  workspace(where: $where, order_by: {created_at: asc}) {
    id name slug status owner_id
  }
}
"""


class MomenError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 502,
        details: Optional[list] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details or []


def _graphql_error(payload: dict) -> Optional[MomenError]:
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        first = errors[0] if isinstance(errors[0], dict) else {}
        message = str(first.get("message") or "Momen request failed.")[:500]
        extension_code = str((first.get("extensions") or {}).get("code") or "")
        details = [
            str(item.get("message"))[:300]
            for item in errors
            if isinstance(item, dict) and item.get("message")
        ]
        return _classify(message, extension_code, details)
    error = payload.get("error")
    if isinstance(error, str) and error:
        return _classify(error[:500], "", [error[:300]])
    return None


def _classify(message: str, extension_code: str, details: list) -> MomenError:
    lowered = message.lower()
    if "incorrect email or password" in lowered or "entity_does_not_exist" in lowered:
        return MomenError(
            "invalid_credentials", "Email or password is incorrect.", 401, details
        )
    if "not owned by the caller" in lowered or "workspace not found" in lowered:
        return MomenError(
            "workspace_forbidden",
            "That workspace does not exist or is not owned by your Momen account.",
            403,
            details,
        )
    if (
        "must not be empty" in lowered
        or "must be a positive id" in lowered
        or "must be text, url, pdf, or image" in lowered
        or "non-whitespace content" in lowered
    ):
        return MomenError("invalid_input", message, 422, details)
    if "jwt expired" in lowered or "token expired" in lowered or "jwt_expired" in lowered:
        return MomenError(
            "momen_session_expired",
            "Your Momen session expired. Reconnect your Momen account.",
            401,
            details,
        )
    if (
        "unauthenticated" in lowered
        or "authentication required" in lowered
        or "not authenticated" in lowered
        or "login required" in lowered
    ):
        return MomenError(
            "momen_not_authenticated",
            "Momen rejected the session. Reconnect your Momen account.",
            401,
            details,
        )
    if (
        "permission" in lowered
        or "not authorized" in lowered
        or "unauthorized" in lowered
        or extension_code in {"FORBIDDEN", "UNAUTHORIZED", "PERMISSION_DENIED"}
    ):
        return MomenError(
            "permission_denied",
            "Your Momen account is not allowed to perform that action.",
            403,
            details,
        )
    return MomenError(
        "momen_graphql_error",
        "Momen rejected the request. Try again or check the server logs.",
        502,
        details,
    )


def graphql(
    query: str,
    variables: Optional[dict[str, Any]] = None,
    *,
    token: Optional[str] = None,
    admin: bool = False,
    transport: Optional[httpx.BaseTransport] = None,
) -> dict:
    """POST one operation to the Momen Runtime GraphQL endpoint."""
    if not settings.momen_graphql_url:
        raise MomenError(
            "momen_not_configured", "MOMEN_GRAPHQL_URL is not configured.", 503
        )
    bearer = token or (settings.momen_admin_token if admin else "")
    if admin and not bearer:
        raise MomenError(
            "momen_read_unavailable",
            "Momen read access is not configured on the server (MOMEN_ADMIN_TOKEN).",
            503,
        )
    headers = {"Content-Type": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"

    try:
        with httpx.Client(
            timeout=settings.momen_timeout_seconds, transport=transport
        ) as http:
            response = http.post(
                settings.momen_graphql_url,
                json={"query": query, "variables": variables or {}},
                headers=headers,
            )
    except httpx.TimeoutException as exc:
        raise MomenError(
            "momen_timeout", "Momen did not respond in time. Try again.", 504
        ) from exc
    except httpx.HTTPError as exc:
        raise MomenError(
            "momen_unavailable", "Momen is unreachable right now.", 502
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise MomenError(
            "momen_invalid_response", "Momen returned an unreadable response.", 502
        ) from exc
    if not isinstance(payload, dict):
        raise MomenError(
            "momen_invalid_response", "Momen returned an unexpected response.", 502
        )

    error = _graphql_error(payload)
    if error:
        raise error
    if response.status_code >= 400:
        raise MomenError(
            "momen_http_error",
            f"Momen rejected the request ({response.status_code}).",
            502,
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise MomenError(
            "momen_invalid_response", "Momen returned no data payload.", 502
        )
    return data


def authenticate(email: str, password: str) -> dict:
    data = graphql(
        LOGIN_MUTATION,
        {"email": email.strip().lower(), "password": password, "register": False},
    )
    result = data.get("authenticateWithEmail")
    if not isinstance(result, dict):
        raise MomenError(
            "momen_output_missing", "Momen did not return a login result.", 502
        )
    account = result.get("account")
    token = (result.get("jwt") or {}).get("token")
    if not isinstance(account, dict) or not account.get("id") or not token:
        raise MomenError(
            "momen_output_missing",
            "Momen did not return a complete account and session token.",
            502,
        )
    return {"account": account, "token": token}


def _jsonb(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def create_verification_job(
    token: str,
    *,
    title: Optional[str],
    workspace_id: int,
    input_type: str,
    original_text: Optional[str] = None,
    original_url: Optional[str] = None,
    uploaded_file_url: Optional[str] = None,
) -> dict:
    data = graphql(
        CREATE_JOB_MUTATION,
        {
            "title": title,
            "workspace_id": workspace_id,
            "input_type": input_type,
            "original_text": original_text,
            "original_url": original_url,
            "uploaded_file_url": uploaded_file_url,
        },
        token=token,
    )
    result = _jsonb(data.get(ACTION_CREATE_VERIFICATION_JOB))
    if not isinstance(result, dict) or result.get("verification_job_id") is None:
        raise MomenError(
            "momen_output_missing",
            "Momen did not return a verification job id.",
            502,
        )
    return result


def list_workspaces(account_id: int) -> list[dict]:
    data = graphql(
        LIST_WORKSPACES_QUERY,
        {"where": {"owner_id": {"_eq": account_id}}},
        admin=True,
    )
    return data.get("workspace") or []


def list_jobs(account_id: int, limit: int = 20, offset: int = 0) -> dict:
    where = {
        "created_by_id": {"_eq": account_id},
        "workspace": {"owner_id": {"_eq": account_id}},
    }
    data = graphql(
        LIST_JOB_SUMMARIES_QUERY,
        {"where": where, "limit": limit, "offset": offset},
        admin=True,
    )
    total = (
        ((data.get("verification_job_aggregate") or {}).get("aggregate") or {}).get(
            "count"
        )
        or 0
    )
    return {"items": data.get("verification_job") or [], "total": total}


def get_job(account_id: int, job_id: int) -> Optional[dict]:
    where = {
        "id": {"_eq": job_id},
        "created_by_id": {"_eq": account_id},
        "workspace": {"owner_id": {"_eq": account_id}},
    }
    data = graphql(GET_JOB_QUERY, {"where": where}, admin=True)
    jobs = data.get("verification_job") or []
    return jobs[0] if jobs else None
