"""LMT IoT Device Integration for Home Assistant.

Developed by LMT IoT
https://github.com/lmt-lv/lmt-iot-ha-integration
"""
import logging
import ssl
import tempfile
import os
import json
from enum import IntEnum
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT
import paho.mqtt.client as mqtt

from .parser import parse_uplink_message
from .config import DOMAIN, CONF_DEVICE_ID, CONF_API_KEY, CONF_CA_CERT, CONF_CLIENT_CERT, CONF_CLIENT_KEY, CONF_SENSOR_CONFIG

_LOGGER = logging.getLogger(__name__)


class MQTTConnectionResult(IntEnum):
    """MQTT connection result codes."""
    SUCCESS = 0
    INCORRECT_PROTOCOL = 1
    INVALID_CLIENT_ID = 2
    SERVER_UNAVAILABLE = 3
    BAD_CREDENTIALS = 4
    NOT_AUTHORIZED = 5

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LMT IoT MQTT from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    def setup_mqtt_client():
        """Set up MQTT client with TLS in executor."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(cadata=entry.data[CONF_CA_CERT])
        
        cert_fd, cert_path = tempfile.mkstemp(suffix='.pem')
        key_fd, key_path = tempfile.mkstemp(suffix='.key')
        
        try:
            os.chmod(cert_path, 0o600)
            os.chmod(key_path, 0o600)
            
            with os.fdopen(cert_fd, 'w') as cert_file:
                cert_file.write(entry.data[CONF_CLIENT_CERT])
            with os.fdopen(key_fd, 'w') as key_file:
                key_file.write(entry.data[CONF_CLIENT_KEY])
            
            context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        finally:
            try:
                os.unlink(cert_path)
            except OSError:
                pass
            try:
                os.unlink(key_path)
            except OSError:
                pass
        
        client = mqtt.Client(client_id=entry.data[CONF_DEVICE_ID], protocol=mqtt.MQTTv311)
        client.tls_set_context(context)
        client.tls_insecure_set(False)
        client.reconnect_delay_set(min_delay=1, max_delay=120)
        
        def on_connect(client, userdata, flags, rc):
            if rc == MQTTConnectionResult.SUCCESS:
                _LOGGER.info("Connected to LMT IoT Cloud")
                device_id = entry.data[CONF_DEVICE_ID]
                topic = f"things/{device_id}/telemetry"
                client.subscribe(topic)
                _LOGGER.info(f"Subscribed to topic: {topic}")
            else:
                _LOGGER.error(f"Failed to connect to LMT IoT Cloud: {MQTTConnectionResult(rc).name} (rc={rc})")
        
        def on_message(client, userdata, msg):
            _LOGGER.debug(f"Received message on {msg.topic}: {msg.payload.decode()}")
            try:
                payload = json.loads(msg.payload.decode())
                parsed = parse_uplink_message(payload)
                
                if parsed:
                    hass.bus.fire(f"{DOMAIN}_uplink_message", {
                        "device_id": entry.data[CONF_DEVICE_ID],
                        "topic": msg.topic,
                        "payload": parsed
                    })
                    _LOGGER.debug(f"Parsed data: {parsed}")
            except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                _LOGGER.error(f"Error parsing message: {e}")
        
        def on_disconnect(client, userdata, rc):
            if rc != 0:
                _LOGGER.warning(f"Disconnected from LMT IoT Cloud: rc={rc}, will auto-reconnect")
            else:
                _LOGGER.info(f"Disconnected from LMT IoT Cloud")
        
        def on_subscribe(client, userdata, mid, granted_qos):
            _LOGGER.debug(f"Subscription confirmed: mid={mid}, qos={granted_qos}")
        
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect
        client.on_subscribe = on_subscribe
        
        _LOGGER.info(f"Connecting to {entry.data[CONF_HOST]}:{entry.data.get(CONF_PORT, 8883)} as {entry.data[CONF_DEVICE_ID]}")
        client.connect(
            entry.data[CONF_HOST],
            entry.data.get(CONF_PORT, 8883)
        )
        _LOGGER.debug("Starting MQTT loop...")
        client.loop_start()
        return {"client": client}
    
    data = await hass.async_add_executor_job(setup_mqtt_client)
    
    hass.data[DOMAIN][entry.entry_id] = data
    
    # Set up sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        client = data["client"]
        await hass.async_add_executor_job(client.loop_stop)
        await hass.async_add_executor_job(client.disconnect)
    
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
