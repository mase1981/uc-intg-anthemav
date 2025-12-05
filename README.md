# Anthem A/V Receivers Integration for Unfolded Circle Remote 2/3

Control your Anthem A/V receivers and processors (MRX, AVM, STR series) directly from your Unfolded Circle Remote 2 or Remote 3 with comprehensive media player control, **complete multi-zone support**, **source switching**, and **full volume control**.

![Anthem](https://img.shields.io/badge/Anthem-A%2FV%20Receivers-red)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-anthemav?style=flat-square)](https://github.com/mase1981/uc-intg-anthemav/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-anthemav?style=flat-square)](https://github.com/mase1981/uc-intg-anthemav/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://community.unfoldedcircle.com/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-anthemav/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)


## Features

This integration provides comprehensive control of Anthem A/V receivers and processors through the Anthem TCP/IP control protocol, delivering seamless integration with your Unfolded Circle Remote for complete home theater control.

---
## 💰 Support Development

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

### 🎵 **Media Player Control**

#### **Power Management**
- **Power On/Off** - Complete power control per zone
- **Power Toggle** - Quick power state switching
- **State Feedback** - Real-time power state monitoring
- **Multi-Zone Control** - Independent power control for up to 3 zones

#### **Volume Control**
- **Volume Up/Down** - Precise volume adjustment
- **Set Volume** - Direct volume control (-90dB to 0dB)
- **Volume Slider** - Visual volume control (0-100 scale)
- **Mute Toggle** - Quick mute/unmute
- **Unmute** - Explicit unmute control
- **Per-Zone Volume** - Independent volume control for each zone

#### **Source Selection**
Control all available input sources per zone:
- **HDMI Inputs** - HDMI 1-8 selection
- **Analog Inputs** - Analog 1-2
- **Digital Inputs** - Digital 1-2 (Coax/Optical)
- **ARC Input** - HDMI ARC support
- **Other Sources** - USB, Network streaming
- **7.1 Analog** - Multichannel analog input

### 🔌 **Multi-Device & Multi-Zone Support**

- **Multiple Receivers** - Control unlimited Anthem receivers on your network
- **Multi-Zone Support** - Up to 3 zones per receiver
- **Individual Configuration** - Each zone gets dedicated media player entity
- **Manual Configuration** - Direct IP address entry
- **Model Detection** - Automatic model identification
- **Zone Naming** - Custom zone names supported

### **Supported Models**

#### **MRX Series** - Receivers
- **MRX 520** - 11-channel receiver with Dolby Atmos
- **MRX 720** - 11-channel receiver with enhanced processing
- **MRX 1120** - 11-channel flagship receiver
- **MRX 1140** - 15-channel flagship with advanced features

#### **AVM Series** - Processors  
- **AVM 60** - 7.1/5.1.2 processor
- **AVM 70** - 15.1 processor with Dolby Atmos
- **AVM 90** - 16-channel reference processor

#### **STR Series** - Integrated Amplifiers
- All STR models with IP control support

### **Protocol Requirements**

- **Protocol**: Anthem TCP/IP Text-Based Control
- **Control Port**: 14999 (TCP)
- **Network Access**: Receiver must be on same local network
- **Firewall**: TCP port 14999 must be accessible
- **Connection**: Persistent TCP connection with automatic reconnection

### **Network Requirements**

- **Local Network Access** - Integration requires same network as Anthem receiver
- **TCP Protocol** - Firewall must allow TCP traffic on port 14999
- **Static IP Recommended** - Receiver should have static IP or DHCP reservation
- **IP Control Enabled** - Enable IP control in receiver's network settings

## Installation

### Option 1: Remote Web Interface (Recommended)
1. Navigate to the [**Releases**](https://github.com/mase1981/uc-intg-anthemav/releases) page
2. Download the latest `uc-intg-anthemav-<version>-aarch64.tar.gz` file
3. Open your remote's web interface (`http://your-remote-ip`)
4. Go to **Settings** → **Integrations** → **Add Integration**
5. Click **Upload** and select the downloaded `.tar.gz` file

### Option 2: Docker (Advanced Users)

The integration is available as a pre-built Docker image from GitHub Container Registry:

**Image**: `ghcr.io/mase1981/uc-intg-anthemav:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-anthemav:
    image: ghcr.io/mase1981/uc-intg-anthemav:latest
    container_name: uc-intg-anthemav
    network_mode: host
    volumes:
      - </local/path>:/data
    environment:
      - UC_CONFIG_HOME=/data
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-anthemav --restart unless-stopped --network host -v anthemav-config:/app/config -e UC_CONFIG_HOME=/app/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-anthemav:latest
```

## Configuration

### Step 1: Prepare Your Anthem Receiver

**IMPORTANT**: Anthem receiver must be powered on and connected to your network before adding the integration.

#### Verify Network Connection:
1. Check that receiver is connected to network (Ethernet recommended)
2. Note the IP address from receiver's network settings menu
3. Ensure receiver firmware is up to date
4. Verify IP control is enabled (usually enabled by default)

#### Network Setup:
- **Wired Connection**: Recommended for stability
- **Static IP**: Recommended via DHCP reservation
- **Firewall**: Allow TCP port 14999
- **Network Isolation**: Must be on same subnet as Remote

### Step 2: Setup Integration

1. After installation, go to **Settings** → **Integrations**
2. The Anthem integration should appear in **Available Integrations**
3. Click **"Configure"** and select setup mode:

#### **Single Device Setup:**

   **Configuration:**
   - **IP Address**: Enter receiver IP (e.g., 192.168.1.100)
   - **Port**: Default 14999 (change only if customized)
   - **Device Name**: Friendly name (e.g., "Living Room Anthem")
   - **Model Series**: Select your receiver (MRX, AVM, STR)
   - **Number of Zones**: 1-3 zones to configure
   - Click **Complete Setup**
   
   **Connection Test:**
   - Integration verifies receiver connectivity
   - Model information retrieved automatically
   - Setup fails if receiver unreachable

#### **Multi-Device Setup:**

   **Configuration:**
   - Select number of devices (2-4)
   - For each device, provide:
     - IP address
     - Port (default 14999)
     - Friendly name
     - Model series
     - Number of zones
   - Click **Complete Setup**
   
   **Connection Test:**
   - Integration tests all connections
   - Only successfully connected devices added
   - Failed connections reported

3. Integration will create **media player entity per zone**:
   - **Zone 1**: `media_player.anthem_[device_name]`
   - **Zone 2**: `media_player.anthem_[device_name]_zone_2`
   - **Zone 3**: `media_player.anthem_[device_name]_zone_3`

## Using the Integration

### Media Player Entity (Per Zone)

Each zone's media player entity provides complete control:

- **Power Control**: On/Off/Toggle with state feedback
- **Volume Control**: Volume slider (-90dB to 0dB mapped to 0-100)
- **Volume Buttons**: Up/Down with real-time feedback
- **Mute Control**: Toggle, Mute, Unmute
- **Source Selection**: Dropdown with all available inputs
- **State Display**: Current power, volume, source, and mute status

### Available Sources

| Source Name | Description |
|------------|-------------|
| HDMI 1-8 | HDMI digital inputs |
| Analog 1-2 | Analog stereo inputs |
| Digital 1-2 | Coaxial/Optical digital inputs |
| ARC | HDMI Audio Return Channel |
| USB | USB audio input |
| Network | Network streaming |
| Analog 7.1 | Multichannel analog input |

### Multi-Zone Control

- **Independent Control**: Each zone operates independently
- **Simultaneous Control**: Control multiple zones at once
- **Zone Linking**: Link zones for synchronized playback (if supported by receiver)
- **Per-Zone Sources**: Each zone can select different input sources
- **Per-Zone Volume**: Independent volume control per zone

## Troubleshooting

### Integration Not Discovered

**Symptoms**: Integration doesn't appear in Remote's integration list

**Solutions**:
1. **Windows Development**: Install/start Bonjour service
   ```powershell
   Get-Service "Bonjour Service" | Start-Service
   ```
2. **Manual Connection**: Add integration using PC's IP address and port 9090
3. Verify both devices are on same network/subnet
4. Check Windows Firewall allows Python and port 9090

### Cannot Connect to Receiver

**Symptoms**: "Connection refused" or timeout errors during setup

**Solutions**:
1. Verify receiver's IP address is correct
2. Ping receiver from PC/Remote: `ping 192.168.1.100`
3. Check receiver has IP control enabled
4. Verify port 14999 is not blocked by firewall
5. Try telnet test: `telnet 192.168.1.100 14999`
6. Ensure receiver is powered on and network cable connected
7. Check receiver's network settings menu for IP configuration

### Entities Show as "Unavailable"

**Symptoms**: Entities exist but show unavailable status

**Solutions**:
1. Check receiver is powered on and network connection stable
2. Verify receiver responds to commands (test via telnet)
3. Review integration logs for connection errors
4. Restart integration
5. Check configuration file is valid
6. Verify receiver firmware is up to date
7. Test TCP connection manually

### Commands Not Working

**Symptoms**: Commands sent but receiver doesn't respond

**Solutions**:
1. Check receiver is not in deep standby mode
2. Verify firmware is up to date
3. Test commands manually via telnet
4. Check for IP control lockout (some models have security settings)
5. Review receiver's network settings menu
6. Ensure no other application is controlling the receiver
7. Check integration logs for error messages

### Volume Not Syncing

**Symptoms**: Volume changes on receiver but not reflected in Remote

**Solutions**:
1. Check TCP connection is stable
2. Verify receiver sends status updates
3. Review logs for parsing errors
4. Try querying status manually: `Z1VOL?`
5. Restart both integration and receiver
6. Check network latency/stability
7. Verify no network packet loss

### Zone 2/3 Not Responding

**Symptoms**: Only Zone 1 works, other zones unavailable

**Solutions**:
1. Verify receiver supports multiple zones (not all models do)
2. Check zones 2/3 are enabled in receiver settings
3. Ensure zones are properly configured in integration setup
4. Review receiver manual for zone capabilities
5. Test zone commands manually via telnet
6. Check receiver's zone configuration menu

### Multi-Device Issues

**Symptoms**: Some receivers work, others don't in multi-device setup

**Solutions**:
1. Verify all IP addresses are correct and unique
2. Test each receiver connection individually
3. Ensure no IP address conflicts on network
4. Check all receivers have IP control enabled
5. Review integration logs for device-specific errors
6. Verify network can reach all receivers
7. Test connections manually via telnet

### Connection Drops

**Symptoms**: Integration loses connection to receiver periodically

**Solutions**:
1. Check network stability (WiFi vs Ethernet)
2. Use wired Ethernet connection for receiver
3. Verify router not dropping idle TCP connections
4. Check for network congestion or bandwidth issues
5. Review router logs for connection issues
6. Assign static IP or DHCP reservation
7. Update receiver firmware
8. Check for network hardware issues

### Setup Fails with Timeout

**Symptoms**: Setup wizard times out during connection test

**Solutions**:
1. Increase timeout if possible (default 10 seconds)
2. Verify receiver is on and connected to network
3. Check firewall rules on both ends
4. Test manual telnet connection first
5. Ensure receiver not busy with other operations
6. Try setup again after receiver restart
7. Check network latency with ping test

## For Developers

### Local Development

1. **Clone and setup:**
   ```bash
   git clone https://github.com/mase1981/uc-intg-anthemav.git
   cd uc-intg-anthemav
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

2. **Configuration:**
   ```bash
   # Windows PowerShell
   $env:UC_CONFIG_HOME = "./config"
   
   # Linux/Mac
   export UC_CONFIG_HOME=./config
   ```

3. **Run development:**
   ```bash
   python -m uc_intg_anthemav.driver
   ```

4. **VS Code debugging:**
   - Open project in VS Code
   - Use F5 to start debugging session
   - Configure integration with real Anthem receiver or simulator

### Testing with Simulator

A complete Anthem receiver simulator is included for development:

```bash
# Run simulator (listens on port 14999)
python anthem_simulator.py

# In another terminal, run integration
python -m uc_intg_anthemav.driver
```

**Simulator Features:**
- Emulates Anthem MRX 1140 with 3 zones
- Responds to all standard commands
- Realistic power, volume, mute, input control
- Zone-independent operation
- TCP connection handling

### Project Structure

```
uc-intg-anthemav/
├── uc_intg_anthemav/          # Main package
│   ├── __init__.py            # Package info
│   ├── client.py              # Anthem TCP protocol client
│   ├── config.py              # Configuration management
│   ├── driver.py              # Main integration driver
│   ├── media_player.py        # Media player entity
│   └── setup.py               # Setup flow handler
├── .github/workflows/         # GitHub Actions CI/CD
│   └── build.yml              # Automated build pipeline
├── .vscode/                   # VS Code configuration
│   └── launch.json            # Debug configuration
├── anthem_simulator.py        # Development simulator
├── docker-compose.yml         # Docker deployment
├── Dockerfile                 # Container build instructions
├── driver.json                # Integration metadata
├── requirements.txt           # Dependencies
├── pyproject.toml             # Python project config
└── README.md                  # This file
```

### Key Implementation Details

#### **Anthem TCP Protocol**
- Uses TCP for all communication (port 14999)
- Text-based ASCII protocol
- Commands terminated with carriage return (`\r`)
- Persistent connection with keepalive
- Automatic reconnection on disconnect

#### **Command Format**
```
Z[zone][command][value]\r
```

**Examples:**
```
Z1POW1       # Zone 1 Power On
Z1POW0       # Zone 1 Power Off
Z1VOL-40     # Zone 1 Volume -40dB
Z1VUP        # Zone 1 Volume Up
Z1VDN        # Zone 1 Volume Down
Z1MUT1       # Zone 1 Mute On
Z1INP3       # Zone 1 Select Input 3
Z1POW?       # Zone 1 Query Power
IDM?         # Query Device Model
```

#### **Response Format**
Responses match command format:
```
Z1POW1       # Zone 1 is powered on
Z1VOL-40     # Zone 1 volume is -40dB
IDMMRX 1140  # Device model is MRX 1140
```

#### **Multi-Device Architecture**
- Each receiver = separate TCP client instance
- Independent connections per device
- Separate media_player entity per zone
- Device ID = `anthem_{ip_with_underscores}_{port}`
- Zone ID = `anthem_{device_id}_zone{number}`

#### **Volume Scaling**
```python
# Receiver range: -90dB to 0dB (90 steps)
# Remote range: 0-100 (percentage)
# Formula: volume_percent = (db_value + 90) / 90 * 100
# Reverse: db_value = (volume_percent * 90 / 100) - 90
```

#### **Reboot Survival Pattern**
```python
# Pre-initialize entities if config exists
if config.is_configured():
    await _initialize_integration()

# Reload config on reconnect
async def on_connect():
    config.reload_from_disk()
    if not entities_ready:
        await _initialize_integration()

# Race condition protection
async def on_subscribe_entities(entity_ids):
    if not entities_ready:
        await _initialize_integration()
```

### Anthem Protocol Reference

Essential commands used by this integration:

```python
# Device Information
"IDM?"           # Query model
"IDN?"           # Query device name
"IDR?"           # Query region
"IDS?"           # Query software version

# Zone Power Control
"Z1POW1"         # Zone 1 power on
"Z1POW0"         # Zone 1 power off
"Z1POW?"         # Zone 1 query power

# Zone Volume Control
"Z1VOL-40"       # Set zone 1 volume to -40dB
"Z1VUP"          # Zone 1 volume up 1dB
"Z1VDN"          # Zone 1 volume down 1dB
"Z1VOL?"         # Query zone 1 volume

# Zone Mute Control
"Z1MUT1"         # Zone 1 mute on
"Z1MUT0"         # Zone 1 mute off
"Z1MUT?"         # Query zone 1 mute

# Zone Input Selection
"Z1INP1"         # Zone 1 select input 1 (HDMI 1)
"Z1INP9"         # Zone 1 select input 9 (Analog 1)
"Z1INP?"         # Query zone 1 input

# Input Name Query
"Z1SIP?"         # Query zone 1 selected input name

# Audio Format Query
"Z1AIC?"         # Query zone 1 audio input codec

# Echo Control
"ECH0"           # Disable command echo
"ECH1"           # Enable command echo
```

### Testing Protocol

#### **Connection Testing**
```python
# Test TCP connection
client = AnthemClient(device_config)
success = await client.connect()
assert success is True
assert client.is_connected
```

#### **Command Testing**
```python
# Test power control
await client.power_on(zone=1)
await asyncio.sleep(0.5)
state = client.get_zone_state(1)
assert state.get("power") is True

# Test volume control
await client.set_volume(-30, zone=1)
await asyncio.sleep(0.5)
state = client.get_zone_state(1)
assert state.get("volume") == -30
```

#### **Multi-Zone Testing**
```python
# Test independent zone control
await client.power_on(zone=1)
await client.power_off(zone=2)
await asyncio.sleep(0.5)
zone1 = client.get_zone_state(1)
zone2 = client.get_zone_state(2)
assert zone1.get("power") is True
assert zone2.get("power") is False
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test with real Anthem receiver or simulator
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Code Style

- Follow PEP 8 Python conventions
- Use type hints for all functions
- Async/await for all I/O operations
- Comprehensive docstrings
- Descriptive variable names
- Header comments only (no inline comments)

## Credits

- **Developer**: Meir Miyara
- **Anthem**: High-performance A/V receivers and processors
- **Unfolded Circle**: Remote 2/3 integration framework (ucapi)
- **Protocol**: Anthem TCP/IP text-based control protocol
- **Community**: Testing and feedback from UC community

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0) - see LICENSE file for details.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-anthemav/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community//)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)
- **Anthem Support**: [Official Anthem Support](https://anthemav.com/support/)

---

**Made with ❤️ for the Unfolded Circle and Anthem Communities** 

**Thank You**: Meir Miyara
