import digitalio
import busio
import board
import time
import subprocess
import sys
import socket
import netifaces
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from adafruit_epd.ssd1680 import Adafruit_SSD1680

# Define some color constants
WHITE = (0xFF, 0xFF, 0xFF)
BLACK = (0x00, 0x00, 0x00)

# Settings
FONTSIZE = 20
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD_FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
BACKGROUND_COLOR = WHITE
TEXT_COLOR = BLACK
TOP_MARGIN = 10      # keeps the first line clear of the cut-off top rows
BOTTOM_MARGIN = 4
LEFT_MARGIN = 3      # distance from the left edge for left-aligned text
SIDE_MARGIN = 3

# Vertical gaps (pixels). Tweak these to taste.
TITLE_GAP = 15       # POWER OFF -> Host
HOST_IP_GAP = 6      # Host -> first IP line
IP_IP_GAP = 6        # LAN -> WLAN (when both are shown)
IP_DATE_GAP = 20     # last IP line -> date/time


# Get the IPv4 address of an interface, or None if it has none
def get_ip(interface):
    try:
        return netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
    except (ValueError, KeyError):
        return None


# Format the date/time like: 10/9/26 10:00am
def format_datetime(now):
    hour = now.hour % 12 or 12
    suffix = "am" if now.hour < 12 else "pm"
    return f"{now.month}/{now.day}/{now.year % 100} {hour}:{now.minute:02d}{suffix}"


# Load a font, falling back to the regular one if the bold file is missing
def load_font(bold, size):
    if bold:
        try:
            return ImageFont.truetype(BOLD_FONT_PATH, size)
        except OSError:
            pass
    return ImageFont.truetype(FONT_PATH, size)


# Shrink the font only if a line is too wide for the screen
def fit_font(draw, text, max_width, bold=False):
    size = FONTSIZE
    while True:
        font = load_font(bold, size)
        width = draw.textbbox((0, 0), text, font=font)[2]
        if width <= max_width or size <= 10:
            return font
        size -= 1


# Create the SPI device and pins we will need
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
ecs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D22)
srcs = None
rst = digitalio.DigitalInOut(board.D27)
busy = digitalio.DigitalInOut(board.D17)

# Display driver 2.13" HD Tri-color or mono display
display = Adafruit_SSD1680(
    122,
    250,
    spi,
    cs_pin=ecs,
    dc_pin=dc,
    sramcs_pin=srcs,
    rst_pin=rst,
    busy_pin=busy,
)

# Rotate the screen
display.rotation = 3

# Create a new image with a plain white background (no border)
image = Image.new("RGB", (display.width, display.height), BACKGROUND_COLOR)
draw = ImageDraw.Draw(image)

# Gather the info to show (last known values at the moment of shutdown)
lan_ip = get_ip('eth0')
wlan_ip = get_ip('wlan0')
hostname = socket.gethostname()

# (text, alignment, bold, gap above this line) in top-to-bottom order
lines = [
    ("POWER OFF", "center", True, 0),
    (f"Host: {hostname}", "left", False, TITLE_GAP),
]

ip_lines = []
if lan_ip:
    ip_lines.append(f"LAN: {lan_ip}")
if wlan_ip:
    ip_lines.append(f"WLAN: {wlan_ip}")
if not lan_ip and not wlan_ip:
    ip_lines.append("IP: None")

for i, text in enumerate(ip_lines):
    lines.append((text, "left", False, HOST_IP_GAP if i == 0 else IP_IP_GAP))

lines.append((format_datetime(datetime.now()), "center", False, IP_DATE_GAP))

# Measure every line first
max_width = display.width - 2 * SIDE_MARGIN
items = []
for text, align, bold, gap_above in lines:
    font = fit_font(draw, text, max_width, bold)
    bbox = draw.textbbox((0, 0), text, font=font)
    items.append((text, align, font, bbox, gap_above))

# If everything doesn't fit, scale all gaps down proportionally
total_text_height = sum(b[3] - b[1] for _, _, _, b, _ in items)
total_gaps = sum(g for _, _, _, _, g in items)
available = display.height - TOP_MARGIN - BOTTOM_MARGIN - total_text_height
scale = min(1.0, available / total_gaps) if total_gaps > 0 else 1.0

# Draw each line
y = TOP_MARGIN
for text, align, font, bbox, gap_above in items:
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    y += max(round(gap_above * scale), 1 if gap_above else 0)

    if align == "center":
        x = (display.width - text_width) // 2 - bbox[0]
    else:
        x = LEFT_MARGIN - bbox[0]

    draw.text((x, y - bbox[1]), text, font=font, fill=TEXT_COLOR)
    y += text_height

# Display image
display.image(image)
display.display()

# Wait a moment to show the message
time.sleep(2)

# Shut down the system (-n: fail immediately instead of waiting for a password)
result = subprocess.run(["sudo", "-n", "systemctl", "poweroff"], capture_output=True, text=True)
if result.returncode != 0:
    print(f"poweroff failed ({result.returncode}): {result.stderr.strip()}")
    sys.exit(1)