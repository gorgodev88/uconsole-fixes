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
