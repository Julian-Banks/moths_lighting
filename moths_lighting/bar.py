import time
import numpy as np
import threading

class Bar:
    def __init__(self, num_leds=96, brightness=1.0):
        self.lock = threading.Lock()
        self.num_leds = num_leds
        self.num_pixels = num_leds * 3
        self.pixels = bytearray([0] * self.num_pixels)
        self.brightness = brightness
        self.state = 0  # 0 for initial mode, can be changed to switch modes

    def update(self, fft_data):
        with self.lock:
            # Process fft_data and update self.pixels accordingly
            magnitude = np.abs(fft_data)
            # Normalize magnitude
            magnitude = magnitude / np.max(magnitude) if np.max(magnitude) > 0 else magnitude
            # Resample magnitude to the number of LEDs
            led_levels = np.interp(np.linspace(0, len(magnitude), self.num_leds),
                                   np.arange(len(magnitude)), magnitude)
            # Map led_levels to colors
            # For example, map frequency bands to colors
            pixels = []
            for level in led_levels:
                color = self.map_level_to_color(level)
                pixels.extend([int(c * self.brightness) for c in color])
            self.pixels = bytearray(pixels)

    def map_level_to_color(self, level):
        # Map level (0 to 1) to a color, e.g., from blue (low) to red (high)
        # Simple gradient from blue to red
        r = int(level * 255)
        g = 0
        b = int((1 - level) * 255)
        return (r, g, b)

    def get_pixels(self):
        with self.lock:
            return self.pixels
