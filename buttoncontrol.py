import board
import digitalio
import os
import subprocess
import sys
import time

# ---------------- Settings ----------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))  # folder this file lives in
FLIP_INTERVAL = 180           # seconds between automatic screen flips (3 minutes)
LONG_PRESS_DURATION = 3       # seconds to hold for a long press
SCRIPT_TIMEOUT = 120          # kill a display script that hangs
DEFAULT_SCREEN = "info.py"    # matches what eink-init.sh shows at boot

# Screens that auto-flip, in order
SCREENS = ["network.py", "info.py"]

# Define the button pins
button_1 = digitalio.DigitalInOut(board.D6)  # Button Top
button_2 = digitalio.DigitalInOut(board.D5)  # Button Bottom

# Set up buttons as inputs with pull-ups enabled
button_1.switch_to_input(pull=digitalio.Pull.UP)
button_2.switch_to_input(pull=digitalio.Pull.UP)

# (name, button, short-press script, long-press script)
BUTTONS = [
    ("Button 1", button_1, "network.py", "shutdown.py"),
    ("Button 2", button_2, "info.py", "reboot.py"),
]


# Run a script with the same Python that is running this file
def run_script(script_name):
    path = os.path.join(SCRIPT_DIR, script_name)
    try:
        result = subprocess.run([sys.executable, path], timeout=SCRIPT_TIMEOUT)
        if result.returncode != 0:
            print(f"{script_name} exited with code {result.returncode}")
    except subprocess.TimeoutExpired:
        print(f"{script_name} timed out after {SCRIPT_TIMEOUT}s and was stopped")
    except OSError as e:
        print(f"Could not run {script_name}: {e}")


# Call only when the button is already pressed.
# Waits for release and returns True if it was a long press.
def read_press(button):
    start = time.monotonic()
    long_press = False
    while not button.value:
        if not long_press and time.monotonic() - start >= LONG_PRESS_DURATION:
            long_press = True
        time.sleep(0.01)
    return long_press


# Return the screen that comes after the current one
def next_screen(current):
    if current in SCREENS:
        return SCREENS[(SCREENS.index(current) + 1) % len(SCREENS)]
    return SCREENS[0]


# ---------------- Main loop ----------------
current_screen = DEFAULT_SCREEN
last_change = time.monotonic()

while True:
    for name, button, short_script, long_script in BUTTONS:
        if not button.value:  # Button pressed
            if read_press(button):
                print(f"{name} Long Pressed.")
                print(f"Running {long_script}")
                run_script(long_script)
            else:
                print(f"{name} Short Pressed.")
                print(f"Running {short_script}")
                run_script(short_script)
                current_screen = short_script  # remember what's on screen
            last_change = time.monotonic()     # restart the flip timer
            break
    else:
        # No button was pressed: flip to the other screen if it's time
        if time.monotonic() - last_change >= FLIP_INTERVAL:
            current_screen = next_screen(current_screen)
            print(f"Auto-flipping to {current_screen}")
            run_script(current_screen)
            last_change = time.monotonic()

    time.sleep(0.1)