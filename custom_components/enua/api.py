"""API client for the Enua Charge REST API."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session

from .const import API_BASE

_LOGGER = logging.getLogger(__name__)


class EnuaApiError(HomeAssistantError):
    """Generic Enua API error."""

    def __init__(
        self, message: str, *, status: int | None = None, error_code: str | None = None
    ) -> None:
        """Initialise the error."""
        super().__init__(message)
        self.status = status
        self.error_code = error_code


class EnuaRateLimitError(EnuaApiError):
    """Raised when the API returns 429."""


class EnuaForbiddenError(EnuaApiError):
    """Raised when the token lacks the required scope for an operation."""


class EnuaNotFoundError(EnuaApiError):
    """Raised when a charger is not visible to the signed-in Enua user."""


class EnuaApiClient:
    """Thin async wrapper around the Enua REST API."""

    def __init__(self, session: ClientSession, oauth_session: OAuth2Session) -> None:
        """Initialise the client."""
        self._session = session
        self._oauth_session = oauth_session

    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> Any:
        """Perform an authenticated request and normalise errors."""
        await self._oauth_session.async_ensure_token_valid()
        token = self._oauth_session.token["access_token"]

        # The command endpoints take no documented body, but the API still
        # rejects a bodyless POST with 415 Unsupported Media Type. Always send
        # a JSON body on POST so the Content-Type header is present.
        payload = json
        if method == "POST" and payload is None:
            payload = {}

        url = f"{API_BASE}{path}"
        try:
            response = await self._session.request(
                method,
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
        except ClientError as err:
            raise EnuaApiError(f"Error talking to the Enua API: {err}") from err

        return await self._handle_response(response)

    async def _handle_response(self, response: ClientResponse) -> Any:
        """Turn an HTTP response into data or a typed exception."""
        if response.status in (200, 201, 202, 204):
            # The command endpoints answer with an empty body.
            try:
                text = await response.text()
            except ClientError as err:
                raise EnuaApiError(
                    f"Error reading the Enua API response: {err}"
                ) from err
            if not text.strip():
                return None
            return _parse_json(text)

        detail, error_code = await _problem_details(response)

        if response.status == 401:
            raise ConfigEntryAuthFailed(
                "The Enua API rejected the access token. Please sign in again."
            )
        if response.status == 403:
            raise EnuaForbiddenError(
                "The Enua API denied this operation. The granted scope may not "
                f"allow it. {detail}".strip(),
                status=403,
                error_code=error_code,
            )
        if response.status == 404:
            raise EnuaNotFoundError(
                "The Enua API returned 404. The signed-in Enua user may not own "
                f"or have been shared this charger. {detail}".strip(),
                status=404,
                error_code=error_code,
            )
        if response.status == 429:
            raise EnuaRateLimitError(
                f"Rate limited by the Enua API. {detail}".strip(),
                status=429,
                error_code=error_code,
            )
        raise EnuaApiError(
            f"Unexpected response {response.status} from the Enua API. "
            f"{detail}".strip(),
            status=response.status,
            error_code=error_code,
        )

    # -- Endpoints ---------------------------------------------------------

    async def async_get_chargers(self) -> list[dict[str, Any]]:
        """Return every charger the signed-in user has access to."""
        data = await self._request("GET", "/chargers")
        if data is None:
            return []
        if isinstance(data, dict):
            # Defensive: tolerate a wrapped collection if the API ever changes.
            for key in ("items", "data", "chargers", "results"):
                if isinstance(data.get(key), list):
                    return data[key]
            return [data]
        return list(data)

    async def async_get_charger(self, charger_id: str) -> dict[str, Any]:
        """Return a single charger."""
        return await self._request("GET", f"/chargers/{charger_id}")

    async def async_start_charging(self, charger_id: str) -> None:
        """Start a charging session."""
        await self._request("POST", f"/chargers/{charger_id}/commands/start-charging")

    async def async_stop_charging(self, charger_id: str) -> None:
        """Stop the running charging session."""
        await self._request("POST", f"/chargers/{charger_id}/commands/stop-charging")

    async def async_set_max_current(self, charger_id: str, max_current: int) -> None:
        """Set the maximum current the charger will deliver."""
        await self._request(
            "POST",
            f"/chargers/{charger_id}/commands/set-max-current",
            json={"maxCurrent": int(max_current)},
        )


def _parse_json(text: str) -> Any:
    """Parse a JSON body regardless of the content type the API sends."""
    try:
        return json.loads(text)
    except ValueError as err:
        raise EnuaApiError(
            f"Could not decode the Enua API response: {err}. Body: {text[:200]}"
        ) from err


async def _problem_details(response: ClientResponse) -> tuple[str, str | None]:
    """Extract RFC 7807 problem details from an error response."""
    try:
        payload = json.loads(await response.text())
    except (ValueError, ClientError):
        return "", None

    if not isinstance(payload, dict):
        return "", None

    error_code = payload.get("errorCode")
    parts = [str(payload[key]) for key in ("title", "detail") if payload.get(key)]
    if error_code:
        parts.append(f"(errorCode: {error_code})")
    return " ".join(parts), error_code
