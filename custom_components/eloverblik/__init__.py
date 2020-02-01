"""The Eloverblik integration."""
import asyncio
import logging

import voluptuous as vol
from homeassistant.util import Throttle
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from pyeloverblik.eloverblik import Eloverblik

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor"]

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=60)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Eloverblik component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Eloverblik from a config entry."""
    refresh_token = entry.data['refresh_token']
    metering_point = entry.data['metering_point']
    
    hass.data[DOMAIN][entry.entry_id] = HassEloverblik(refresh_token, metering_point)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

class HassEloverblik:
    def __init__(self, refresh_token, metering_point):
        self._client = Eloverblik(refresh_token)
        self._metering_point = metering_point

    def get_total_day(self):
        return self._data.get_total_metering_data()

    def get_usage_hour(self, hour):
        return self._data.get_metering_data(hour)

    def get_data_date(self):
        return self._data.data_date

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        _LOGGER.debug("Fetching data from Danfoss Air CCM module")

        self._data = self._client.get_yesterday_parsed(self._metering_point)

        _LOGGER.debug("Done fetching data from Danfoss Air CCM module")

