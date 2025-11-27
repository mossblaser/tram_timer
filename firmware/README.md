Firmware flashing and configuration
===================================


# Installing MicroPython

To use this firmware, a [MicroPython build for the Raspberry Pi Pico
W](https://micropython.org/download/RPI_PICO_W/) must be installed on the
device. I have tested with v1.26.1. If MicroPython is already installed,
there's likely no need to re-install it -- we just need to update our software.


# Copying the firmware

To copy the firmware onto the device you might wish to use
the [upyt](https://github.com/mossblaser/upyt) tool. Set the device name in
your environment like so:

```sh
export UPYT_DEVICE=/dev/ttyACM0
```

Before we copy anything across, the `config.py` file needs creating and
populating as indicated in `config.py.example`.

> [!NOTE]
> Unfortunately, TFGM/BeeNetwork are not handing out new API keys at the moment
> so you'll need to beg or borrow one.
>
> If you already have a device with an API key configured, make sure you note
> it down (e.g. by reading back the `config.py` file) -- with the key owner's
> permission, of course!
>
>     upyt cp :config.py .

We can fiddle with the `position_min_ns` and `position_max_ns` settings later
on.

Copy the firmware across to the device and reset to set it running:

```sh
upyt sync --reset path/to/firmware/
```

> [!TIP]
> Add the `--terminal` argument to start a serial terminal after the file sync
> is complete.


# Calibrating the servo

Servos can differ slightly in the range of PWM values they expect. To extract
the full range out of a servo, the `position_min_ns` and `position_max_ns`
values may need adjusting. To do this we'll use the MicroPython REPL.

Attach a serial terminal using:

```sh
upyt terminal
```

Since the firmware starts the watchdog timer, we'll need to perform a soft
reset and interrupt the firmware before the watchdog is started. To do this
press Ctrl+D to trigger a reset and then press Ctrl+C during the count-down to
the watchdog starting. You should drop into a Python REPL.

The `tram` object is an instance of the `Tram` class in [`tram.py`](./tram.py).
This is used to move the tram along the track. You can check the calibration by
manually running commands such as:

```python
>>> tram.move_to(4)  # Move to the four minute mark
```

If the spacing is right but everything is offset slightly you might be able to
adjust the position of the countdown board/platform by loosening the screws
attaching it to the linear rail and moving it along.

If the scale is off, you will need to adjust `position_min_ns` and
`position_max_ns`. This is a matter of trying PWM values by trial-and-error for
the '0' and '?' positions on the scale and setting `position_min_ns` and
`position_max_ns` respectively.

To control the servo, first turn it on:

```python
>>> tram._pwm.freq(50)
>>> tram._pwm.duty_ns(566_500)
>>> tram._pwm.init()
```

Then iteratively call `tram._pwm.duty_ns(...)` with new values until you've
determined the two endpoints.

Write the values into `config.py`, copy it onto the device and reset  (using
`upyt sync --reset path/to/firmware/`) and check the calibration again.
