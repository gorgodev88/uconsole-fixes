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

Add a check against the kernel's ALSA PCM status files:

```
/proc/asound/card*/pcm*p/sub*/status
```

These files are maintained by the kernel and report `state: RUNNING` only while audio is actively being played back. They require no PulseAudio or PipeWire connection and are readable by a system service running as root.

**New logic:**
- If headphones are plugged in → amp OFF
- If no headphones AND audio is playing → amp ON
- If no headphones AND audio is silent/stopped → amp OFF
- If the headphone-jack GPIO can't be read reliably → amp OFF (fail safe)

The amp is only powered when it is actually needed, eliminating the EMI pickup during silence. The replacement script checks *every* playback substream on *every* sound card, so it keeps working even if the analog output is not card 0 (for example when a USB audio device grabs a lower card number at boot).

### Trade-offs (read before applying)

- **Sound onset is clipped.** The amp powers up on the first poll *after* playback starts, so up to ~0.5 s of the beginning of a sound plays into a disabled amp. Very short notification beeps can be inaudible entirely. If you rely on system notification sounds, this fix may not be for you.
- **The amp turns off a few seconds after audio ends, not instantly.** Under PipeWire/WirePlumber the PCM stays in `RUNNING` for the node suspend timeout (~5 s by default) after playback stops, so expect roughly that much delay before the amp drops. If you've set WirePlumber's `session.suspend-timeout-seconds = 0` (a common anti-pop tweak), the PCM never leaves `RUNNING` and **this fix will do nothing** — the amp will stay on, as stock.
- **HDMI corner case:** because the script treats playback on *any* card as "audio playing," playing audio over HDMI also powers the speaker amp. During HDMI playback you get stock behavior (amp on, possible idle static from the speakers).

---

## Step-by-Step Instructions

### Step 0 — Check the prerequisites

This fix replaces a file installed by the stock `clockworkpi-audio` package. Confirm it's present:

```bash
systemctl cat clockworkpi-audio-patch.service   # should print the unit
ls /usr/local/bin/audio_3.5_patch.py            # should exist
```

If either is missing, your image doesn't use this mechanism and this fix doesn't apply as written.

### Step 1 — Back up the original script

```bash
sudo cp /usr/local/bin/audio_3.5_patch.py /usr/local/bin/audio_3.5_patch.py.bak
```

### Step 2 — Replace the script

If you cloned this repo:

```bash
sudo install -m 0644 audio_3.5_patch.py /usr/local/bin/audio_3.5_patch.py
```

Otherwise copy the script from the [Fixed Script](#fixed-script) section below into `/usr/local/bin/audio_3.5_patch.py` (e.g. with `sudo nano`).

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
- **Play audio:** Speakers activate within ~0.5 seconds (the first instant of sound is clipped — see trade-offs).
- **Audio stops:** Speakers go silent once the audio server suspends the stream (~5 s under stock PipeWire).
- **Plug in headphones:** Audio switches to headphones; speakers disabled.

---

## Fixed Script

`/usr/local/bin/audio_3.5_patch.py` — the same file is tracked in this directory as [`audio_3.5_patch.py`](audio_3.5_patch.py):

```python
import glob
import subprocess
import time


def pinctrl(*args):
    return subprocess.run(
        ["pinctrl", *args], capture_output=True, text=True
    )


def init_gpio():
    pinctrl("set", "11", "op", "dl")
    pinctrl("set", "10", "ip", "pn")


def is_audio_playing():
    # Check every playback substream on every card, so the fix keeps
    # working even if the analog output is not card0 (e.g. a USB audio
    # device grabbed a lower card number at boot).
    for path in glob.glob("/proc/asound/card*/pcm*p/sub*/status"):
        try:
            with open(path) as f:
                if "state: RUNNING" in f.read():
                    return True
        except OSError:
            continue
    return False


def headphones_inserted():
    # pinctrl prints e.g. "10: ip    pn | hi // GPIO10 = input".
    # Only trust the level if the pin is actually in input mode; anything
    # unrecognized returns None so the caller fails safe (amp off).
    out = pinctrl("10").stdout
    if " ip " not in out:
        return None
    if "| hi" in out:
        return True
    if "| lo" in out:
        return False
    return None


def set_amp(on):
    # "op" re-asserts the pin direction on every write, so a failed
    # init_gpio() heals itself on the first successful amp write.
    return pinctrl("set", "11", "op", "dh" if on else "dl").returncode == 0


def main():
    init_gpio()
    amp_on = None  # unknown until the first confirmed write
    while True:
        headphones = headphones_inserted()
        if headphones is None:
            init_gpio()  # try to reclaim a misconfigured jack-detect pin
            amp_on = None  # init drove GPIO11 low; cached state is stale
        want_amp = headphones is False and is_audio_playing()
        # Only cache the new state after pinctrl confirms the write, so a
        # failed amp-off is retried on the next poll instead of being
        # remembered as done.
        if want_amp != amp_on and set_amp(want_amp):
            amp_on = want_amp
        time.sleep(0.5)


main()
```

---

## What Changed vs. the Original

| | Original | Fixed |
|---|---|---|
| Amp when idle (no audio) | **ON** (causes static) | **OFF** |
| Amp when audio playing | ON | ON |
| Amp when headphones in | OFF | OFF |
| Amp when jack state unreadable | last state | **OFF** (fail safe) |
| Poll interval | 1.0s | 0.5s |
| Audio detection method | None | ALSA PCM status (`/proc/asound/card*/pcm*p/sub*/status`) |
| GPIO writes | every loop | only on state change |

---

## Hardware Reference

| GPIO | Function |
|---|---|
| GPIO10 | 3.5mm headphone jack detect (input, pull-none) — LOW = no headphones, HIGH = headphones inserted |
| GPIO11 | Speaker amplifier enable (output) — HIGH = amp on, LOW = amp off |

---

## Compatibility

Tested on:
- ClockworkPi uConsole CM5 (BCM2712, kernel 6.12.x)
- `clockworkpi-audio` package v1.1
- PipeWire audio server

Should also work on CM4 (`clockworkpi-uconsole` overlay), since the GPIO assignments are the same and the ALSA playback status is discovered by globbing rather than hard-coding a card number — but CM4 is untested by the author.

**Note:** `/usr/local/bin/audio_3.5_patch.py` belongs to the `clockworkpi-audio` package. If that package is upgraded or reinstalled, it may silently restore the stock script — re-apply Step 2 afterwards.

---

## Troubleshooting

- **No speaker audio at all after applying:** check `cat /proc/asound/cards` and `ls /proc/asound/card*/pcm*p/sub*/status`. If no playback status file exists, the script can never see audio as "playing" and will keep the amp off. Revert (below) and file an issue with your `/proc/asound/cards` output.
- **Speakers stay silent for quiet/short sounds:** expected — see trade-offs above.
- **Static returned after an OS update:** the package likely restored the stock script — re-apply Step 2.

---

## Reverting

To restore the original behaviour:

```bash
sudo cp /usr/local/bin/audio_3.5_patch.py.bak /usr/local/bin/audio_3.5_patch.py
sudo systemctl restart clockworkpi-audio-patch.service
```
