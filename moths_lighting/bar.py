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
        self.colours = [(255,0,0),(0,255,0),(0,0,255)]
        self.steps_per_transition = 100 
        self.all_colours = self.cycle_colours(colours=self.colours,steps_per_transition=self.steps_per_transition)
        self.modes = [self.mode_static, self.mode_wave, self.mode_pulse]  # Add more modes as needed
        self.modes_menu = ["Static", "Wave", "Pulse"]
        self.current_step = 0

    def update(self, fft_data):
        with self.lock:
            # Call the current mode's update method
            self.modes[self.state](fft_data)


    def mode_static(self, fft_data):
        # Use self.current_step to select the current color
        color = self.all_colours[self.current_step]

        # Apply brightness to the color
        brightened_color = tuple(int(c * self.brightness) for c in color)
        
        # Update the pixels with the brightened color
        self.pixels = bytearray(brightened_color * self.num_leds)

        # Increment current_step, and reset if it exceeds the length of all_colours
        self.current_step += 1
        if self.current_step >= len(self.all_colours):
            self.current_step = 0

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

    
    #Helper functions with colours
    def interpolate_colour(self, colour1, colour2, steps):
        # This function will take two colours and return a list of colours that are interpolated between the two colours
        # The resulting colors are converted to integers
        return [list(map(int, (1 - t) * np.array(colour1) + t * np.array(colour2))) for t in np.linspace(0, 1, steps)]



    def cycle_colours(self, colours, steps_per_transition):
        """Cycle through a list of RGB colors smoothly with integer values."""
        all_colors = []
        for i in range(len(colours)):
            color1 = colours[i]
            color2 = colours[(i + 1) % len(colours)]  # Wrap to the first color after the last
            all_colors.extend(self.interpolate_colour(color1, color2, steps_per_transition))
        return all_colors
 