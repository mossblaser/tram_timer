"""
A wrapper around the native watchdog timer to support much longer feed
intervals (e.g. tens of seconds).

Usage:

    >>> import watchdog
    >>> watchdog.timeout = 30  # Optional
    >>> watchdog.feed()  # Must be called every 'timeout' seconds
"""

# To support itmeouts longer than the underlying hardware watchdog, we use a
# timer to decrement a counter every second. So long as that counter stays
# above zero, the timer also feeds the hardware watchdog (with a 2 second
# timeout). Feeding this watchdog is a matter of resetting the software counter
# to the desired timeout value.

# NB: The slightly non-idiomatic not-encapsulated implementation of this module
# is largely this way because 1: the watchdog is a singleton anyway and 2:
# methods and interrupt service routines don't mix elegantly.

from machine import WDT, Timer, disable_irq, enable_irq
import micropython

# The watchdog timeout (in seconds)
timeout = 30

# We use a timer ISR so it is nice to see any exceptions which happen there...
micropython.alloc_emergency_exception_buf(128)

# Countdown counter, decremented every second and reset to 'timeout' whenever
# 'feed()' is called.
_countdown = None

# The underlying WDT timer
_wdt = None

# The Timer used to decrement the _countdown and feed the real underlying
# watchdog.
_feeder_timer = None

def feed() -> None:
    """
    Feed the watchdog timer. If not called for 'timeout' seconds, the hardware
    watchdog will reset the system.
    """
    global _countdown, _wdt
    state = disable_irq()
    _countdown = timeout
    enable_irq(state)
    
    if _wdt is None:
        _wdt = WDT(timeout=2000)
        _feeder_timer = Timer(
            period=1000,
            mode=Timer.PERIODIC,
            callback=_feed_timer,
        )

def _feed_timer(*_) -> None:
    global _countdown, _wdt
    _countdown -= 1
    if _countdown > 0:
        _wdt.feed()
