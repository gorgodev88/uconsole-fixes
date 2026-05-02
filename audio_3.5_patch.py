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
