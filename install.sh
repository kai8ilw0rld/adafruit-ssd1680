#!/bin/bash
set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Paths: the project folder is wherever this script lives
PROJECT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
EINK_DIR="$PROJECT_DIR"
VENV_DIR="$PROJECT_DIR/env"
SUDOERS_FILE="/etc/sudoers.d/eink"

echo -e "${BLUE}Starting installation script...${NC}"

# Don't run as root (venv and crontab must belong to the normal user)
if [ "$(id -u)" -eq 0 ]; then
    echo -e "${RED}Error: Run this script as a normal user, not with sudo. It calls sudo where needed.${NC}"
    exit 1
fi

# Check the required project files exist before touching anything
for f in eink-init.sh buttoncontrol.py info.py network.py shutdown.py reboot.py; do
    if [ ! -f "$EINK_DIR/$f" ]; then
        echo -e "${RED}Error: $EINK_DIR/$f not found.${NC}"
        exit 1
    fi
done
echo -e "${GREEN}Project files found in $EINK_DIR.${NC}"

# Detect Pi model (Pi 5 needs rpi-lgpio instead of RPi.GPIO)
PI_MODEL="$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo unknown)"
IS_PI5=0
if [[ "$PI_MODEL" == *"Raspberry Pi 5"* ]]; then
    IS_PI5=1
fi
echo -e "${BLUE}Detected board: ${PI_MODEL}${NC}"

# Make the boot script executable
chmod +x "$EINK_DIR/eink-init.sh"
echo -e "${BLUE}Permissions changed.${NC}"

# Debian dependencies
echo -e "${MAGENTA}Installing Debian dependencies...${NC}"
sudo apt-get update
sudo apt-get install -y --upgrade python3-setuptools
sudo apt-get install -y python3-pip python3-venv python3-dev \
    fonts-dejavu i2c-tools libgpiod-dev python3-libgpiod python3-lgpio python3-pil
echo -e "${MAGENTA}Debian dependencies installed.${NC}"

# Raspberry Pi interface settings (some options don't exist on newer OS versions)
echo -e "${BLUE}Configuring Raspberry Pi settings...${NC}"
sudo raspi-config nonint do_i2c 0 || echo -e "${YELLOW}Warning: could not enable I2C.${NC}"
sudo raspi-config nonint do_spi 0 || echo -e "${YELLOW}Warning: could not enable SPI.${NC}"
sudo raspi-config nonint do_serial_hw 0 || echo -e "${YELLOW}Warning: could not enable serial hardware.${NC}"
sudo raspi-config nonint do_ssh 0 || echo -e "${YELLOW}Warning: could not enable SSH.${NC}"
sudo raspi-config nonint do_camera 0 2>/dev/null || echo -e "${YELLOW}Skipping camera setting (not available on this OS).${NC}"
sudo raspi-config nonint disable_raspi_config_at_boot 0 || true
echo -e "${BLUE}Raspberry Pi settings configured.${NC}"

# Virtual environment (system site packages so the apt-installed lgpio is used,
# which avoids compiling it from source)
echo -e "${GREEN}Creating Python virtual environment...${NC}"
python3 -m venv --system-site-packages "$VENV_DIR"
echo -e "${GREEN}Virtual environment created at $VENV_DIR.${NC}"

# Install pip packages using the venv's own pip (no activation needed)
echo -e "${CYAN}Installing pip packages...${NC}"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install --upgrade \
    RPi.GPIO adafruit-blinka \
    adafruit-python-shell adafruit-circuitpython-epd \
    Pillow psutil requests netifaces

# On Pi 5, RPi.GPIO doesn't work; swap it for the compatible rpi-lgpio
if [ "$IS_PI5" -eq 1 ]; then
    echo -e "${CYAN}Pi 5 detected: replacing RPi.GPIO with rpi-lgpio...${NC}"
    "$VENV_DIR/bin/pip" uninstall -y RPi.GPIO || true
    "$VENV_DIR/bin/pip" install --upgrade rpi-lgpio
fi
echo -e "${CYAN}Pip packages installed.${NC}"

# Cron job
CRON_JOB="@reboot $EINK_DIR/eink-init.sh"
if crontab -l 2>/dev/null | grep -Fxq "$CRON_JOB"; then
    echo -e "${YELLOW}Cron job already exists.${NC}"
else
    echo -e "${BLUE}Adding cron job to run eink-init.sh at reboot...${NC}"
    (crontab -l 2>/dev/null || true; echo "$CRON_JOB") | crontab -
    echo -e "${BLUE}Cron job added.${NC}"
fi

# Allow the button scripts to power off / reboot without a password prompt.
# Works for whichever user runs this installer, and only allows these two commands.
CURRENT_USER="$(id -un)"
SYSTEMCTL="$(readlink -f "$(command -v systemctl)")"
echo -e "${BLUE}Allowing ${CURRENT_USER} to run poweroff/reboot without a password...${NC}"
SUDOERS_TMP="$(mktemp)"
echo "${CURRENT_USER} ALL=(root) NOPASSWD: ${SYSTEMCTL} poweroff, ${SYSTEMCTL} reboot" > "$SUDOERS_TMP"
# Validate the rule first so a typo can never break sudo
if sudo visudo -cf "$SUDOERS_TMP" > /dev/null; then
    sudo install -m 440 -o root -g root "$SUDOERS_TMP" "$SUDOERS_FILE"
    echo -e "${GREEN}Sudoers rule installed at $SUDOERS_FILE.${NC}"
else
    rm -f "$SUDOERS_TMP"
    echo -e "${RED}Error: sudoers rule failed validation and was not installed.${NC}"
    exit 1
fi
rm -f "$SUDOERS_TMP"

# Verify the key imports work
echo -e "${BLUE}Verifying installation...${NC}"
"$VENV_DIR/bin/python" -c "import lgpio, board, adafruit_epd, PIL; print('Imports OK')"

echo -e "${MAGENTA}Installation complete. A reboot is recommended so interface changes take effect.${NC}"