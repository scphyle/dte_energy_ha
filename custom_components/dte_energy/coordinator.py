import asyncio
import base64
import json
import logging
from datetime import datetime, timedelta, timezone

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from custom_components.dte_energy.const import APIM_SUBSCRIPTION_KEY
from custom_components.dte_energy.const import (
    DOMAIN,
    SCAN_INTERVAL_MINUTES,
    TOKEN_REFRESH_BUFFER_SECONDS,
    URL_TOKEN_REFRESH,
    URL_USER_DETAILS,
    URL_BILL_DATA,
    URL_USAGE,
)

_LOGGER = logging.getLogger(__name__)


class DTEDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, web_security_token: str, account_number: str):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=SCAN_INTERVAL_MINUTES),
        )
        self.account_number = account_number
        self._web_security_token = web_security_token
        self._web_token_expiry: datetime | None = None
        self._bearer_token: str | None = None
        self._bearer_token_expiry: datetime | None = None

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    def _is_web_token_expired(self) -> bool:
        if not self._web_token_expiry:
            return True
        buffer = timedelta(seconds=TOKEN_REFRESH_BUFFER_SECONDS)
        return datetime.now(timezone.utc) >= (self._web_token_expiry - buffer)

    def _is_bearer_token_expired(self) -> bool:
        if not self._bearer_token_expiry:
            return True
        buffer = timedelta(seconds=TOKEN_REFRESH_BUFFER_SECONDS)
        return datetime.now(timezone.utc) >= (self._bearer_token_expiry - buffer)

    def _decode_bearer_expiry(self, jwt: str) -> datetime:
        """Decode exp claim from JWT payload."""
        payload_b64 = jwt.split(".")[1]
        # Add padding if needed
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.b64decode(payload_b64).decode("utf-8"))
        return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    async def _refresh_web_security_token(self, session: aiohttp.ClientSession) -> None:
        """Hit /api/tokenRefresh to get a new webSecurityToken."""
        _LOGGER.debug("Refreshing webSecurityToken")
        async with session.get(
            URL_TOKEN_REFRESH,
            cookies={"webSecurityToken": self._web_security_token},
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        self._web_security_token = data["webSecurityToken"]
        self._web_token_expiry = datetime.fromisoformat(
            data["webSecurityTokenExpiry"].replace("Z", "+00:00")
        )
        _LOGGER.debug("webSecurityToken refreshed, expires: %s", self._web_token_expiry)

    async def _refresh_bearer_token(self, session: aiohttp.ClientSession) -> None:
        """Hit /api/getUserDetails to get a bearer token."""
        _LOGGER.debug("Fetching bearer token via getUserDetails")
        async with session.get(
            URL_USER_DETAILS,
            cookies={"webSecurityToken": self._web_security_token},
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

        # Log the full response once so we can confirm the bearer token field name
        _LOGGER.debug("getUserDetails response: %s", data)

        # Adjust field name below if needed once you see the debug log
        self._bearer_token = data.get("bearerToken") or data.get("access_token") or data.get("token")
        if not self._bearer_token:
            raise UpdateFailed(f"Could not find bearer token in getUserDetails response: {data}")

        self._bearer_token_expiry = self._decode_bearer_expiry(self._bearer_token)
        _LOGGER.debug("Bearer token refreshed, expires: %s", self._bearer_token_expiry)

    async def _fetch_bill_data(self, session: aiohttp.ClientSession) -> dict:
        """Fetch current bill data."""
        async with session.get(
            URL_BILL_DATA,
            cookies={"webSecurityToken": self._web_security_token},
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def _fetch_usage_data(self, session: aiohttp.ClientSession) -> dict:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        url = URL_USAGE.format(account_number=self.account_number)
        async with session.get(
                url,
                headers={
                    "Authorization": f"Bearer {self._bearer_token}",
                    "ocp-apim-subscription-key": APIM_SUBSCRIPTION_KEY,
                },
                params={
                    "startDate": start_date.strftime("%Y-%m-%d"),
                    "endDate": end_date.strftime("%Y-%m-%d"),
                },
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    # ------------------------------------------------------------------
    # Main update loop
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: Refresh webSecurityToken if needed
                if self._is_web_token_expired():
                    await self._refresh_web_security_token(session)

                # Step 2: Refresh bearer token if needed
                if self._is_bearer_token_expired():
                    await self._refresh_bearer_token(session)

                # Step 3: Fetch data
                bill_data, usage_data = await asyncio.gather(
                    self._fetch_bill_data(session),
                    self._fetch_usage_data(session),
                )

            return self._parse_data(bill_data, usage_data)

        except aiohttp.ClientResponseError as err:
            raise UpdateFailed(f"DTE API error: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    # ------------------------------------------------------------------
    # Data parsing
    # ------------------------------------------------------------------

    def _parse_data(self, bill_data: dict, usage_data: dict) -> dict:
        account = bill_data["currentBillData"]["accounts"][0]
        summary = account["accountSummary"]
        charges = summary["summaryOfCharges"]["charges"]

        # Group usage entries by day, find most recent day with non-null data
        days: dict = {}
        for entry in usage_data.get("usage", []):
            if entry.get("usage") is None:
                continue
            day = entry["day"]
            if day not in days:
                days[day] = {"peak": 0.0, "offpeak": 0.0, "rate_category": None}
            days[day]["rate_category"] = entry.get("rateCategory")
            if entry["timeOfDay"] == "PEAK":
                days[day]["peak"] += entry["usage"]
            elif entry["timeOfDay"] == "OFFPEAK":
                days[day]["offpeak"] += entry["usage"]

        # Pick the most recent day that has data
        latest_day = None
        latest_data = {"peak": 0.0, "offpeak": 0.0, "rate_category": None}
        if days:
            latest_day = max(days.keys())
            latest_data = days[latest_day]

        peak_kwh = latest_data["peak"]
        offpeak_kwh = latest_data["offpeak"]
        rate_category = latest_data["rate_category"]

        # Parse last payment from status bar message
        last_payment = 0.0
        for msg in account.get("statusBarMessages", []):
            if "payment" in msg.get("text", "").lower() and "$" in msg.get("text", ""):
                try:
                    last_payment = float(
                        msg["text"].split("$")[-1].split(" ")[0].replace(",", "")
                    )
                except ValueError:
                    pass
                break

        return {
            # Bill data
            "amount_due": float(summary["totalAmountDue"]),
            "due_date": summary["dueDate"],
            "billing_period": charges["dateRange"],
            "number_of_days": int(charges["numberOfDays"]),
            "electric_charge": float(charges["electric"]),
            "average_daily_cost": float(charges["averageElectric"]),
            "last_payment_amount": last_payment,
            # Usage data — most recent day with non-null readings
            "last_reading_date": latest_day,
            "today_peak_kwh": round(peak_kwh, 3),
            "today_offpeak_kwh": round(offpeak_kwh, 3),
            "today_total_kwh": round(peak_kwh + offpeak_kwh, 3),
            "rate_category": rate_category,
        }