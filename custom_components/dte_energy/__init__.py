import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from const import DOMAIN, PLATFORMS, CONF_WEB_SECURITY_TOKEN, CONF_ACCOUNT_NUMBER
from coordinator import DTEDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = DTEDataCoordinator(
        hass,
        web_security_token=entry.data[CONF_WEB_SECURITY_TOKEN],
        account_number=entry.data[CONF_ACCOUNT_NUMBER],
    )

    # Do first refresh — raises ConfigEntryNotReady if it fails
    # so HA will retry automatically
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to connect to DTE Energy: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok