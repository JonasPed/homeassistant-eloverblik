"""Config flow for Eloverblik integration."""
import logging
from requests import HTTPError

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from pyeloverblik.eloverblik import Eloverblik

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("refresh_token"): str,
        vol.Required("metering_point",): str
    })

async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    token = data["refresh_token"]
    metering_point = data["metering_point"]

    service = Eloverblik(token)

    try:
        await hass.async_add_executor_job(service.get_tariffs, metering_point)
    except HTTPError as error:
        raise InvalidAuth() from error
    
    return {"title": f"Eloverblik {metering_point}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eloverblik."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        errors = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                metering_point = user_input["metering_point"]
                await self.async_set_unique_id(metering_point)
                return self.async_create_entry(title=info["title"], data=user_input)

            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
