"""The Eloverblik integration."""
import asyncio
import logging
import sys

import voluptuous as vol
from homeassistant.util import Throttle
from datetime import timedelta, date

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from pyeloverblik.eloverblik import Eloverblik

from .const import DOMAIN

import requests

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

        self._day_data = None
        self._year_data = None
        self._tariff_data = None

    def get_total_day(self):
        if self._day_data != None:
            return round(self._day_data.get_total_metering_data(), 3)
        else:
            return None
    
    def get_total_year(self):
        if self._year_data != None:
            return round(self._year_data.get_total_metering_data(), 3)
        else:
            return None

    def get_usage_hour(self, hour):
        if self._day_data != None:
            try:
                return round(self._day_data.get_metering_data(hour), 3)
            except IndexError:
                self._day_data.get_metering_data(23)
                _LOGGER.info(f"Unable to get data for hour {hour}. If siwtch to daylight saving day this is not an error.")
                return 0
        else:
            return None

    def get_data_date(self):
        if self._day_data != None:
            return self._day_data.data_date.date().strftime('%Y-%m-%d')
        else:
            return None

    def get_metering_point(self):
        return self._metering_point

    def get_tariff_sum_hour(self, hour):
        if self._tariff_data != None:
            sum = 0.0
            for tariff in self._tariff_data.charges.values():
                if isinstance(tariff, list):
                    if len(tariff) == 24:
                        sum += tariff[hour - 1]
                    else:
                        _LOGGER.warning(f"Unexpected length of tariff array ({len(tariff)}), expected 24 entries.")
                else:
                    sum += float(tariff)

            return sum

        else:
            return None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update_energy(self):
        _LOGGER.debug("Fetching energy data from Eloverblik")

        try: 
            day_data = self._client.get_latest(self._metering_point)
            if day_data.status == 200:
                self._day_data = day_data
            else:
                _LOGGER.warn(f"Error from eloverblik when getting day data: {day_data.status} - {day_data.detailed_status}")

            year_data = self._client.get_per_month(self._metering_point)
            if year_data.status == 200:
                self._year_data = year_data
            else:
                _LOGGER.warn(f"Error from eloverblik when getting year data: {year_data.status} - {year_data.detailed_status}")
        except requests.exceptions.HTTPError as he:
            message = None
            if he.response.status_code == 401:
                message = f"Unauthorized error while accessing eloverblik.dk. Wrong or expired refresh token?"
            else:
                e = sys.exc_info()[1]
                message = f"Exception: {e}"

            _LOGGER.warn(message)
        except: 
            e = sys.exc_info()[1]
            _LOGGER.warn(f"Exception: {e}")

        _LOGGER.debug("Done fetching energy data from Eloverblik")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update_tariffs(self):
        _LOGGER.debug("Fetching tariff data from Eloverblik")

        try: 
            tariff_data = self._client.get_tariffs(self._metering_point)
            if tariff_data.status == 200:
                self._tariff_data = tariff_data
            else:
                _LOGGER.warn(f"Error from eloverblik when getting tariff data: {tariff_data.status} - {tariff_data.detailed_status}")
        except requests.exceptions.HTTPError as he:
            message = None
            if he.response.status_code == 401:
                message = f"Unauthorized error while accessing eloverblik.dk. Wrong or expired refresh token?"
            else:
                e = sys.exc_info()[1]
                message = f"Exception: {e}"

            _LOGGER.warn(message)
        except: 
            e = sys.exc_info()[1]
            _LOGGER.warn(f"Exception: {e}")

        _LOGGER.debug("Done fetching tariff data from Eloverblik")