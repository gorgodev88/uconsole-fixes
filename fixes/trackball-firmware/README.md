# Fix: Trackball Firmware Update on uConsole

Updates the keyboard/trackball firmware on the ClockworkPi uConsole using the official flashing tool. The stock firmware that ships on many units predates the trackball scroll-wheel feature — after updating, holding **Select** while rolling the trackball scrolls instead of moving the cursor.

---

## The Problem

The uConsole's keyboard, trackball, and gamepad buttons are driven by a dedicated microcontroller (an STM32F103R-series chip) on the keyboard module, running its own firmware — independent of the OS on the CM4/CM5 mainboard.

Early stock firmware had **no scroll capability at all**: the trackball could only move the cursor, and there is no physical scroll wheel or middle button. ClockworkPi later added a scroll mode to the stock firmware:

- Nov 2023 — trackball scroll mode added (hold `Fn`), from a [community forum patch](https://forum.clockworkpi.com/t/uconsole-trackball-as-scrolling-wheel-temporary-solution/11032)
- Aug 2024 — trigger changed from `Fn` to `Select` (avoids Fn-layer side effects)

Units that shipped before these changes (or were never updated) are stuck with the old behavior until the keyboard firmware is reflashed.

---

## The Fix

Flash the current official keyboard firmware with ClockworkPi's one-shot flashing tool. Run this **on the uConsole itself** (it talks to the keyboard MCU over the internal USB connection):

```bash
wget https://github.com/clockworkpi/uConsole/raw/master/Bin/uconsole_keyboard_flash.tar.gz
tar zxvf uconsole_keyboard_flash.tar.gz
sudo apt install -y dfu-util
cd uconsole_keyboard_flash
sudo ./flash.sh
```

That's it. The keyboard MCU reboots into its bootloader, takes the new firmware, and comes back on its own. If keys or the trackball seem unresponsive right after flashing, reboot the uConsole.

### What `flash.sh` actually does

The script resets the running keyboard firmware into its DFU bootloader (the bundled `maple_upload`/`upload-reset` helper pokes the keyboard's USB-serial port at `/dev/ttyACM0`), then flashes over USB DFU:

```bash
sudo dfu-util -d 1EAF:0003 -a 2 -D uconsole_keyboard.ino.bin -R
```

- `1EAF:0003` is the LeafLabs Maple / STM32duino DFU bootloader the keyboard MCU uses. In normal operation the keyboard enumerates as `1eaf:0024 Leaflabs uConsole` (composite keyboard + mouse + serial device) — that's the ID you'll see in `lsusb` when everything is working.
- `-a 2` selects the bootloader's flash-memory interface. Don't change it.
- `-R` resets the MCU back into the new firmware when done.

---

## Verify

After flashing:

1. `lsusb` should show `1eaf:0024 Leaflabs uConsole` (keyboard back in normal mode).
2. Keyboard and trackball work as before.
3. **Hold Select and roll the trackball** — the page scrolls instead of the cursor moving.

---

## Gotchas

- **Have a fallback input method before you flash** — an external USB keyboard or an open SSH session. A failed flash can leave the built-in keyboard dead until recovered.
- **Use the tarball, not the standalone `.bin` files.** The `Bin/` directory of the ClockworkPi repo also contains standalone `uconsole.kbd.0.X_48mhz.bin` images; the wiki explicitly warns these are *not* interchangeable with the binary bundled in the flash tool.
- **If the keyboard is bricked** (no `/dev/ttyACM0`, `flash.sh` can't reset it): the keyboard PCB has a recovery procedure — shorting the boot pin on the module forces the DFU bootloader directly (green LED flash), after which `dfu-util -d 1EAF:0003 -a 2 -D <bin> -R` works without the reset helper. See the community firmware repos below for photos of the pin.
- **CM5 note:** ClockworkPi's instructions mention A06/CM4; the procedure targets the keyboard module itself, which is the same part in CM5 builds. Successfully used on a CM5 uConsole (this repo's author), but not officially documented for CM5.

---

## Going further: community firmware

If you want more than the stock firmware offers (adjustable cursor acceleration curves, horizontal scroll, precision mode, extra layers), two actively maintained community firmwares flash with the exact same `dfu-util` mechanism:

- [j1n6/qmk-uconsole](https://github.com/j1n6/qmk-uconsole) — QMK port; Select+trackball scroll, precision-speed toggle, per-layer tuning
- [ClusterM/uconsole-keyboard](https://github.com/ClusterM/uconsole-keyboard) — from-scratch STM32 HAL firmware; configurable acceleration, cursor inertia, 10 layers

Stock cursor *speed/acceleration* is fixed in firmware — if the cursor feels too slow or too fast for you, the community firmwares above are the firmware-level answer (or adjust pointer acceleration in your OS/compositor settings).

---

## Sources

- [ClockworkPi uConsole repo](https://github.com/clockworkpi/uConsole) — firmware source at `Code/uconsole_keyboard/`, flash tool at `Bin/uconsole_keyboard_flash.tar.gz`
- [Keyboard flashing tool wiki page](https://github.com/clockworkpi/uConsole/wiki/Simple-uConsole-keyboard-flashing-tool)
- [Forum: trackball as scrolling wheel](https://forum.clockworkpi.com/t/uconsole-trackball-as-scrolling-wheel-temporary-solution/11032)
