# LMT IoT

Custom component for automatic LMT IoT device provisioning and cloud connectivity.

## Installation

1. Install via HACS (recommended) or manually copy files
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Click "+ Add Integration"
5. Search for "LMT IoT"
6. Enter your API key (create one following the steps below)
7. Select your device from the list
8. Click Submit - your device will be automatically activated

## Creating an API Key

1. Open https://mobile.lmt-iot.com web client portal
2. Select **Settings** section on the left-hand side
3. Press **Create API Key** button in the **SECURITY** section
4. Provide API Key name and select **READ** and **WRITE** access for the key
5. Copy the API-KEY secret value and paste it in the Home Assistant integration

## Requirements

- **API key**: Create one following the instructions above

## Features

- Automatic device provisioning
- API key authentication
- Cloud MQTT connectivity
- No manual certificate management

## Support

For issues and feature requests, visit the [GitHub repository](https://github.com/lmt-iot/homeassistant-integration).
