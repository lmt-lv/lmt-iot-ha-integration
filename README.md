# LMT IoT for Home Assistant

**Developed by LMT IoT**

Custom component for automatic LMT IoT device provisioning and cloud connectivity.

**Repository**: https://github.com/lmt-lv/lmt-iot-ha-integration

## For End Users

### Requirements

- **API key**: Found in LMT IoT Mobile App or at https://mobile.lmt-iot.com/

### Installation

1. Copy the `custom_components/lmt_iot` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click "+ Add Integration"
5. Search for "LMT IoT"
6. Enter your API key
7. Select your device from the list
8. Click Submit - your device will be automatically activated

## Usage

After setup, your device will automatically connect to the cloud and receive data:

- Subscribe to topics and receive messages from your LMT IoT devices
- Use with Home Assistant MQTT entities
- Monitor sensor data in real-time

## Troubleshooting

- Check Home Assistant logs for connection errors
- Verify your device ID is correct
- Contact support if activation fails

## Support

- **Issues**: https://github.com/lmt-lv/lmt-iot-ha-integration/issues
- **Documentation**: https://github.com/lmt-lv/lmt-iot-ha-integration
