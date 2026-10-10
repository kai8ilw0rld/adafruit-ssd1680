import digitalio
import busio
import board
from PIL import Image, ImageDraw, ImageFont, ImageChops
from adafruit_epd.ssd1680 import Adafruit_SSD1680
import psutil  # For system utilization metrics
import subprocess  # For getting uptime
import os  # For reading temperature

# Define some color constants
WHITE = (0xFF, 0xFF, 0xFF)
BLACK = (0x00, 0x00, 0x00)

# Define some constants for easy resizing of shapes and colors
FONTSIZE = 20
BACKGROUND_COLOR = WHITE
TEXT_COLOR = BLACK

# Image offset to compensate for display shift (pixels)
X_OFFSET = 0
Y_OFFSET = 6

# Create the SPI device and pins needed
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

# Get CPU utilization
cpu_usage = psutil.cpu_percent(interval=1)
cpu_text = f"CPU: {cpu_usage}%"

# Get memory usage
memory_info = psutil.virtual_memory()
memory_usage_mb = memory_info.used // (1024 * 1024)  # Convert to MB
total_memory_mb = memory_info.total // (1024 * 1024)  # Total memory in MB
memory_text = f"RAM: {memory_usage_mb}MB / {total_memory_mb}MB"

# Get disk utilization
disk_info = psutil.disk_usage('/')
disk_usage_gb = disk_info.used // (1024 * 1024 * 1024)  # Used space in GB
total_disk_gb = disk_info.total // (1024 * 1024 * 1024)  # Total disk space in GB
disk_text = f"Disk: {disk_usage_gb}GB / {total_disk_gb}GB"

# Get temperature and format to 1 decimal place
try:
    temp = os.popen("vcgencmd measure_temp").readline()
    temp_value = float(temp.replace("temp=", "").strip().replace("'C", ""))
    temp_text = f"Temp: {temp_value:.1f}°C"
except Exception as e:
    temp_text = "Temp: N/A"

# Get uptime and format it
uptime_seconds = float(subprocess.run(['cut', '-d', ' ', '-f', '1', '/proc/uptime'], capture_output=True, text=True).stdout.strip())
uptime_days = int(uptime_seconds // 86400)
uptime_hours = int((uptime_seconds % 86400) // 3600)
uptime_minutes = int((uptime_seconds % 3600) // 60)

uptime_parts = []
if uptime_days > 0:
    uptime_parts.append(f"{uptime_days}d")
if uptime_hours > 0:
    uptime_parts.append(f"{uptime_hours}h")
uptime_parts.append(f"{uptime_minutes}m")

uptime_text = "Uptime: " + " ".join(uptime_parts)


# Calculate text sizes and positions
bbox_cpu = draw.textbbox((0, 0), cpu_text, font=font)
bbox_mem = draw.textbbox((0, 0), memory_text, font=font)
bbox_disk = draw.textbbox((0, 0), disk_text, font=font)
bbox_temp = draw.textbbox((0, 0), temp_text, font=font)
bbox_uptime = draw.textbbox((0, 0), uptime_text, font=font)

# Set fixed padding value
fixed_padding = 6  # Adjust this value for desired spacing

# Set positions
cpu_position = (3, 5)
mem_position = (3, 5 + bbox_cpu[3] - bbox_cpu[1] + fixed_padding)
disk_position = (3, 5 + bbox_cpu[3] - bbox_cpu[1] + bbox_mem[3] - bbox_mem[1] + 2 * fixed_padding)
temp_position = (3, 5 + bbox_cpu[3] - bbox_cpu[1] + bbox_mem[3] - bbox_mem[1] + bbox_disk[3] - bbox_disk[1] + 3 * fixed_padding)
uptime_position = (3, 2 + bbox_cpu[3] - bbox_cpu[1] + bbox_mem[3] - bbox_mem[1] + bbox_disk[3] - bbox_disk[1] + bbox_temp[3] - bbox_temp[1] + 4 * fixed_padding)

# Draw the text on the display
draw.text(cpu_position, cpu_text, font=font, fill=TEXT_COLOR)
draw.text(mem_position, memory_text, font=font, fill=TEXT_COLOR)
draw.text(disk_position, disk_text, font=font, fill=TEXT_COLOR)
draw.text(temp_position, temp_text, font=font, fill=TEXT_COLOR)
draw.text(uptime_position, uptime_text, font=font, fill=TEXT_COLOR)

# Shift the image to compensate for the display offset (wraps around, nothing is cropped)
image = ImageChops.offset(image, X_OFFSET, Y_OFFSET)

# Display image
display.image(image)
display.display()