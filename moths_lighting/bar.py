import numpy as np
import threading

class Bar:
    def __init__(self, num_leds=96, brightness=1.0):
        self.lock = threading.Lock()
        self.num_leds = num_leds
        self.num_pixels = num_leds * 3
        self.pixels = bytearray([0] * self.num_pixels)
        self.brightness = brightness
        self.state = 0  # Mode index
        self.modes = [self.mode_static, self.mode_wave, self.mode_pulse]  # Add more modes as needed
        self.modes_menu = ["Static", "Wave", "Pulse"]

    def update(self, fft_data):
        with self.lock:
            # Call the current mode's update method
            self.modes[self.state](fft_data)

    def mode_static(self, fft_data):
        # Simple static color
        color = (255, 0, 0)  # Red color
        self.pixels = bytearray(color * self.num_leds)

    def mode_wave(self, fft_data):
        # Simple wave pattern based on FFT data
        magnitude = np.abs(fft_data)
        magnitude = magnitude / np.max(magnitude) if np.max(magnitude) > 0 else magnitude
        led_levels = np.interp(np.linspace(0, len(magnitude), self.num_leds),
                               np.arange(len(magnitude)), magnitude)
        pixels = []
        for level in led_levels:
            color = self.map_level_to_color(level)
            pixels.extend([int(c * self.brightness) for c in color])
        self.pixels = bytearray(pixels)

    def mode_pulse(self, fft_data):
        # Simple pulsing effect
        level = np.mean(np.abs(fft_data))
        level = level / np.max([level, 1e-6])
        color = (int(255 * level), 0, int(255 * (1 - level)))
        self.pixels = bytearray(color * self.num_leds)

    def map_level_to_color(self, level):
        # Map level (0 to 1) to a color gradient
        r = int(level * 255)
        g = int((1 - level) * 255)
        b = 0
        return (r, g, b)

    def get_pixels(self):
        with self.lock:
            return self.pixels

    def set_mode(self, mode_index):
        with self.lock:
            if 0 <= mode_index < len(self.modes):
                self.state = mode_index
