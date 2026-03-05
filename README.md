# LMT IoT for Home Assistant

**Developed by LMT IoT**

Custom component for automatic LMT IoT device provisioning and cloud connectivity.

**Repository**: https://github.com/lmt-lv/lmt-iot-ha-integration

## For End Users

### Requirements

- **API key**: Create one following the instructions below

### Creating an API Key

1. Open https://mobile.lmt-iot.com web client portal
2. Select **Settings** section on the left-hand side
3. Press **Create API Key** button in the **SECURITY** section
4. Provide API Key name and select **READ** and **WRITE** access for the key
5. Copy the API-KEY secret value and paste it in the Home Assistant integration

### Installation

#### Option 1: HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add repository URL: `https://github.com/lmt-lv/lmt-iot-ha-integration`
6. Select category: "Integration"
7. Click "Add"
8. Search for "LMT IoT" in HACS
9. Click "Download"
10. Restart Home Assistant

#### Option 2: Manual Installation

1. Copy the `custom_components/lmt_iot` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

#### Configuration

1. Go to Configuration > Integrations
2. Click "+ Add Integration"
3. Search for "LMT IoT"
4. Enter your API key
5. Select your device from the list
6. Click Submit – your device will be automatically activated

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
