# Adafruit-SSD1680

A small status display for Raspberry Pi using an SSD1680-based 2.13" (250x122) e-paper screen with two buttons. It shows system stats and network info, flips between screens automatically, and gives you physical buttons to shut down or reboot the Pi.

## Features

- **System screen** (`info.py`): CPU usage, RAM, disk, temperature, uptime
- **Network screen** (`network.py`): WAN IP, LAN IP, WLAN IP, Wi-Fi SSID
- **Auto-flip:** alternates between the two screens every 3 minutes
- **Button control:** short press switches screens, long press shuts down or reboots
- **Shutdown screen:** shows the hostname, last known IP address(es) and the date/time, and stays on the display while the Pi is off (e-paper keeps its image without power)
- **Reboot screen:** stays visible until the Pi is back up
- **Runs at boot** via cron, with logging to `eink.log`

## Hardware

- Raspberry Pi, anything from the Zero W up to the Pi 5
- SSD1680 2.13" e-paper display with two buttons (for example an Adafruit 2.13" eInk bonnet)
    * https://www.adafruit.com/product/4687

| Function | Pin |
| --- | --- |
| SPI chip select | CE0 |
| Data/command (DC) | GPIO 22 |
| Reset (RST) | GPIO 27 |
| Busy | GPIO 17 |
| Top button | GPIO 6 |
| Bottom button | GPIO 5 |

If your display or buttons are wired differently, change the pins at the top of each script.

## Requirements

- Raspberry Pi OS (developed on Debian 13 "Trixie")
- Python 3 (the installer creates a virtual environment)
- Internet access for the installer, and for the WAN IP lookup (via ipify) at runtime

## Installation

Clone the repository into your home directory and run the installer **as a normal user, not with sudo**:

```bash
cd ~
git clone https://github.com/<your-username>/adafruit-ssd1680.git
cd adafruit-ssd1680
chmod +x install.sh
./install.sh
sudo reboot
```

The installer:

1. Installs the needed Debian packages (fonts, i2c tools, GPIO libraries, Pillow)
2. Enables SPI, I2C and the other interfaces through `raspi-config`
3. Creates a virtual environment at `~/adafruit-ssd1680/env` and installs the Python packages (it uses `rpi-lgpio` on a Pi 5)
4. Adds a cron `@reboot` entry that runs `adafruit-ssd1680/eink-init.sh`
5. Adds a sudoers rule (see below) so the buttons can power off and reboot the Pi
6. Checks that the key Python imports work

## Usage

| Button | Short press | Long press (3 s) |
| --- | --- | --- |
| Top (GPIO 6) | Network screen | Shut down |
| Bottom (GPIO 5) | System info screen | Reboot |

After boot it shows the system info screen. If nothing is pressed, it flips to the other screen every 3 minutes. Pressing a button restarts that timer.

## Project layout

```
adafruit-ssd1680/
├── install.sh              # installer
│   ├── eink-init.sh        # started at boot by cron
│   ├── buttoncontrol.py    # button loop and auto-flip timer
│   ├── info.py             # system stats screen
│   ├── network.py          # network info screen
│   ├── shutdown.py         # draws the power-off screen, then shuts down
│   └── reboot.py           # draws the reboot screen, then reboots
├── env/                    # Python virtual environment (created by install.sh)
└── eink.log                # runtime log, recreated at each boot
```

## Configuration

- **Flip interval:** `FLIP_INTERVAL` in `buttoncontrol.py` (seconds)
- **First screen at boot:** `DEFAULT_SCREEN` in `buttoncontrol.py`, and the script that `eink-init.sh` runs first
- **Long-press time:** `LONG_PRESS_DURATION` in `buttoncontrol.py`
- **Font size and spacing:** `FONTSIZE` and the gap or margin settings at the top of each screen script
- **Screen position:** on some panels or library versions the top rows are cut off. The scripts start text 10 px from the top for this reason, and `info.py` also has `X_OFFSET` / `Y_OFFSET` to shift the whole image.
- **Network interfaces:** the scripts use `eth0` and `wlan0`; change them if your interface names differ

## About the sudoers rule

The buttons run as your normal user, so shutting down needs `sudo` without a password prompt. The installer creates `/etc/sudoers.d/eink` for the user who runs it, allowing **only** these two commands:

```
<user> ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff, /usr/bin/systemctl reboot
```

The rule is validated with `visudo` before it's installed. To remove it:

```bash
sudo rm /etc/sudoers.d/eink
```

## Troubleshooting

- **Check the log:** `tail -n 50 ~/adafruit-ssd1680/eink.log`
- **Run a screen by hand:** `~/adafruit-ssd1680/env/bin/python ~/adafruit-ssd1680/info.py`
- **Nothing happens at boot:** check that the cron entry exists with `crontab -l` and that `eink-init.sh` is executable
- **Shutdown or reboot button does nothing:** confirm the sudoers rule works with `sudo -n -l systemctl reboot`, which should print the command instead of asking for a password
- **Blank or garbled display:** make sure SPI is enabled (`sudo raspi-config nonint do_spi 0`) and check the pin wiring
- **"No Internet" or no SSID:** the network screen needs an active connection; the SSID line uses `iwgetid`, `iw` or `nmcli`

## Uninstall

```bash
crontab -l | grep -v "eink-init.sh" | crontab -
sudo rm -f /etc/sudoers.d/eink
rm -rf ~/adafruit-ssd1680
```

## Notes

- The network screen looks up your public IP through [ipify](https://www.ipify.org/). If you'd rather not make that request, remove the WAN lookup from `network.py`.
- E-paper holds its last image with no power. If you leave a Pi off for a long time, consider showing a blank screen rather than leaving one image up indefinitely.
