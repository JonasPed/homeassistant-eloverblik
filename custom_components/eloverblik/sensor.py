"""Platform for Eloverblik sensor integration."""
from datetime import datetime, timedelta
import logging
import pytz
from homeassistant.const import UnitOfEnergy
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    DOMAIN as RECORDER_DOMAIN,
    async_import_statistics,
    get_last_statistics,
)
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMetaData
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity
from pyeloverblik.models import TimeSeries
from .__init__ import HassEloverblik, MIN_TIME_BETWEEN_UPDATES
from .const import DOMAIN, CURRENCY_KRONER_PER_KILO_WATT_HOUR

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    """Set up the sensor platform."""
    eloverblik = hass.data[DOMAIN][config.entry_id]

    sensors = []
    sensors.append(EloverblikEnergy("Eloverblik Energy Total", 'total', eloverblik))
    sensors.append(EloverblikEnergy("Eloverblik Energy Total (Year)", 'year_total', eloverblik))
    sensors.append(MeterReading("Eloverblik Meter Reading", eloverblik))
    for hour in range(1, 25):
        sensors.append(EloverblikEnergy(f"Eloverblik Energy {hour-1}-{hour}", 'hour', eloverblik, hour))
    sensors.append(EloverblikTariff("Eloverblik Tariff Sum", eloverblik))
    sensors.append(EloverblikStatistic(eloverblik))

    async_add_entities(sensors)

class EloverblikEnergy(Entity):
    """Representation of an energy sensor."""

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
        elif sensor_type == 'total':
            self._unique_id = f"{self._data.get_metering_point()}-total"
        elif sensor_type == 'year_total':
            self._unique_id = f"{self._data.get_metering_point()}-year-total"
        else:
            raise ValueError(f"Unexpected sensor_type: {sensor_type}.")

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
    def extra_state_attributes(self):
        """Return state attributes."""
        attributes = dict()
        attributes['Metering date'] = self._data_date
        attributes['metering_date'] = self._data_date

        return attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._data.update_energy()

        self._data_date = self._data.get_data_date()

        if self._sensor_type == 'hour':
            self._state = self._data.get_usage_hour(self._hour)
        elif self._sensor_type == 'total':
            self._state = self._data.get_total_day()
        elif self._sensor_type == 'year_total':
            self._state = self._data.get_total_year()
        else:
            raise ValueError(f"Unexpected sensor_type: {self._sensor_type}.")

class MeterReading(Entity):
    """Representation of a meter reading sensor."""

    def __init__(self, name, client):
        """Initialize the sensor."""
        self._state = None
        self._data_date = None
        self._data = client
        self._name = name

        self._unique_id = f"{self._data.get_metering_point()}-meter-reading"

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
    def extra_state_attributes(self):
        """Return state attributes."""
        attributes = dict()
        attributes['meter_reading_date'] = self._data_date
        
        return attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfEnergy.KILO_WATT_HOUR

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._data.update_meter_reading()       

        self._data_date = self._data.meter_reading_date()
        self._state = self._data.meter_reading()

class EloverblikTariff(Entity):
    """Representation of an energy sensor."""

    def __init__(self, name, client):
        """Initialize the sensor."""
        self._state = None
        self._data = client
        self._data_hourly_tariff_sums = [0] * 24
        self._name = name
        self._unique_id = f"{self._data.get_metering_point()}-tariff-sum"

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
    def extra_state_attributes(self):
        """Return state attributes."""
        attributes = {
            "hourly": [self._data_hourly_tariff_sums[i] for i in range(24)]
        }

        return attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return CURRENCY_KRONER_PER_KILO_WATT_HOUR

    def update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._data.update_tariffs()

        self._data_hourly_tariff_sums = [self._data.get_tariff_sum_hour(h) for h in range(1, 25)]
        self._state = self._data_hourly_tariff_sums[datetime.now().hour]


class EloverblikStatistic(SensorEntity):
    """This class handles the total energy of the meter,
    and imports it as long term statistics from Eloverblik."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, hass_eloverblik: HassEloverblik):
        self._attr_name = "Eloverblik Energy Statistic"
        self._attr_unique_id = f"{hass_eloverblik.get_metering_point()}-statistic"
        self._hass_eloverblik = hass_eloverblik

    async def async_will_remove_from_hass(self) -> None:
        """Cleanup callback to remove statistics when deleting entity"""
        await get_instance(self.hass).async_clear_statistics([self.entity_id])

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Continually update history"""
        last_stat = await self._get_last_stat(self.hass)

        if last_stat is not None and pytz.utc.localize(datetime.now()) - last_stat["start"] < timedelta(days=1):
            # If less than 1 day since last record, don't pull new data.
            # Data is available at the earliest a day after.
            return

        self.hass.async_create_task(self._update_data(last_stat))

    async def _update_data(self, last_stat: StatisticData):
        if last_stat is None:
            # if none import from last january
            from_date = datetime(datetime.today().year-1, 1, 1)
        else:
            # Next day at noon (eloverblik.py will strip time)
            from_date = last_stat["start"] + timedelta(hours=13)

        data = await self.hass.async_add_executor_job(
            self._hass_eloverblik.get_hourly_data,
            from_date,
            datetime.now())

        if data is not None:
            await self._insert_statistics(data, last_stat)
        else:
            _LOGGER.debug("None data was returned from Eloverblik")

    async def _insert_statistics(
        self,
        data: dict[datetime, TimeSeries],
        last_stat: StatisticData):

        statistics : list[StatisticData] = []

        if last_stat is not None:
            total = last_stat["sum"]
        else:
            total = 0

        # Sort time series to ensure correct insertion
        sorted_time_series = sorted(data.values(), key = lambda timeseries : timeseries.data_date)

        for time_series in sorted_time_series:
            if time_series._metering_data is not None:
                number_of_hours = len(time_series._metering_data)

                # data_date returned is end of the time series
                date = pytz.utc.localize(time_series.data_date) - timedelta(hours=number_of_hours)

                for hour in range(0, number_of_hours):
                    start = date + timedelta(hours=hour)

                    total += time_series.get_metering_data(hour+1)

                    statistics.append(
                        StatisticData(
                            start=start,
                            sum=total
                        ))

        metadata = StatisticMetaData(
            name=self._attr_name,
            source=RECORDER_DOMAIN,
            statistic_id=self.entity_id,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            has_mean=False,
            has_sum=True,
        )

        if len(statistics) > 0:
            async_import_statistics(self.hass, metadata, statistics)

    async def _get_last_stat(self, hass: HomeAssistant) -> StatisticData:
        last_stats = await get_instance(hass).async_add_executor_job(
            get_last_statistics, hass, 1, self.entity_id, True, {"sum"}
        )

        if self.entity_id in last_stats and len(last_stats[self.entity_id]) > 0:
            return last_stats[self.entity_id][0]
        else:
            return None
