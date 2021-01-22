# SensiML Simple Streaming Gateway

This application works as example application code for developing a gateway for emmbedded devices using the SensiML Simple Streaming service.

## Installation

To install the app dependencies run

```bash
cd simple-streaming-gateway
pip install -r requirements.txt
```

To Start the application run

```bash
python3 app.py
```

## Data Collection over Serial

    1. Connect edge node to Gateway over USB serial
    2. Go to Gateway Configure Screen, Select Serial Radio and Click Scan
    3. Enter the the Device ID (which is the port) into the Text Field and Click Configure
    4. The Simple Streaming Gateway is now configured to Stream Data from your Device over WiFi

**NOTE** The BAUD RATE for the serial connection can be changed in the app.py by updating the default BAUD_RATE configuration.

## Data Collection over BLE

    1. Connect edge node to Gateway over USB serial
    2. Go to Gateway Configure Screen, Select BLE Radio and Click Scan
    3. Enter the the Device ID (which is the port) into the Text Field and Click Configure
    4. The Simple Streaming Gateway is now configured to Stream Data from your Device over WiFi

**NOTE** To use bluethooth as a source you may have to run the following to allow bluepy-helper to access the correct permissions

```bash
find ~/ -name bluepy-helper
cd <PATH>
sudo setcap 'cap_net_raw,cap_net_admin+eip' bluepy-helper
```
