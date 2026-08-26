# Enua Charge for Home Assistant

Unofficial Home Assistant integration for [Enua Charge](https://www.enua.no) EV
chargers, built on Enua's public REST API (`https://api.enua.io`).

It signs in with your own Enua account using OAuth2 Authorization Code with
PKCE, so no client secret and no API key are stored in Home Assistant. Each
Home Assistant instance you install it on signs in as its own Enua user and
sees only the chargers that user owns or has been shared.

---

## Before you install

1. **Home Assistant 2025.2 or newer.**
2. **The `my` integration must be enabled.** It is part of `default_config`, so
   it is on unless you removed it. Home Assistant then uses
   `https://my.home-assistant.io/redirect/oauth` as the OAuth redirect, which
   is the URI Enua has registered. Without it, Home Assistant falls back to
   `<your external URL>/auth/external/callback`, which Enua has *not*
   registered, and sign-in will fail.
3. **The Enua account must be activated.** Sign in to the Enua app at least
   once with the account you are going to use. An account that has never signed
   in returns an empty list or `404` from the API even with a valid token.
4. **The account must own the chargers, or have them shared with it.**

### About the client ID

The client ID is built in — nothing to configure. Enua registered this
integration as a *public* client, which is exactly why PKCE is used instead of
a client secret, so the ID is not a secret and every install picks it up
automatically. You only sign in with your own Enua account.

---

## Installation

### HACS (recommended)

1. HACS → three-dot menu → **Custom repositories**.
2. Repository: `https://github.com/stianandre100/ha-enua`, category **Integration**.
3. Install **Enua Charge**, then restart Home Assistant.
4. **Settings → Devices & services → Add integration → Enua Charge**.
5. Sign in with your Enua account and approve access.

### Manual

Copy `custom_components/enua` into `<config>/custom_components/`, restart, then
add the integration from the UI.

---

## Installing on several Home Assistant instances

The same client ID and the same redirect URI work on every instance — work,
home, and anywhere else. Nothing per-instance needs to be registered with Enua,
because the redirect always goes through `my.home-assistant.io`, which then
bounces back to whichever Home Assistant started the flow.

What differs per instance is only *which Enua user signs in*:

| Instance | Signs in as | Sees |
| --- | --- | --- |
| Home | your personal Enua account | your own chargers |
| Work | the company's Enua account | chargers owned by or shared with it |
| Someone else's | their own Enua account | their own chargers |

If several instances should see the same chargers, share the chargers in the
Enua app with each account instead of reusing one login.

### One gotcha: My Home Assistant points at a single instance

The redirect goes through `my.home-assistant.io`, and that page remembers
**one** instance URL, stored in the browser you are signing in from. If it
points at a different Home Assistant than the one you are configuring, the
sign-in ends on `Invalid state. Is My Home Assistant configured to go to the
right instance?` and the flow fails.

Before adding the integration on a second or third instance, open
<https://my.home-assistant.io> in the browser you will use, click the pencil,
and set the URL to the instance you are about to configure. Point it back
afterwards if you use My links for another instance. Using a separate browser
profile per instance avoids the switching entirely.

---

## Entities

One device per charger.

### Sensors

| Entity | Notes |
| --- | --- |
| Vehicle state | Control pilot signal: not connected / connected / charging / error |
| Power | Calculated as `Σ (phase voltage × phase current)` — the API has no power field |
| Session energy | Energy delivered in the current session, converted from Wh to kWh |
| Current L1 / L2 / L3 | Ampere |
| Voltage L1 / L2 / L3 | Volt — disabled by default, enable if you want them |
| Charger max current | Diagnostic |
| Vehicle max current | Diagnostic |
| Cable lock, Wall mount lock | Diagnostic, locked / unlocked / error |

### Binary sensors

| Entity | Notes |
| --- | --- |
| Online | Connectivity, diagnostic |
| Cable connected | Control pilot state B or C |
| Charging | Control pilot state C |
| Active session | `hasActiveTransaction`, diagnostic |
| Problem | Control pilot error, or either lock reporting an error |

### Controls

| Entity | Endpoint |
| --- | --- |
| Charging (switch) | `POST /chargers/{id}/commands/start-charging` and `stop-charging`. Its state reflects whether current is actually flowing (control pilot state C), not the API's `hasActiveTransaction` |
| Max current (number) | `POST /chargers/{id}/commands/set-max-current`, 6–32 A |

> **Note on scopes.** The command endpoints work with the `Charger.Read` scope
> Enua grants - no separate write scope is needed. Verified against real
> hardware.

> **Note on `hasActiveTransaction`.** The API keeps this flag true after
> charging has been stopped, and even after the vehicle reports itself
> disconnected, so it is not a usable "is charging" signal. The *Charging*
> switch and binary sensor therefore use the control pilot state instead. The
> raw flag is exposed as the *Active session* binary sensor if you want it.

---

## Options

**Settings → Devices & services → Enua Charge → Configure.**

- **Polling interval** — default 30 seconds, allowed range 10–600. The Enua API
  is rate limited per IP address (`429` with error code `RateLimit`), so do not
  set it lower than you need. If several Home Assistant instances share one
  public IP, give them a higher interval.

The energy sensor works with the Home Assistant Energy dashboard: add
*Session energy* as an individual device under **Settings → Dashboards →
Energy**.

---

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| `no_url_available` when adding | The `my` integration is disabled and no external URL is set |
| Sign-in page shows a redirect URI error | The `my` integration is disabled, so Home Assistant sent an unregistered redirect URI |
| `Invalid state. Is My Home Assistant configured to go to the right instance?` | my.home-assistant.io points at a different instance - see the section above |
| Setup succeeds but "no chargers" | The Enua account has never signed in to the app, or owns no chargers |
| Entities go unavailable with `401` | Refresh failed — the integration will ask you to sign in again |
| Frequent `429` | Increase the polling interval |

Refresh tokens are valid for 90 days with rolling renewal, so an instance that
runs normally never needs a new sign-in. An instance offline for more than 90
days will need re-authentication.

To collect logs:

```yaml
logger:
  default: warning
  logs:
    custom_components.enua: debug
```

---

## Technical notes

- **Auth:** Azure AD B2C, policy `B2C_1_SignInIntegrations`, Authorization Code
  with PKCE (`S256`), public client, no secret.
- **Scopes:** `openid`, `offline_access`, and the Enua resource scope
  `https://enuab2c.onmicrosoft.com/7c1a5025-e720-4ef9-861b-6e33d001c330/Charger.Read`.
  The resource scope is also sent on refresh — without it, B2C issues the
  access token for our own client ID and the API answers `401`.
- **Token used:** the `access_token`, never the `id_token`. The `id_token` is
  only read locally (unverified) to derive a stable unique ID for the config
  entry.

---

## Disclaimer

Not affiliated with or endorsed by Enua AS. Built by
[Flekkerøy Elektro AS](https://www.flekkeroy-elektro.no) and released under the
MIT license so other Enua customers can use it.
