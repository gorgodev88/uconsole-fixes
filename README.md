# Fix: Speaker Static Noise on uConsole (CM4 / CM5)

Fixes the built-in speakers producing static/buzzing noise during keyboard presses and CPU activity when no audio is playing.

---

## The Problem

On the ClockworkPi uConsole, the built-in speaker amplifier is controlled by **GPIO11**. The stock `clockworkpi-audio` package includes a service (`clockworkpi-audio-patch.service`) that runs a Python script (`audio_3.5_patch.py`) to:

- Monitor **GPIO10** for 3.5mm headphone jack insertion
- Enable the speaker amp (GPIO11 HIGH) when no headphones are plugged in
- Disable the speaker amp (GPIO11 LOW) when headphones are inserted

**The bug:** The amp is kept powered **on at all times** when no headphones are plugged in — even during complete silence. A powered-on amplifier picks up electromagnetic interference (EMI) from:

- The keyboard matrix being scanned
- CPU and memory bus activity during process execution
- Other GPIO switching events

This results in audible static, buzzing, or clicking from the speakers whenever keys are held down or processes are running.

---

## Root Cause

The relevant section of the original `/usr/local/bin/audio_3.5_patch.py`:

```python
while True:
    tmp = check_3_5()
    if tmp == "10: ip    pn | lo // GPIO10 = input":
        enable_speaker_gpio()       # <-- amp ON whenever no headphones
    elif tmp == "10: ip    pn | hi // GPIO10 = input":
        disable_speaker_gpio()
    
    time.sleep(1)
```

There is no check for whether audio is actually playing. The amplifier stays on indefinitely, picking up system noise.

---

## The Fix

Add a check against the kernel's ALSA PCM status file:

```
/proc/asound/card0/pcm0p/sub0/status
```

This file is maintained by the kernel and reports `state: RUNNING` only when audio is actively being played back through the speaker output. It requires no PulseAudio or PipeWire connection and is accessible from a system service running as root.

**New logic:**
- If headphones are plugged in → amp OFF
- If no headphones AND audio is playing → amp ON
- If no headphones AND audio is silent/stopped → amp OFF

This means the amp is only powered when it is actually needed, eliminating the EMI pickup during silence.

---

## Step-by-Step Instructions

### Step 1 — Back up the original script

```bash
sudo cp /usr/local/bin/audio_3.5_patch.py /usr/local/bin/audio_3.5_patch.py.bak
```

### Step 2 — Replace the script

```bash
sudo nano /usr/local/bin/audio_3.5_patch.py
```

Delete the existing contents and paste in the fixed script below (see **Fixed Script** section), then save with `Ctrl+O`, `Enter`, `Ctrl+X`.

Or use this one-liner to write it directly:

```bash
sudo tee /usr/local/bin/audio_3.5_patch.py > /dev/null << 'EOF'
import os
import time

ALSA_STATUS = "/proc/asound/card0/pcm0p/sub0/status"

def init_gpio():
    os.popen("pinctrl set 11 op")
    os.popen("pinctrl set 10 ip pn")

def check_3_5():
    tmp = os.popen("pinctrl 10").readline().strip("\n")
    return tmp

def is_audio_playing():
    try:
        with open(ALSA_STATUS) as f:
            return "state: RUNNING" in f.read()
    except OSError:
        return False

def enable_speaker_gpio():
    os.popen("pinctrl set 11 op dh")

def disable_speaker_gpio():
    os.popen("pinctrl set 11 op dl")

init_gpio()

while True:
    headphones_in = check_3_5() == "10: ip    pn | hi // GPIO10 = input"

    if headphones_in or not is_audio_playing():
        disable_speaker_gpio()
    else:
        enable_speaker_gpio()

    time.sleep(0.5)
EOF
```

### Step 3 — Restart the service

```bash
sudo systemctl restart clockworkpi-audio-patch.service
```

### Step 4 — Verify the service is running

```bash
systemctl status clockworkpi-audio-patch.service
```

Expected output should show `Active: active (running)`.

### Step 5 — Test

- **Idle / typing:** No static from speakers.
- **Play audio:** Speakers activate within ~0.5 seconds.
- **Audio stops:** Speakers go silent within ~0.5 seconds.
- **Plug in headphones:** Audio switches to headphones; speakers disabled.

---

## Fixed Script

`/usr/local/bin/audio_3.5_patch.py`

```python
import os
import time

ALSA_STATUS = "/proc/asound/card0/pcm0p/sub0/status"

def init_gpio():
    os.popen("pinctrl set 11 op")
    os.popen("pinctrl set 10 ip pn")

def check_3_5():
    tmp = os.popen("pinctrl 10").readline().strip("\n")
    return tmp

def is_audio_playing():
    try:
        with open(ALSA_STATUS) as f:
            return "state: RUNNING" in f.read()
    except OSError:
        return False

def enable_speaker_gpio():
    os.popen("pinctrl set 11 op dh")

def disable_speaker_gpio():
    os.popen("pinctrl set 11 op dl")

init_gpio()

while True:
    headphones_in = check_3_5() == "10: ip    pn | hi // GPIO10 = input"

    if headphones_in or not is_audio_playing():
        disable_speaker_gpio()
    else:
        enable_speaker_gpio()

    time.sleep(0.5)
```

---

## What Changed vs. the Original

| | Original | Fixed |
|---|---|---|
| Amp when idle (no audio) | **ON** (causes static) | **OFF** |
| Amp when audio playing | ON | ON |
| Amp when headphones in | OFF | OFF |
| Poll interval | 1.0s | 0.5s |
| Audio detection method | None | `/proc/asound/card0/pcm0p/sub0/status` |

---

## Hardware Reference

| GPIO | Function |
|---|---|
| GPIO10 | 3.5mm headphone jack detect (input, pull-none) — LOW = no headphones, HIGH = headphones inserted |
| GPIO11 | Speaker amplifier enable (output) — HIGH = amp on, LOW = amp off |

---

## Compatibility

Tested on:
- ClockworkPi uConsole CM5 (BCM2712, kernel 6.12.67-v8-16k+)
- `clockworkpi-audio` package v1.1
- PipeWire audio server

Should also work on CM4 (`clockworkpi-uconsole` overlay) since the GPIO assignments and ALSA card layout are the same. The ALSA status path (`/proc/asound/card0/pcm0p/sub0/status`) will remain valid as long as the RP1-Audio-Out device is card 0, which is the default in the ClockworkPi kernel.

---

## Reverting

To restore the original behaviour:

```bash
sudo cp /usr/local/bin/audio_3.5_patch.py.bak /usr/local/bin/audio_3.5_patch.py
sudo systemctl restart clockworkpi-audio-patch.service
```
