"""Platform for Eloverblik sensor integration."""
import logging
from homeassistant.const import ENERGY_KILO_WATT_HOUR
from homeassistant.helpers.entity import Entity
from pyeloverblik.eloverblik import Eloverblik
from pyeloverblik.models import TimeSeries

_LOGGER = logging.getLogger(__name__)
from .const import DOMAIN



async def async_setup_entry(hass, config, async_add_entities):
    """Set up the sensor platform."""
    eloverblik = hass.data[DOMAIN][config.entry_id]

    sensors = []
    sensors.append(EloverblikEnergy("Eloverblik Energy Total", 'total', eloverblik))
    for x in range(1, 25):
        sensors.append(EloverblikEnergy(f"Eloverblik Energy {x-1}-{x}", 'hour', eloverblik, x))
    async_add_entities(sensors)


class EloverblikEnergy(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, sensor_type, client, hour=None):
        """Initialize the sensor."""
        self._state = None
        self._data_date = None
        self._data = client
        self._hour = hour
        self._name = name
        self._sensor_type = sensor_type

        if sensor_type == 'hour':
            self._unique_id = f"{self._data.get_metering_point()}-{hour}"
        else:
            self._unique_id = f"{self._data.get_metering_point()}-total"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """The unique id of the sensor."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return state attributes."""
        attributes = dict()
        attributes['Metering date'] = self._data_date
        
        return attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return ENERGY_KILO_WATT_HOUR

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._data.update()        

        self._data_date = self._data.get_data_date()

        if self._sensor_type == 'total':
            self._state = self._data.get_total_day()
        else:
            self._state = self._data.get_usage_hour(self._hour)

