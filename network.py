import digitalio
import busio
import board
from PIL import Image, ImageDraw, ImageFont
from adafruit_epd.ssd1680 import Adafruit_SSD1680
import requests
import subprocess
import netifaces
from concurrent.futures import ThreadPoolExecutor

# Define some color constants
WHITE = (0xFF, 0xFF, 0xFF)
BLACK = (0x00, 0x00, 0x00)

# Define constants for easy resizing of shapes and colors
FONTSIZE = 20
BACKGROUND_COLOR = WHITE
TEXT_COLOR = BLACK
WLAN_INTERFACE = 'wlan0'


# Get local IP address from Ethernet interface
def get_local_ip(interface='eth0'):
    try:
        local_info = netifaces.ifaddresses(interface)
        return local_info[netifaces.AF_INET][0]['addr']
    except (ValueError, KeyError):
        return "Not Connected"


# Get WLAN IP address
def get_wlan_ip(interface=WLAN_INTERFACE):
    try:
        wlan_info = netifaces.ifaddresses(interface)
        return wlan_info[netifaces.AF_INET][0]['addr']
    except (ValueError, KeyError):
        return "Not Connected"


# Function to get WAN IP (public IP)
def get_wan_ip():
    try:
        response = requests.get('https://api64.ipify.org?format=json', timeout=3)
        if response.status_code == 200:
            return response.json()['ip']
        return "No Internet"
    except requests.RequestException:
        return "No Internet"


# Run a command and return its stdout (empty string on any failure)
def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            return result.stdout
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""


# Get the SSID of the connected Wi-Fi network (tries several tools)
def get_ssid(interface=WLAN_INTERFACE):
    # 1) iwgetid (wireless-tools)
    ssid = run_cmd(['iwgetid', interface, '-r']).strip()
    if ssid:
        return ssid

    # 2) iw
    for line in run_cmd(['iw', 'dev', interface, 'link']).splitlines():
        line = line.strip()
        if line.startswith("SSID:"):
            ssid = line.split("SSID:", 1)[1].strip()
            if ssid:
                return ssid

    # 3) NetworkManager
    for line in run_cmd(['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi']).splitlines():
        if line.startswith("yes:"):
            ssid = line[4:].replace("\\:", ":").strip()
            if ssid:
                return ssid

    return "Not Connected"


# Start the slow WAN lookup in the background right away
executor = ThreadPoolExecutor(max_workers=1)
wan_future = executor.submit(get_wan_ip)

# While that runs, set up the display
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

# Load a TTF Font
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', FONTSIZE)

# Local lookups are quick
local_ip = get_local_ip()
wlan_ip = get_wlan_ip()
ssid = get_ssid()

# Collect the background result
wan_ip = wan_future.result()
executor.shutdown()

# Define the text to display
wan_text = f"WAN: {wan_ip}"
local_text = f"LAN: {local_ip}"
wlan_text = f"WLAN: {wlan_ip}"
ssid_text = f"SSID: {ssid}"

# Shorten the SSID line with "..." if it is too wide for the screen
max_width = display.width - 6
while draw.textbbox((0, 0), ssid_text, font=font)[2] > max_width and len(ssid_text) > 8:
    ssid_text = ssid_text[:-4] + "..."

# Calculate text sizes and positions
bbox_wan = draw.textbbox((0, 0), wan_text, font=font)
bbox_local = draw.textbbox((0, 0), local_text, font=font)
bbox_wlan = draw.textbbox((0, 0), wlan_text, font=font)
bbox_ssid = draw.textbbox((0, 0), ssid_text, font=font)

# Set fixed padding value
fixed_padding = 13  # Adjust this value for desired spacing

# Set positions for the WAN, Local IP, WLAN IP, and SSID
wan_position = (3, 10)
local_position = (3, 10 + bbox_wan[3] - bbox_wan[1] + fixed_padding)
wlan_position = (3, 10 + bbox_wan[3] - bbox_wan[1] + bbox_local[3] - bbox_local[1] + 2 * fixed_padding)
ssid_position = (3, 10 + bbox_wan[3] - bbox_wan[1] + bbox_local[3] - bbox_local[1] + bbox_wlan[3] - bbox_wlan[1] + 3 * fixed_padding)

# Draw the text on the display
draw.text(wan_position, wan_text, font=font, fill=TEXT_COLOR)
draw.text(local_position, local_text, font=font, fill=TEXT_COLOR)
draw.text(wlan_position, wlan_text, font=font, fill=TEXT_COLOR)
draw.text(ssid_position, ssid_text, font=font, fill=TEXT_COLOR)

# Display image
display.image(image)
display.display()