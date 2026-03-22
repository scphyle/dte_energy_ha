import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from const import DOMAIN, CONF_WEB_SECURITY_TOKEN, CONF_ACCOUNT_NUMBER


class DTEEnergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            # Basic validation — try a token refresh to verify the token works
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://newlook.dteenergy.com/api/tokenRefresh",
                        cookies={"webSecurityToken": user_input[CONF_WEB_SECURITY_TOKEN]},
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            # Store the fresh token instead of the one they pasted
                            user_input[CONF_WEB_SECURITY_TOKEN] = data["webSecurityToken"]
                        else:
                            errors["base"] = "invalid_token"
            except Exception:
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