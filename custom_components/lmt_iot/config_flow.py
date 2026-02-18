"""Config flow for LMT IoT Device integration.

Developed by LMT IoT
https://github.com/lmt-lv/lmt-iot-ha-integration
"""
import logging
import voluptuous as vol
import aiohttp
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from . import DOMAIN, CONF_DEVICE_ID, CONF_API_KEY, CONF_CA_CERT, CONF_CLIENT_CERT, CONF_CLIENT_KEY, CONF_SENSOR_CONFIG, CONF_DEVICE_TYPE
from .config import API_URL, MQTT_HOST, MQTT_PORT

_LOGGER = logging.getLogger(__name__)

CONF_DEVICE_LIST = "device_list"

class LMTIoTMQTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LMT IoT Device."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._device_id = None
        self._device_name = None
        self._api_url = API_URL
        self._api_key = None
        self._device_list = []
        self._sensor_configs = {}

    def _format_device_display_name(self, device: dict, device_id: str) -> str:
        """Format device display name from device data."""
        room = device.get("room", {})
        custom_name = room.get("customName")
        default_name = room.get("name", "")
        room_name = custom_name if custom_name else (default_name.title() if default_name else "")
        house_name = room.get("house", {}).get("name", "")
        
        display_parts = []
        if house_name:
            display_parts.append(house_name)
        if room_name:
            display_parts.append(room_name)
        display_parts.append(f"({device_id})")
        
        return " - ".join(display_parts)

    async def async_step_user(self, user_input=None):
        """Handle the initial step - API key input or device selection."""
        errors = {}

        existing_api_key = None
        for entry in self._async_current_entries():
            if CONF_API_KEY in entry.data:
                existing_api_key = entry.data[CONF_API_KEY]
                break

        if existing_api_key:
            # Skip API key input, use existing key
            self._api_key = existing_api_key
            return await self._get_device_list()

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            return await self._get_device_list()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            }),
            errors=errors,
            description_placeholders={"info": "Enter your X-API-KEY from the developer portal"}
        )

    async def _get_device_list(self):
        """Get device list from API."""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"X-API-KEY": self._api_key}
                async with session.get(f"{self._api_url}/devices?limit=50", headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 401:
                        return self._show_api_error("invalid_api_key")
                    elif response.status == 403:
                        return self._show_api_error("insufficient_permissions")
                    elif response.status >= 500:
                        return self._show_api_error("server_error")
                    elif response.status >= 400:
                        return self._show_api_error("api_error")
                    
                    devices = (await response.json()).get("data", [])
                    
                    type_cache = {}
                    for device in devices:
                        device_type = device["type"]
                        if device_type not in type_cache:
                            async with session.get(f"{self._api_url}/devices/types/{device_type}", headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as type_response:
                                if type_response.status >= 300:
                                    continue
                                type_data = await type_response.json()
                                smart_home = (type_data.get("measurements") or {}).get("smartHome") or {}
                                type_cache[device_type] = {
                                    "enabled": smart_home.get("enabled", False),
                                    "sensors": smart_home.get("sensors", [])
                                }
                        
                        if type_cache.get(device_type, {}).get("enabled"):
                            device_id = device["serialNumber"]
                            display_name = self._format_device_display_name(device, device_id)
                            
                            self._device_list.append({
                                "id": device_id,
                                "name": display_name,
                                "device_name": display_name,
                                "type": device_type
                            })
                            self._sensor_configs[device_id] = type_cache[device_type]["sensors"]
                    
                    if not self._device_list:
                        return self.async_abort(reason="no_devices")
                    
                    return await self.async_step_device_select()
        except aiohttp.ClientTimeout:
            return self._show_api_error("timeout")
        except aiohttp.ClientError:
            return self._show_api_error("connection_error")
        except Exception as e:
            _LOGGER.error(f"Failed to get devices: {e}", exc_info=True)
            return self._show_api_error("cannot_connect")

    def _show_api_error(self, error_key):
        """Show API error form."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            }),
            errors={"base": error_key},
            description_placeholders={"info": "Enter your X-API-KEY from the developer portal"}
        )

    async def async_step_device_select(self, user_input=None):
        """Handle device selection step."""
        errors = {}

        if user_input is not None:
            self._device_id = user_input[CONF_DEVICE_ID]
            selected_device = next((dev for dev in self._device_list if dev["id"] == self._device_id), None)
            self._device_name = selected_device["device_name"]
            device_type = selected_device["type"]
            
            await self.async_set_unique_id(self._device_id)
            self._abort_if_unique_id_configured()
            
            _LOGGER.info(f"User selected device: {self._device_id}")

            try:
                _LOGGER.info(f"Requesting certificates for device: {self._device_id}")
                async with aiohttp.ClientSession() as session:
                    headers = {"X-API-KEY": self._api_key}
                    data = {"target": "SMART_HOME"}
                    async with session.post(f"{self._api_url}/devices/{self._device_id}/certificates", headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 401:
                            errors["base"] = "invalid_api_key"
                        elif response.status == 403:
                            errors["base"] = "insufficient_permissions"
                        elif response.status == 404:
                            errors["base"] = "device_not_found"
                        elif response.status >= 500:
                            errors["base"] = "server_error"
                        elif response.status >= 400:
                            errors["base"] = "api_error"
                        else:
                            provision_data = await response.json()
                            _LOGGER.info(f"Certificate response: {provision_data}")
                            return await self._provision_device(provision_data, device_type)
            except aiohttp.ClientTimeout:
                errors["base"] = "timeout"
            except aiohttp.ClientError:
                errors["base"] = "connection_error"
            except Exception as e:
                _LOGGER.error(f"Certificate retrieval failed for device {self._device_id}: {e}", exc_info=True)
                errors["base"] = "cannot_connect"

        device_options = {dev["id"]: dev["name"] for dev in self._device_list}

        return self.async_show_form(
            step_id="device_select",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_ID): vol.In(device_options),
            }),
            errors=errors
        )

    async def _provision_device(self, data, device_type):
        """Provision device with received credentials."""
        _LOGGER.info(f"Provisioning device: {self._device_id}")
        ca_cert = await self._get_amazon_root_ca()
        
        sensor_count = len(self._sensor_configs.get(self._device_id, []))
        _LOGGER.info(f"Creating config entry for device {self._device_id} with {sensor_count} sensors")

        title = f"Device {self._device_name}" if self._device_name else f"Device {self._device_id}"

        return self.async_create_entry(
            title=title,
            data={
                CONF_HOST: MQTT_HOST,
                CONF_PORT: MQTT_PORT,
                CONF_CA_CERT: ca_cert,
                CONF_CLIENT_CERT: data["certificatePem"],
                CONF_CLIENT_KEY: data["privateKey"],
                CONF_DEVICE_ID: self._device_id,
                CONF_API_KEY: self._api_key,
                CONF_SENSOR_CONFIG: self._sensor_configs.get(self._device_id, []),
                CONF_DEVICE_TYPE: device_type,
            }
        )

    async def _get_amazon_root_ca(self):
        """Download Amazon Root CA 1 certificate."""
        try:
            _LOGGER.info("Downloading Amazon Root CA certificate")
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.amazontrust.com/repository/AmazonRootCA1.pem", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    _LOGGER.info(f"Amazon Root CA download status: {response.status}")
                    return await response.text()
        except Exception as e:
            _LOGGER.error(f"Failed to download Amazon Root CA: {e}", exc_info=True)
            _LOGGER.warning("Using fallback Amazon Root CA certificate")
            return "-----BEGIN CERTIFICATE-----\nMIIDQTCCAimgAwIBAgITBmyfz5m/jAo54vB4ikPmljZbyjANBgkqhkiG9w0BAQsF\nADA5MQswCQYDVQQGEwJVUzEPMA0GA1UEChMGQW1hem9uMRkwFwYDVQQDExBBbWF6\nb24gUm9vdCBDQSAxMB4XDTE1MDUyNjAwMDAwMFoXDTM4MDExNzAwMDAwMFowOTEL\nMAkGA1UEBhMCVVMxDzANBgNVBAoTBkFtYXpvbjEZMBcGA1UEAxMQQW1hem9uIFJv\nb3QgQ0EgMTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALJ4gHHKeNXj\nca9HgFB0fW7Y14h29Jlo91ghYPl0hAEvrAIthtOgQ3pOsqTQNroBvo3bSMgHFzZM\n9O6II8c+6zf1tRn4SWiw3te5djgdYZ6k/oI2peVKVuRF4fn9tBb6dNqcmzU5L/qw\nIFAGbHrQgLKm+a/sRxmPUDgH3KKHOVj4utWp+UhnMJbulHheb4mjUcAwhmahRWa6\nVOujw5H5SNz/0egwLX0tdHA114gk957EWW67c4cX8jJGKLhD+rcdqsq08p8kDi1L\n93FcXmn/6pUCyziKrlA4b9v7LWIbxcceVOF34GfID5yHI9Y/QCB/IIDEgEw+OyQm\njgSubJrIqg0CAwEAAaNCMEAwDwYDVR0TAQH/BAUwAwEB/zAOBgNVHQ8BAf8EBAMC\nAYYwHQYDVR0OBBYEFIQYzIU07LwMlJQuCFmcx7IQTgoIMA0GCSqGSIb3DQEBCwUA\nA4IBAQCY8jdaQZChGsV2USggNiMOruYou6r4lK5IpDB/G/wkjUu0yKGX9rbxenDI\nU5PMCCjjmCXPI6T53iHTfIuJruydjsw2hUwsOjsQl/8gDHmG5Oq14cNA4+7QKj2V\n11RUYfXTpz0AhHsHnoDcTDMxnpXb78ieQw2E+MPWbbWmXw/VWJJwpxn4OkqNGpF8\nShQl5Z6psk4ajJaGSiJOrM8fDS8acDRRVCs0Uc7pmAoTGnHXXXO2VEA5Y9Xig3CH\n82o9RpR1BSiMDx0GXEcSUk1EZfFDgqSWjOhK1J8Z4jNVrqI1qbFff3RHksVK1EPe\nOAD0C/X7RxbAnp/XDjgA+RFrOO/r\n-----END CERTIFICATE-----"
