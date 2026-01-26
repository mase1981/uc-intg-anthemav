# Anthem A/V Receivers Integration for Unfolded Circle Remote 2/3

Control your Anthem A/V receivers and processors (MRX, AVM, STR series) directly from your Unfolded Circle Remote 2 or Remote 3 with comprehensive media player control, **complete multi-zone support**, **source switching**, and **full volume control**.

![Anthem](https://img.shields.io/badge/Anthem-A%2FV%20Receivers-red)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-anthemav?style=flat-square)](https://github.com/mase1981/uc-intg-anthemav/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-anthemav?style=flat-square)](https://github.com/mase1981/uc-intg-anthemav/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-anthemav/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)

---

## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️

---

## Features

This integration provides comprehensive control of Anthem A/V receivers and processors through the Anthem TCP/IP control protocol, delivering seamless integration with your Unfolded Circle Remote for complete home theater control.

### 🎵 **Media Player Control**

#### **Power Management**
- Power On/Off with real-time state feedback
- Power Toggle for quick control
- Multi-Zone Control - independent power per zone (up to 3 zones)

#### **Volume Control**
- Volume Up/Down with precise adjustment
- Direct volume control (-90dB to 0dB)
- Volume slider (0-100 scale)
- Mute Toggle with unmute control
- Per-Zone Volume - independent control for each zone

#### **Source Selection**
- HDMI Inputs (HDMI 1-8)
- Analog Inputs (Analog 1-2)
- Digital Inputs (Digital 1-2 - Coax/Optical)
- HDMI ARC support
- USB and Network streaming
- 7.1 Multichannel analog input

### 🔌 **Multi-Device & Multi-Zone Support**

- **Multiple Receivers** - Control unlimited Anthem receivers on your network
- **Multi-Zone Support** - Up to 3 zones per receiver
- **Individual Configuration** - Each zone gets dedicated media player entity
- **Manual Configuration** - Direct IP address entry
- **Model Detection** - Automatic model identification
- **Zone Naming** - Custom zone names supported

### **Supported Models**

#### **MRX Series** - Receivers
- MRX 520 - 11-channel receiver with Dolby Atmos
- MRX 720 - 11-channel receiver with enhanced processing
- MRX 1120 - 11-channel flagship receiver
- MRX 1140 - 15-channel flagship with advanced features

#### **AVM Series** - Processors
- AVM 60 - 7.1/5.1.2 processor
- AVM 70 - 15.1 processor with Dolby Atmos
- AVM 90 - 16-channel reference processor

#### **STR Series** - Integrated Amplifiers
- All STR models with IP control support

### **Protocol Requirements**

- **Protocol**: Anthem TCP/IP Text-Based Control
- **Control Port**: 14999 (TCP)
- **Network Access**: Receiver must be on same local network
- **Firewall**: TCP port 14999 must be accessible
- **Connection**: Persistent TCP connection with automatic reconnection

## Installation

### Option 1: Remote Web Interface (Recommended)

1. Navigate to the [**Releases**](https://github.com/mase1981/uc-intg-anthemav/releases) page
2. Download the latest `uc-intg-anthemav-<version>-aarch64.tar.gz` file
3. Open your remote's web interface (`http://your-remote-ip`)
4. Go to **Settings** → **Integrations** → **Add Integration**
5. Click **Upload** and select the downloaded `.tar.gz` file

### Option 2: Docker (Advanced Users)

The integration is available as a pre-built Docker image from GitHub Container Registry:

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
3. Click **"Configure"** to begin setup:

#### **Configuration:**
- **IP Address**: Enter receiver IP (e.g., 192.168.1.100)
- **Port**: Default 14999 (change only if customized)
- **Device Name**: Friendly name (e.g., "Living Room Anthem")
- **Model Series**: Select your receiver (MRX, AVM, STR)
- **Number of Zones**: 1-3 zones to configure
- Click **Complete Setup**

#### **Connection Test:**
- Integration verifies receiver connectivity
- Model information retrieved automatically
- Setup fails if receiver unreachable

4. Integration will create media player entity per zone:
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
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)
- **Anthem Support**: [Official Anthem Support](https://anthemav.com/support/)

---

**Made with ❤️ for the Unfolded Circle and Anthem Communities**

**Thank You**: Meir Miyara
