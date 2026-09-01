# Fix: Trackball Firmware Update on uConsole

Updates the keyboard/trackball firmware on the ClockworkPi uConsole using the official flashing tool. The stock firmware that ships on many units predates the trackball scroll-wheel feature — after updating, holding **Select** while rolling the trackball scrolls instead of moving the cursor.

---

## The Problem

The uConsole's keyboard, trackball, and gamepad buttons are driven by a dedicated microcontroller (an STM32F103-compatible chip) on the keyboard module, running its own firmware — independent of the OS on the CM4/CM5 mainboard.

Early stock firmware had **no scroll capability at all**: the trackball could only move the cursor, and there is no physical scroll wheel or middle button. ClockworkPi later added a scroll mode to the stock firmware:

- Nov 2023 — trackball scroll mode added (hold `Fn`), from a [community forum patch](https://forum.clockworkpi.com/t/uconsole-trackball-as-scrolling-wheel-temporary-solution/11032)
- Aug 2024 — trigger changed from `Fn` to `Select` (avoids Fn-layer side effects)

Units that shipped before these changes (or were never updated) are stuck with the old behavior until the keyboard firmware is reflashed.

---

## Before you flash

1. **Check whether you even need to:** hold **Select** and roll the trackball. If the page scrolls, your firmware already has the fix — stop here. Flashing carries a small but real risk; don't take it needlessly.
2. **Have a fallback input method ready** — an external USB keyboard or an open SSH session. A failed flash can leave the built-in keyboard dead until recovered.
3. **Unplug other USB-serial devices** (Meshtastic nodes, Arduinos, USB-serial adapters…). The flash tool hardcodes `/dev/ttyACM0`; if another device holds that name, the tool pokes the wrong device and the flash fails. Check with `ls -l /dev/serial/by-id/` — only the keyboard should be present.
4. **Know your rollback options** — you can downgrade to older published firmware, but not recover the exact factory image. See [Reverting](#reverting) below.

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

1. `lsusb` should show `1eaf:0024 Leaflabs uConsole` or similar (keyboard back in normal mode; the exact text comes from the device's own descriptors, so wording can vary).
2. Keyboard and trackball work as before.
3. **Hold Select and roll the trackball** — the page scrolls instead of the cursor moving.

---

## Gotchas

- **The download is unpinned and unchecksummed.** The `wget` above pulls whatever is currently on ClockworkPi's `master` branch, and `flash.sh` runs as root. It's the vendor's own repo, but there is no integrity check — if that bothers you, read the extracted `flash.sh` (it's ~5 lines) before running it.
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

## Reverting

You can't restore the *exact* image your unit shipped with — the flash tool doesn't read the old firmware off the MCU before overwriting it, and there's no way to know which build the factory installed. But downgrading is possible:

- ClockworkPi publishes older firmware versions (0.1–0.4) in the repo's [`Bin/` directory](https://github.com/clockworkpi/uConsole/tree/master/Bin), flashable via the [UART flashing procedure](https://github.com/clockworkpi/uConsole/blob/master/wiki/How-to-use-keyboard-UART-port-to-flash-firmware.md) (note the tarball-vs-standalone warning above for the dfu-util path).
- You can move to one of the community firmwares below, or back to stock, at any time — they all use the same bootloader and flash procedure.

Reverting hasn't been needed in this author's use; the main behavior change to be aware of is that older builds used `Fn` (not `Select`) as the scroll trigger, or had no scroll mode at all.

---

## Sources

- [ClockworkPi uConsole repo](https://github.com/clockworkpi/uConsole) — firmware source at `Code/uconsole_keyboard/`, flash tool at `Bin/uconsole_keyboard_flash.tar.gz`
- [Keyboard flashing tool wiki page](https://github.com/clockworkpi/uConsole/wiki/Simple-uConsole-keyboard-flashing-tool)
- [Forum: trackball as scrolling wheel](https://forum.clockworkpi.com/t/uconsole-trackball-as-scrolling-wheel-temporary-solution/11032)
