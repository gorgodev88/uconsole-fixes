# uConsole Fixes

A collection of tested fixes for the [ClockworkPi uConsole](https://www.clockworkpi.com/uconsole) — a portable ARM computer (CM4/CM5) with a built-in keyboard, trackball, DSI display, and speakers.

Each fix lives in its own directory under `fixes/`, with a standalone README covering the problem, root cause, step-by-step instructions, and what your options are if you want to go back.

| Fix | Problem it solves |
|---|---|
| [`fixes/speaker-static/`](fixes/speaker-static/) | Built-in speakers emit static/buzzing during keyboard presses and CPU activity when no audio is playing |
| [`fixes/trackball-firmware/`](fixes/trackball-firmware/) | Older stock keyboard firmware has no trackball scrolling; updating it adds Select+trackball scroll-wheel mode |

## Hardware tested

- ClockworkPi uConsole with CM5 (BCM2712), ClockworkPi kernel 6.12.x
- Fixes should also apply to CM4 units — each fix's README notes compatibility specifics

## Contributing

These are personal notes made public in the hope they're useful. Issues and PRs with additional uConsole fixes or corrections are welcome.

## License

[MIT](LICENSE)
