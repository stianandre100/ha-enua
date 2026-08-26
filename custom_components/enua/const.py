"""Constants for the Enua Charge integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "enua"

MANUFACTURER: Final = "Enua"
MODEL: Final = "Enua Charge"

# ---------------------------------------------------------------------------
# OAuth2 / Azure AD B2C
# ---------------------------------------------------------------------------
# Enua has registered this integration as a *public* client (Authorization Code
# with PKCE, no client secret), so the client id is not a secret and is shipped
# with the integration. Every Home Assistant instance uses the same client id
# and each user signs in with their own Enua account.
CLIENT_ID: Final = "0ff3843e-7662-43e0-8523-a7351a2ee213"

B2C_TENANT: Final = "enuab2c.onmicrosoft.com"
B2C_POLICY: Final = "B2C_1_SignInIntegrations"
B2C_BASE: Final = f"https://enuab2c.b2clogin.com/{B2C_TENANT}/{B2C_POLICY}/oauth2/v2.0"

OAUTH2_AUTHORIZE: Final = f"{B2C_BASE}/authorize"
OAUTH2_TOKEN: Final = f"{B2C_BASE}/token"

API_SCOPE: Final = (
    "https://enuab2c.onmicrosoft.com/7c1a5025-e720-4ef9-861b-6e33d001c330/Charger.Read"
)
# offline_access is required to get a refresh token. The resource scope must be
# present or Azure AD B2C issues the access token for our own client id and the
# Enua API rejects it.
SCOPES: Final = ["openid", "offline_access", API_SCOPE]

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
API_BASE: Final = "https://api.enua.io"

DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=30)
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 600

CONF_SCAN_INTERVAL: Final = "scan_interval"

# Seconds to wait after a command before refreshing state, so the charger has
# had time to report the new state back to the cloud.
COMMAND_REFRESH_DELAY: Final = 5

# Ampere bounds accepted by the set-max-current command.
MIN_CURRENT: Final = 6
MAX_CURRENT: Final = 32

DATA_IMPLEMENTATION: Final = "oauth_implementation"

# ---------------------------------------------------------------------------
# Value maps
# ---------------------------------------------------------------------------
# IEC 61851 control pilot states reported by the charger.
VEHICLE_STATE_MAP: Final[dict[str, str]] = {
    "A": "not_connected",
    "B": "connected",
    "C": "charging",
    "E": "error",
}
VEHICLE_STATES: Final = ["not_connected", "connected", "charging", "error"]

LOCK_STATUS_MAP: Final[dict[str, str]] = {
    "Locked": "locked",
    "Unlocked": "unlocked",
    "Error": "error",
}
LOCK_STATES: Final = ["locked", "unlocked", "error"]
