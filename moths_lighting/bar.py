import numpy as np
import threading
import time

class mode:
    def __init__(self, name = None, audio_reactive = False, mode_func = None, auto_cycle = False):  
        self.name = name
        self.audio_reactive = audio_reactive
        self.auto_cycle = auto_cycle
        self.mode_func = mode_func

class mode_manager:
    def __init__(self):
        self.modes = []
        self.modes_menu = []
            
    def remove_auto_cycle_mode(self,idx):
        if 0 <= idx < len(self.modes):
            if self.modes[idx].auto_cycle:
                self.modes[idx].auto_cycle = False
                
    def add_auto_cycle_mode(self,idx):
        if 0 <= idx < len(self.modes):
            if not self.modes[idx].auto_cycle:
                self.modes[idx].auto_cycle = True
            
    def get_all_modes(self):
        return self.modes
    
    def get_all_mode_menu(self):
        return self.modes_menu
    
    def get_auto_cycle_modes(self):
        return [mode for mode in self.modes if mode.auto_cycle]
    def get_auto_cycle_menu(self):
        return [mode.name for mode in self.modes if mode.auto_cycle]
    
    

class Bar:
    def __init__(self,colour_manager, num_leds=96, brightness=0.5):
        self.lock = threading.Lock()
        self.num_leds = num_leds
        self.num_pixels = num_leds * 3
        self.pixels = bytearray([0] * self.num_pixels)
        self.brightness = brightness
        self.state = 4  # Mode index
        self.auto_cycle = False 
        self.time_per_mode = 60
        self.previous_state = 4  # Previous mode index
        self.start_time = time.time()
        #colours 
        
        self.colour = colour_manager.get_colour_list()[0]
        self.colour_manager = colour_manager
        self.colours = self.colour_manager.get_colour_list()
        self.steps_per_transition = 1000 
        self.all_colours = self.cycle_colours(colours=self.colours,steps_per_transition=self.steps_per_transition)
        
        #Modes
        self.mode_manager = mode_manager()
        self.generate_mode_menu()
        self.modes = [
            {"name": "Static", "func": self.mode_static, "audio_reactive": False, "auto_cycle": False},
            {"name": "Wave", "func": self.mode_wave, "audio_reactive": True, "auto_cycle": False},
            {"name": "Pulse", "func": self.mode_pulse, "audio_reactive": True, "auto_cycle": False},
            {"name": "Bass Strobe", "func": self.mode_bass_strobe, "audio_reactive": True, "auto_cycle": False},
            {"name": "Bass & Mid Strobe", "func": self.mode_bass_mid_strobe, "audio_reactive": True, "auto_cycle": False},
        ]
        
        #modes for auto_cycle 
        self.cycle_modes = []
        self.cycle_modes_menu = [] 
        self.all_modes = []
        self.all_modes_menu = []
        
        #lighting related
        self.fade = 0.2
        self.fade_out_count = 0  # Initialize counter for fade_out calls
        self.fade_out_threshold = 40  # Adjust this threshold based on the desired fading duration
        self.current_step = 0
        self.length_mid_strobe = 30
        #audio related
        self.trigger_style = "max"
        
        self.bass_threshold = 0.8
        self.bass_lower_bound = 0
        self.bass_upper_bound = 200
        
        self.mid_threshold  = 0.5
        self.mid_lower_bound = 800
        self.mid_upper_bound = 3000
        
    def generate_mode_menu(self):
        for config in self.modes:
            name = config["name"]
            audio_reactive = config["audio_reactive"]
            mode_func = config["func"]
            auto_cycle = config["auto_cycle"]
            mode = mode(name = name, audio_reactive = audio_reactive, mode_func = mode_func, auto_cycle = auto_cycle)
            self.mode_manager.add_mode(mode)
        
        
        #want to delete these attributes
        self.cycle_modes = mode_manager.get_auto_cycle_modes()
        self.cycle_modes_menu = mode_manager.get_auto_cycle_menu()
        self.all_modes = mode_manager.get_all_modes()
        self.all_modes_menu = mode_manager.get_all_mode_menu()
        

    def update(self, fft_data):
        with self.lock:
            # Call the current mode's update method
            if self.state == "static":
                self.mode_display_colour()
            elif self.auto_cycle:
                self.update_auto_cycle(fft_data)
            else:
                if self.state in enumerate(self.mode_manager.get_all_modes()):
                    self.mode_manager.mode[self.state].mode_func(fft_data)
                else: 
                    print(f'Mode {self.state} not found')

    def update_auto_cycle(self, fft_data):
        # Calculate the time elapsed since the start of the current mode
        elapsed_time = time.time() - self.start_time

        # If the time elapsed exceeds the time per mode, switch to the next mode
        if elapsed_time > self.time_per_mode:
            
            self.state += 1
            self.start_time = time.time()

        # If the current mode is the last mode, reset to the first mode
        if self.state >= len(self.cycle_modes):
            self.state = 0

        # Call the current mode's update method
        self.cycle_modes[self.state].mode_func(fft_data)
            
    def mode_display_colour(self):
        colour =(self.colour.red, self.colour.green, self.colour.blue)
        # Apply brightness to the color
        brightened_color = tuple(int(c * self.brightness) for c in colour)
        
        # Update the pixels with the brightened color
        self.pixels = bytearray(brightened_color * self.num_leds)

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
        
    def mode_bass_strobe(self, fft_data):
        # Compute the bass magnitude from fft_data
        # Increment current_step and reset if it exceeds the length of all_colours
        self.current_step += 1
        if self.current_step >= len(self.all_colours):
            self.current_step = 0
            
        bass_magnitude = self.compute_bass_magnitude(fft_data)

        # Check if the bass magnitude exceeds the threshold
        if bass_magnitude > self.bass_threshold:
            # Apply the strobe effect (turn on all LEDs)
            # Use the current step color when not in strobe mode
            color = self.all_colours[self.current_step]
            brightened_color = tuple(int(c * self.brightness) for c in color)
            self.pixels = bytearray(brightened_color * self.num_leds)
      
            # Reset fading when strobe is active
            self.fade_out_count = 0
        else:
            # If not strobing, apply fading effect
            self.fade_out()
            
    def mode_bass_mid_strobe(self, fft_data):
        # Compute the bass magnitude from fft_data
        # Increment current_step and reset if it exceeds the length of all_colours
        self.current_step += 1
        if self.current_step >= len(self.all_colours):
            self.current_step = 0
            
        bass_magnitude = self.compute_bass_magnitude(fft_data)
        mid_magnitude = self.compute_mid_magnitude(fft_data)
        # Check if the bass magnitude exceeds the threshold
        if bass_magnitude > self.bass_threshold:
            # Apply the strobe effect (turn on all LEDs)
            # Use the current step color when not in strobe mode
            color = self.all_colours[self.current_step]
            brightened_color = tuple(int(c * self.brightness) for c in color)
            self.pixels = bytearray(brightened_color * self.num_leds)
      
            # Reset fading when strobe is active
            self.fade_out_count = 0
        
        else:
            # If not strobing, apply fading effect
            self.fade_out()   
        
        if mid_magnitude > self.mid_threshold:
                    # Apply the strobe effect (turn on all LEDs)
            # Use the current step color when not in strobe mode
            color = (150,150,150)#self.all_colours[self.current_step]
            brightened_color = tuple(int(c * self.brightness) for c in color)
            
            #for a length of 30 LEDs, somewhere random on the bars
            strobe_idx = np.random.randint(0, self.num_pixels - self.length_mid_strobe*3)
            for i in range(strobe_idx,strobe_idx+self.length_mid_strobe*3,3):
                self.pixels[i] = brightened_color[0]
                self.pixels[i+1] = brightened_color[1]
                self.pixels[i+2] = brightened_color[2]
                
            #self.pixels = bytearray(brightened_color * self.num_leds)
      
            # Reset fading when strobe is active
            self.fade_out_count = 0
        
        else:
            # If not strobing, apply fading effect
            self.fade_out()      

    def fade_out(self):
        # Only continue fading if the counter is below the threshold
        if self.fade_out_count < self.fade_out_threshold:
            # Apply fading effect to each pixel
            for i in range(self.num_pixels):
                # Reduce each channel (R, G, B) based on the fade parameter
                self.pixels[i] = max(0, int(self.pixels[i] * (1 - self.fade)))
            
            # Increment the fade out counter
            self.fade_out_count += 1
        else:
            # If the threshold is reached, set pixels to black directly for performance
            self.pixels = bytearray([0] * self.num_pixels)
            self.current_step += 1
            if self.current_step >= len(self.all_colours):
                self.current_step = 0
                        
    def mode_colour_with_strobe(self, fft_data):
        # Compute the bass magnitude from fft_data
        bass_magnitude = self.compute_bass_magnitude(fft_data)

        # Check if the bass magnitude exceeds the threshold
        if bass_magnitude > self.bass_threshold:
            # Apply the strobe effect (turn on all LEDs)
            color = (255, 255, 255)  # White color for strobe effect
            self.pixels = bytearray([int(c * self.brightness) for c in color] * self.num_leds)
        else:
            # Use the current step color when not in strobe mode
            color = self.all_colours[self.current_step]
            brightened_color = tuple(int(c * self.brightness) for c in color)
            self.pixels = bytearray(brightened_color * self.num_leds)

            # Increment current_step and reset if it exceeds the length of all_colours
            self.current_step += 1
            if self.current_step >= len(self.all_colours):
                self.current_step = 0
        
    def compute_bass_magnitude(self, fft_data):
        # Assuming fft_data contains magnitudes for frequencies up to 5000 Hz
        # Extract indices corresponding to bass frequencies (20-200 Hz)
        num_bins = len(fft_data)
        max_freq = 5000
        freqs = np.linspace(0, max_freq, num_bins)

        # Find indices for the bass range (20-200 Hz)
        bass_indices = np.where((freqs >= self.bass_lower_bound) & (freqs <= self.bass_upper_bound))[0]

        # Compute the  bass trigger magnitude
        if self.trigger_style == "max":
            bass_magnitude = np.max(fft_data[bass_indices])
        elif self.trigger_style == "mean":
            bass_magnitude = np.mean(fft_data[bass_indices])
            
        return bass_magnitude
    
    def compute_mid_magnitude(self, fft_data):
        # Assuming fft_data contains magnitudes for frequencies up to 5000 Hz
        # Extract indices corresponding to bass frequencies (20-200 Hz)
        num_bins = len(fft_data)
        max_freq = 5000
        freqs = np.linspace(0, max_freq, num_bins)

        # Find indices for the bass range (20-200 Hz)
        mid_indices = np.where((freqs >= self.mid_lower_bound) & (freqs <= self.mid_upper_bound))[0]

        # Compute the mid trigger magnitude
        if self.trigger_style == "max":
            mid_magnitude = np.max(fft_data[mid_indices])
        elif self.trigger_style == "mean": 
            mid_magnitude = np.mean(fft_data[mid_indices])
            
        return mid_magnitude
    
    def map_level_to_color(self, level):
        # Map level (0 to 1) to a color gradient
        r = int(level * 255)
        g = int((1 - level) * 255)
        b = 0
        return (r, g, b)

    def get_pixels(self):
        
    #helper functions with modes
        with self.lock:
            return self.pixels

    def set_auto_cycle(self, auto_cycle):
        self.auto_cycle = auto_cycle
        if auto_cycle:
            self.start_time = time.time()
        
    def get_auto_cycle(self):
        return self.auto_cycle

    def set_time_per_mode(self, time_per_mode):
        self.time_per_mode = time_per_mode
    
    def get_time_per_mode(self):
        return self.time_per_mode

    ##Helper functions with colours
    def update_colours(self):
        self.colours = self.colour_manager.get_colour_list()
        self.all_colours = self.cycle_colours(colours=self.colours,steps_per_transition=self.steps_per_transition)
    
    def interpolate_colour(self, colour1, colour2, steps):
        # This function will take two colours and return a list of colours that are interpolated between the two colours
        # The resulting colors are converted to integers
        colour1 = (colour1.red, colour1.green, colour1.blue)
        colour2 = (colour2.red, colour2.green, colour2.blue)
        return [list(map(int, (1 - t) * np.array(colour1) + t * np.array(colour2))) for t in np.linspace(0, 1, steps)]

    def cycle_colours(self, colours, steps_per_transition):
        """Cycle through a list of RGB colors smoothly with integer values."""
        all_colors = []
        for i in range(len(colours)):
            color1 = colours[i]
            color2 = colours[(i + 1) % len(colours)]  # Wrap to the first color after the last
            all_colors.extend(self.interpolate_colour(color1, color2, steps_per_transition))
        return all_colors
 