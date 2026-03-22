import voluptuous as vol
import logging
from homeassistant import config_entries

from .const import DOMAIN, CONF_WEB_SECURITY_TOKEN, CONF_ACCOUNT_NUMBER

_LOGGER = logging.getLogger(__name__)

class DTEEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    # Step 1: Refresh the token they pasted
                    async with session.get(
                            "https://newlook.dteenergy.com/api/tokenRefresh",
                            cookies={"webSecurityToken": user_input[CONF_WEB_SECURITY_TOKEN]},
                    ) as resp:
                        _LOGGER.error("tokenRefresh status: %s", resp.status)
                        if resp.status != 200:
                            body = await resp.text()
                            _LOGGER.error("tokenRefresh body: %s", body)
                            errors["base"] = "invalid_token"
                        else:
                            data = await resp.json()
                            fresh_token = data["webSecurityToken"]

                    if not errors:
                        # Step 2: Verify we can get a bearer token with it
                        async with session.get(
                                "https://newlook.dteenergy.com/api/getUserDetails",
                                cookies={"webSecurityToken": fresh_token},
                        ) as resp:
                            _LOGGER.error("getUserDetails status: %s", resp.status)
                            if resp.status != 200:
                                errors["base"] = "invalid_token"
                            else:
                                # All good, store the fresh token
                                user_input[CONF_WEB_SECURITY_TOKEN] = fresh_token

            except Exception as e:
                _LOGGER.error("DTE connection exception: %s", str(e))
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"DTE Energy ({user_input[CONF_ACCOUNT_NUMBER]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_WEB_SECURITY_TOKEN): str,
                vol.Required(
                    CONF_ACCOUNT_NUMBER,
                    default="00000000000"
                ): str,
            }),
            errors=errors,
            description_placeholders={
                "token_help": "Log into newlook.dteenergy.com, then open DevTools (F12) → Application → Cookies and copy the webSecurityToken value."
            }
        )

    async def async_step_reauth(self, user_input=None):
        """Handle re-authentication when token expires."""
        errors = {}

        if user_input is not None:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://newlook.dteenergy.com/api/tokenRefresh",
                        cookies={"webSecurityToken": user_input[CONF_WEB_SECURITY_TOKEN]},
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # Update the existing config entry with the new token
                            self.hass.config_entries.async_update_entry(
                                self._get_reauth_entry(),
                                data={
                                    **self._get_reauth_entry().data,
                                    CONF_WEB_SECURITY_TOKEN: data["webSecurityToken"],
                                },
                            )
                            await self.hass.config_entries.async_reload(
                                self._get_reauth_entry().entry_id
                            )
                            return self.async_abort(reason="reauth_successful")
                        else:
                            errors["base"] = "invalid_token"
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema({
                vol.Required(CONF_WEB_SECURITY_TOKEN): str,
            }),
            errors=errors,
        )