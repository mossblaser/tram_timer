"""
Implements control of the servo which moves the model tram.

Example:

    >>> from tram import Tram
    >>> tram = Tram(Pin(22))
    >>> tram.move_to(0)
    >>> tram.move_to(5)
    >>> tram.move_to(12)
"""

import math
import time

from machine import Pin, PWM


def sinusoidal_ease(p):
    """
    Simple sinusoidal easing function.
    """
    return -(math.cos(math.pi * p) - 1) / 2

class Tram:
    """
    Controls the movement of the servo which moves the model tram along its
    track.
    
    The tram can move between a defined number of discreete steps defined by
    the 'steps' parameter. Positions are numbered from 0 to steps-1
    (inclusive).
    """

    _pwm: PWM
    
    # The PWM period (in ns) corresponding to minimum/maximum positions
    _position_min_ns: float
    _position_max_ns: float

    # The number of equally-spaced discrete positions the tram can take along
    # its track
    _steps: int
    
    # The last set position of the tram (in steps)
    _position: int | None
    
    # The duration over which a full-scale movement should be performed (in
    # seconds)
    _full_scale_duration: float
    
    # The easing function to use for movements (float -> float)
    _ease: "Callable"

    def __init__(
        self,
        pin: Pin,
        position_min_ns: float = 566_500,
        position_max_ns: float = 2_200_000,
        steps: int = 14,
        full_scale_duration: float = 4.0,
        ease = sinusoidal_ease,
    ) -> None:
        """
        Params
        ------
        pin : Pin
            The pin the servo control pin is attched to.
        position_min_ns : int
        position_max_ns : int
            The servo PWM 50 Hz 'high' period in nanoseconds for its minimum
            and maximum extents. That is, at positions 0 and steps-1.
        steps : int
            The number of discrete positions the tram can be in. This should
            correspond with the number of marks written on the tram tracks.
        full_scale_duration : float
            The number of seconds to take to move between the two most extreme
            positions. Shorter moves will be made over proportionally shorter
            durations.
        ease : function(ratio) -> value
            An easing function to apply to the movements of the tram. Should
            take and return a float between 0.0 and 1.0.
        """
        
        self._pwm = PWM(pin)
        
        # Ensure PWM generator is off initially to prevent the servo buzzing or
        # movement
        self._pwm.deinit()
        
        self._position_min_ns = position_min_ns
        self._position_max_ns = position_max_ns
        
        self._steps = steps
        
        self._position = None
        
        self._full_scale_duration = full_scale_duration
        self._ease = ease
    
    def _position_to_ratio(self, position: int) -> float:
        return position / (self._steps - 1)
    
    def _position_to_ns(self, position: int) -> float:
        full_range = self._position_max_ns - self._position_min_ns
        return self._position_min_ns + full_range * self._position_to_ratio(position)
    
    def move_to(self, position: int) -> None:
        """
        Move to the provided position (i.e. step number). Blocks whilst the
        servo moves.
        """
        # NB: Special handling is required for our first move since the servo
        # could be in an unknown position on startup. Rather than tweening
        # between first/last position, we instead just give the servo a long
        # time to settle on the desired position.
        first_movement = False
        if self._position is None:
            self._position = position
            first_movement = True
        
        # Scale the duration of the movement based on how far we have to move
        change_steps = abs(self._position - position)
        change_ratio = self._position_to_ratio(change_steps)
        duration_ms = (self._full_scale_duration * change_ratio) * 1000
        
        position_start_ns = self._position_to_ns(self._position)
        position_end_ns = self._position_to_ns(position)
        
        self._pwm.freq(50)
        self._pwm.duty_ns(round(position_start_ns))
        self._pwm.init()
        
        # Move from the previous to new position
        start_ms = time.ticks_ms()
        while True:
            ellapsed_ms = time.ticks_diff(time.ticks_ms(), start_ms)
            if ellapsed_ms >= duration_ms:
                break
            
            p = self._ease(ellapsed_ms / duration_ms)
            
            self._pwm.duty_ns(
                round(
                    position_start_ns +
                    ((position_end_ns - position_start_ns) * p)
                )
            )
            time.sleep_ms(round(1000 / self._pwm.freq()))
        
        # Give the servo some extra time to settle on its final position.
        self._pwm.duty_ns(round(position_end_ns))
        if first_movement:
            # Allow time for a possibly large movement at high speed during
            # initial move
            time.sleep_ms(1000)
        else:
            time.sleep_ms(100)
        
        # Turn off the servo to prevent buzzing
        self._pwm.deinit()
        
        self._position = position
