"""Sensor platform for LMT IoT Device integration."""
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass, RestoreEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util
from datetime import timedelta

from . import DOMAIN, CONF_DEVICE_ID, CONF_SENSOR_CONFIG

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up LMT IoT sensors dynamically based on device config."""
    device_id = entry.data[CONF_DEVICE_ID]
    sensor_config = entry.data.get(CONF_SENSOR_CONFIG, [])

    sensors = [
        LMTIoTDynamicSensor(device_id, sensor)
        for sensor in sensor_config
    ]

    _LOGGER.info(f"Creating {len(sensors)} sensors for device {device_id}")
    async_add_entities(sensors)


class LMTIoTDynamicSensor(RestoreEntity, SensorEntity):
    """Dynamic sensor for LMT IoT device."""

    def __init__(self, device_id: str, config: dict):
        """Initialize the sensor."""
        self._device_id = device_id
        self._key = config["key"]
        self._attr_name = f"{device_id} {config['name']}"
        self._attr_unique_id = f"{device_id}_{config['key']}"
        self._attr_has_entity_name = False
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_native_value = None
        self._attr_available = True
        self._availability_timeout = timedelta(seconds=config.get("availabilityTimeout", 7200))
        self._unsub_availability = None
        
        state_class = config.get("stateClass")
        if state_class:
            state_class = state_class.lower()
            try:
                self._attr_state_class = SensorStateClass(state_class)
            except ValueError:
                _LOGGER.warning(f"Unknown state class: {state_class}")
        else:
            self._attr_state_class = None

        device_class = config.get("deviceClass")
        if device_class:
            device_class = device_class.lower()
            try:
                self._attr_device_class = SensorDeviceClass(device_class)
            except ValueError:
                _LOGGER.warning(f"Unknown device class: {device_class}")

    async def async_added_to_hass(self):
        """Subscribe to MQTT messages via event bus."""
        await super().async_added_to_hass()
        
        _LOGGER.info(f"Setting up sensor: {self._attr_name} (unique_id: {self._attr_unique_id})")
        
        last_state = await self.async_get_last_state()
        _LOGGER.info(f"Last state for {self._attr_name}: {last_state}")
        
        if last_state and last_state.state not in ("unknown", "unavailable", None):
            try:
                if self._attr_state_class is None:
                    self._attr_native_value = last_state.state
                else:
                    self._attr_native_value = float(last_state.state)
                _LOGGER.info(f"Restored {self._attr_name}: {self._attr_native_value}")
            except (ValueError, TypeError) as e:
                _LOGGER.warning(f"Could not restore state for {self._attr_name}: {last_state.state} - {e}")
        else:
            _LOGGER.info(f"No valid last state to restore for {self._attr_name}")

        @callback
        def handle_message(event):
            """Handle MQTT message event."""
            if event.data["device_id"] != self._device_id:
                return

            try:
                payload = event.data["payload"]
                if self._key in payload:
                    value = payload[self._key]
                    if isinstance(value, (int, float)):
                        self._attr_native_value = float(value)
                    else:
                        self._attr_native_value = value
                    self._attr_available = True
                    self._schedule_availability_check()
                    self.async_write_ha_state()
                    _LOGGER.debug(
                        f"{self._attr_name} updated: {self._attr_native_value}{self._attr_native_unit_of_measurement or ''}")
            except Exception as e:
                _LOGGER.error(f"Error parsing {self._key}: {e}")

        self.async_on_remove(
            self.hass.bus.async_listen(f"{DOMAIN}_uplink_message", handle_message)
        )
    
    def _schedule_availability_check(self):
        """Schedule availability timeout check."""
        if self._unsub_availability:
            self._unsub_availability()
        
        @callback
        def mark_unavailable(_):
            self._attr_available = False
            self.async_write_ha_state()
            _LOGGER.warning(f"{self._attr_name} marked unavailable (no data for {self._availability_timeout})")
        
        self._unsub_availability = async_track_point_in_utc_time(
            self.hass, mark_unavailable, dt_util.utcnow() + self._availability_timeout
        )
