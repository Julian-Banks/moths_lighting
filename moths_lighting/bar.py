import numpy as np
import threading
import time
import yaml
import os 
import math
from scipy.signal import find_peaks



class Bar:
    def __init__(self,colour_manager, mode_manager,controller_idx, num_leds=96):
        
        self.config_file = 'moths_lighting/moths_lighting/config/bar_config.yaml'
        self.controller_idx = controller_idx
        self.set_config()
        #standard, always the same properties
        self.lock = threading.Lock()
        self.num_leds = num_leds
        self.num_pixels = num_leds * 3
        self.pixels = bytearray([0] * self.num_pixels)
        
        self.previous_state = 0  # Previous mode index
        self.fade_out_count = 0
        self.start_time = time.time()
        self.debounce_time = time.time()
        self.bass_debounce_time = time.time()
        
        #Pulse settings
        self.global_magnitude_max = 0 
        self.decay_factor = 0.999
        
        #Sine mode settings
        self.time = 0              # Initialize time for the animation
        self.sine_frequency = 4  #frequency of the sine wave
        self.last_time_change = 0.005
        
        #beat decection settings
        self.energy_buffer_size = 100  # Adjust the buffer size based on your frame rate and desired window
        self.energy_buffer = np.zeros(self.energy_buffer_size)
        self.energy_index = 0  # Index to keep track of where to insert the next energy value

        #colours 
        self.colour_manager = colour_manager
        self.update_colours()

        #Modes also want to move this into mode manager class
        self.mode_manager = mode_manager
      
        

    def set_config(self):
        config = self.get_config()
        self.state = config['state']
        self.steps_per_transition = config['steps_per_transition']
        self.auto_cycle = config['auto_cycle']
        self.time_per_mode = config['time_per_mode']
        self.brightness = config['brightness']
        self.fade = config['fade']
        self.fade_out_threshold = config['fade_out_threshold']
        self.current_step = config['current_step']
        self.length_mid_strobe = config['length_mid_strobe']
        self.trigger_style = config['trigger_style']
        self.bass_threshold = config['bass_threshold']
        self.bass_lower_bound = config['bass_lower_bound']
        self.bass_upper_bound = config['bass_upper_bound']
        self.mid_threshold = config['mid_threshold']
        self.mid_lower_bound = config['mid_lower_bound']
        self.mid_upper_bound = config['mid_upper_bound']
        self.mid_debounce = config['mid_debounce']
        self.bass_debounce = config['bass_debounce']
        self.colour_offset = config['colour_offset']
    
    def get_config(self):
        with open(self.config_file, 'r') as file:
            data = yaml.safe_load(file)
        data = data[self.controller_idx]
        return data
    
    def update_config(self):
                # Get the current working directory
        target_file = self.config_file
        to_print = self.dictify()
        current_directory = os.getcwd()
        #print(f"Current working directory: {current_directory}")
        if os.path.exists(target_file):
            with open(target_file, 'r') as file:
                data = yaml.safe_load(file)
        else:
            print(f"File does not exist: {target_file}")
            print("creating file")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            data = {}
            
        data[self.controller_idx] = to_print      
        
        with open(target_file, 'w') as file:
            yaml.dump(data, file)
        print(f"Config updated: {target_file}")
    
    #write a function to get all of the correct properties in the correct format.
    def dictify(self):
        config = {
            'state': self.state,
            'steps_per_transition': self.steps_per_transition,
            'auto_cycle': self.auto_cycle,
            'time_per_mode': self.time_per_mode,
            'brightness': self.brightness,
            'fade': self.fade,
            'fade_out_threshold': self.fade_out_threshold,
            'current_step': self.current_step,
            'length_mid_strobe': self.length_mid_strobe,
            'trigger_style': self.trigger_style,
            'bass_threshold': self.bass_threshold,
            'bass_lower_bound': self.bass_lower_bound,
            'bass_upper_bound': self.bass_upper_bound,
            'mid_threshold': self.mid_threshold,
            'mid_lower_bound': self.mid_lower_bound,
            'mid_upper_bound': self.mid_upper_bound,
            'mid_debounce': self.mid_debounce,
            'bass_debounce': self.bass_debounce,
            'colour_offset' : self.colour_offset
        }
        return config 
    
    ##ADD MODES HERE ONCE YOU MAKE THEM##

    def get_mode_func(self, mode_name):
        mode_funcs = {
            "Static": self.mode_static,
            "Bass Strobe 1": self.mode_bass_strobe_1,
            "Pulse": self.mode_pulse,
            "Bass Strobe": self.mode_bass_strobe,
            "Bass & Mid Strobe": self.mode_bass_mid_strobe,
            "Sine Wave" :self.mode_sine_wave,
            "Swirl": self.mode_swirl
        }
        return mode_funcs.get(mode_name)

    def update(self, fft_data):
        with self.lock:    
            # Call the current mode's update method
            #print(f"in bar, auto cycle: {self.auto_cycle}")
            #print(f"in bar, len(self.mode_manager.auto_cycle_modes): {len(self.mode_manager.auto_cycle_modes)}")
            if self.state == "static":
                self.mode_display_colour()
            elif self.auto_cycle and (len(self.mode_manager.auto_cycle_modes) > 0):
                self.update_auto_cycle(fft_data)
            else:
                if self.state < len(self.mode_manager.get_all_modes()):
                    mode_name = self.mode_manager.modes[self.state].name
                    self.get_mode_func(mode_name)(fft_data)
                else: 
                    print(f'Mode {self.state} not found')
                     
    def get_mode(self):
        if self.auto_cycle:
            if self.state < len(self.mode_manager.auto_cycle_modes):
                auto_cycle_idx = self.mode_manager.auto_cycle_modes[self.state].name
            #find the idx of the mode in all modes
                idx = [mode.name for mode in self.mode_manager.get_all_modes()].index(auto_cycle_idx)
                return idx
            else: 
                return self.state
        else:
            return self.state

    def update_auto_cycle(self, fft_data):
        # Calculate the time elapsed since the start of the current mode
        elapsed_time = time.time() - self.start_time

        # If the time elapsed exceeds the time per mode, switch to the next mode
        if elapsed_time > self.time_per_mode:
            
            self.state += 1
            self.start_time = time.time()

        # If the current mode is the last mode, reset to the first mode
        if self.state >= len(self.mode_manager.auto_cycle_modes):
            self.state = 0

        # Call the current mode's update method
        mode_name = self.mode_manager.auto_cycle_modes[self.state].name
        self.get_mode_func(mode_name)(fft_data)
 
 
 ############### MODES ####################################           
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
        energy = self. compute_fft_energy(fft_data)
        # Increment current_step and reset if it exceeds the length of all_colours
        self.current_step += 1
        if self.current_step >= len(self.all_colours):
            self.current_step = 0

        # Determine maximum magnitude (apply decay if needed)
        if energy > self.global_magnitude_max:
            self.global_magnitude_max = energy
        else:
            self.global_magnitude_max *= self.decay_factor

        # Calculate the brightness level as a ratio of the current magnitude to the max magnitude
        level = energy / self.global_magnitude_max
        
        # Number of LEDs that should be lit based on the level
        num_leds_on = int(level * self.num_leds)
        
        # Get the current color
        colour = self.all_colours[self.current_step]
        colour = tuple(int(c * self.brightness) for c in colour)
            
        beat = self.compute_fft_magnitude(fft_data) > (self.bass_threshold *0.5)
        
        if beat:
            self.fade_out_count = int(self.fade_out_threshold/10)  # Reset the fade out count to allow further fading
            # Create a byte array for the LEDs that will light up based on the current magnitude
            # This array will maintain the faded LEDs and increase the brightness of the relevant ones
            updated_pixels = bytearray(self.pixels)  # Start with the current LED state
            # Update only the LEDs that are supposed to be on based on current magnitude
            # Set the updated pixel array
            self.pixels = updated_pixels
            
            for i in range(num_leds_on):
                updated_pixels[i*3:i*3+3] = colour  # Increase the brightness of the correct LEDs
            self.fade_out()
        else:
            self.fade_out()  # Apply fade to the LEDs
        
    def mode_bass_strobe(self, fft_data):
        # Compute the bass magnitude from fft_data
        # Increment current_step and reset if it exceeds the length of all_colours
        self.current_step += 1
        if self.current_step >= len(self.all_colours):
            self.current_step = 0
            
        bass_magnitude = self.compute_bass_magnitude(fft_data)

        # Check if the bass magnitude exceeds the threshold
        if (bass_magnitude > self.bass_threshold) and (time.time() - self.bass_debounce_time > self.bass_debounce):
            self.bass_debounce_time = time.time()
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
            
    def mode_bass_strobe_1(self, fft_data):
        
        #move this into detect beat maybe?

        
        self.current_step += 1
        if self.current_step >= len(self.all_colours):
            self.current_step = 0
        
        beat_detected = self.compute_bass_magnitude(fft_data) > self.bass_threshold
        # Use beat_detected to trigger actions
        if beat_detected and (time.time() - self.bass_debounce_time > self.bass_debounce):
            self.bass_debounce_time = time.time()
            color = self.all_colours[self.current_step]
            brightened_color = tuple(int(c * self.brightness) for c in color)
            self.pixels = bytearray(brightened_color * self.num_leds)
      
            # Reset fading when strobe is active
            self.fade_out_count = 0
        else:
            self.sine_fade_out()
            
    def mode_bass_mid_strobe(self, fft_data):
        # Compute the bass magnitude from fft_data
        # Increment current_step and reset if it exceeds the length of all_colours
        self.current_step += 1
        if self.current_step >= len(self.all_colours):
            self.current_step = 0
            
        bass_magnitude = self.compute_bass_magnitude(fft_data)
        mid_magnitude = self.compute_mid_magnitude(fft_data)

                # Check if the bass magnitude exceeds the threshold
        if (bass_magnitude > self.bass_threshold) and (time.time() - self.bass_debounce_time > self.bass_debounce):
            
            self.bass_debounce_time = time.time()
            # Apply the strobe effect (turn on all LEDs)
            # Use the current step color when not in strobe mode
            color = self.all_colours[self.current_step]
            brightened_color = tuple(int(c * self.brightness*0.5) for c in color)
            self.pixels = bytearray(brightened_color * self.num_leds)
      
            # Reset fading when strobe is active
            self.fade_out_count = 0
        
        elif (mid_magnitude > self.mid_threshold) and (time.time() - self.debounce_time > self.mid_debounce):
            
            self.debounce_time = time.time()
       
            halfway_index = (self.current_step + len(self.all_colours) // 2) % len(self.all_colours)
            color = self.all_colours[halfway_index]

            brightened_color = tuple(int(c * self.brightness) for c in color)
            
            sine_wave = np.sin(np.linspace(0, np.pi, self.length_mid_strobe))  # Creates half a sine wave over 30 steps

            # Random starting point for the strobe
            max_value = (self.num_pixels - self.length_mid_strobe * 3) // 3
            strobe_idx = np.random.randint(0, max_value + 1) * 3

            # Apply sine wave for soft edge effect
            for i in range(strobe_idx, strobe_idx + self.length_mid_strobe * 3, 3):
                sine_factor = sine_wave[(i - strobe_idx) // 3]  # Scales brightness based on sine wave
                self.pixels[i] = int(brightened_color[0] * sine_factor)
                self.pixels[i+1] = int(brightened_color[1] * sine_factor)
                self.pixels[i+2] = int(brightened_color[2] * sine_factor)
            
            # Reset fading when strobe is active
            self.fade_out_count = 0
        else:
            # If not strobing, apply fading effect
            self.sine_fade_out()      

    def mode_swirl(self, fft_data):
        # Update time for animation
        
        if not hasattr(self, 'time'):
            self.time = 0
            
        # Compute the overall magnitude from fft_data
        beat = (self.compute_bass_magnitude(fft_data) > self.bass_threshold)
        # Increment time to animate the wave
        this_time_change = 0
        
        if beat:
            this_time_change =  min(self.last_time_change*2, 0.03)
            self.current_step = (self.current_step + 50) % len(self.all_colours)
        else:
            this_time_change += max(0.003 , self.last_time_change * 0.95)
        
        self.time += this_time_change
        self.last_time_change = this_time_change
        

        # Get the current color
        color = self.all_colours[self.current_step]

        # Create the swirling pattern
        pixels = bytearray()
        for i in range(self.num_leds):
            # Calculate the brightness for this pixel
            position = i / self.num_leds
            wave = (
                    math.sin(2 * math.pi * (position * 7 + self.time * 1.2)) +
                    math.sin(2 * math.pi * (position * 13 - self.time * 0.7)) +
                    math.sin(2 * math.pi * (position * 17 + self.time * 0.5))
                )

            # Normalize the wave value to be between 0 and 1
            brightness = (wave + 3) / 6  # Sum of three sine waves, total range -3 to +3

            # Bias brightness towards lower values
            brightness = brightness ** 2  # Square to bias towards dimmer pixels
            brightness = brightness ** 2  # Square again to further bias towards dimmer pixels
            # Adjust overall brightness
            brightness *= self.brightness# Adjust as needed

            # Ensure brightness is between 0 and 1
            brightness = min(max(brightness, 0), 1)

            # Calculate the pixel color
            pixel_color = tuple(int(c * brightness) for c in color)

            # Append the color to the pixels array
            pixels.extend(pixel_color)
            
        self.pixels = pixels

    def mode_sine_wave(self, fft_data):
        start_time = time.time()
        # Initialize time variable if not already present
        if not hasattr(self, 'time'):
            self.time = 0
            
        # Compute the overall magnitude from fft_data
        magnitude = self.compute_bass_magnitude(fft_data)
        # Increment time to animate the wave
        this_time_change = 0
        if magnitude > self.bass_threshold:
            this_time_change =  min(self.last_time_change*3, 0.09)
        else:
            this_time_change += max(0.003 , self.last_time_change * 0.97)
        
        self.time += this_time_change
        self.last_time_change = this_time_change
    
        # Map magnitude to amplitude and frequency for the sine wave
        amplitude = self.brightness
        
        frequency = self.sine_frequency 

        # Cycle through colors using current_step
        self.current_step += 1
        if self.current_step >= len(self.all_colours):
            self.current_step = 0

        base_color = self.all_colours[self.current_step]
        brightened_color = tuple(int(c * self.brightness) for c in base_color)

        # Create the pixels bytearray
        pixels = bytearray()
        for i in range(self.num_leds):
            
            # Calculate the sine wave value at this position and time
            position = i / (self.num_leds)
            angle = math.pi * (frequency * position +   self.time)
            value = math.sin(angle)

            # Normalize the sine value to a brightness level between 0 and 1
            brightness = (value * amplitude + amplitude) / (2 * amplitude)

            brightness = brightness ** 2  # Square to bias towards dimmer pixels
            # Apply brightness to the base color
            pixel_color = tuple(int(c * brightness) for c in brightened_color)

            # Append the color to the pixels array
            pixels.extend(pixel_color)

        # Update the LED pixels
        self.pixels = pixels
        end_time = time.time()
        duration = end_time - start_time
        #print(f"Mode Duration: {duration:.4f}s")
            
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
 
########## MODE HELEPERS ############################
    def fade_out(self):
        # Only continue fading if the counter is below the threshold
        fade_out_threshold = (5/self.fade)
        if self.fade_out_count < fade_out_threshold:
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
    def sine_fade_out(self):
        # Only continue fading if the counter is below the threshold
        fade_out_threshold = (5 / self.fade)
        if self.fade_out_count < fade_out_threshold:
            # Create a sine wave across the number of LEDs (soft edges)
            sine_wave = np.sin(np.linspace(0, np.pi, self.num_leds))  # Half sine wave
            
            # Apply fading effect to each pixel with sine wave modulation
            for i in range(0, self.num_pixels, 3):  # Assuming 3 channels (R, G, B)
                # Get the sine factor corresponding to the current LED index
                led_idx = i // 3
                sine_factor = sine_wave[led_idx]

                # Reduce each channel (R, G, B) based on the fade parameter and sine wave factor
                self.pixels[i] = max(0, int(self.pixels[i] * (1 - self.fade) * sine_factor))
                self.pixels[i+1] = max(0, int(self.pixels[i+1] * (1 - self.fade) * sine_factor))
                self.pixels[i+2] = max(0, int(self.pixels[i+2] * (1 - self.fade) * sine_factor))

            # Increment the fade out counter
            self.fade_out_count += 1
        else:
            # If the threshold is reached, set pixels to black directly for performance
            self.pixels = bytearray([0] * self.num_pixels)
            self.current_step += 1
            if self.current_step >= len(self.all_colours):
                self.current_step = 0
        
##### I need to figure out what I'm actually using here. Currently these calculations are being repeated which I dont like.
##### Once I know what I'm using I can do the calculations once in the ArtnetController class and pass the values to the bar class.        

    def detect_beats(self,fft_data):

        self.compute_fft_energy(fft_data)
        # Ensure that the energy buffer is sufficiently filled
        if np.count_nonzero(self.energy_buffer) < self.energy_buffer_size:
            # Not enough data yet
            return False

        # Reorder the energy buffer so that the oldest sample is at index 0
        reordered_buffer = np.concatenate(
            (self.energy_buffer[self.energy_index:], self.energy_buffer[:self.energy_index])
        )

        # Apply a smoothing filter to reduce noise (optional but can help)
        from scipy.ndimage import uniform_filter1d
        smoothed_energy = uniform_filter1d(reordered_buffer, size=5)

        # Normalize the energy buffer
        normalized_energy = (smoothed_energy - np.mean(smoothed_energy)) / np.std(smoothed_energy)

        # Adjust parameters for find_peaks
        peaks, properties = find_peaks(
            normalized_energy,
            prominence=self.bass_threshold,      # Adjust prominence as needed
            height=0,            # Peaks must be higher than 0
            distance=20          # Minimum number of samples between peaks
        )

        recent_window_start = len(normalized_energy) - 5  # Start of the last 5 readings
        recent_peaks = [p for p in peaks if p >= recent_window_start]

        return len(recent_peaks) > 0

    def compute_fft_energy(self,fft_data):
        # Compute energy from fft_data
        energy = np.sum(np.abs(fft_data))

        # Update energy buffer
        self.energy_buffer[self.energy_index] = energy
        self.energy_index = (self.energy_index + 1) % self.energy_buffer_size
        return energy

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
    
    def compute_fft_magnitude(self, fft_data):
        # Compute the  bass trigger magnitude
        if self.trigger_style == "max":
            magnitude = np.max(fft_data)
        elif self.trigger_style == "mean":
            magnitude = np.mean(fft_data)
        return magnitude
    
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


### Get and set Functions ###
    def get_pixels(self):
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
    ### Update colours fetchs the RGB values from the colour manager and then Creates the list of all colours to cycle through
    def update_colours(self):
        with self.lock:
            self.colours = self.colour_manager.get_colour_list()
            self.all_colours = self.cycle_colours(colours=self.colours,steps_per_transition=self.steps_per_transition)
            self.current_step = int(round(len(self.all_colours)*self.colour_offset*self.controller_idx))%len(self.all_colours) #Calculate the colour offset and clamp to the range of self.all_colours
        
    ### Update colours then calls cycle colours to create the list of all colours to cycle through
    def cycle_colours(self, colours, steps_per_transition):
        """Cycle through a list of RGB colors smoothly with integer values."""
        all_colors = []
        for i in range(len(colours)):
            color1 = colours[i]
            color2 = colours[(i + 1) % len(colours)]  # Wrap to the first color after the last
            all_colors.extend(self.interpolate_colour(color1, color2, steps_per_transition))
        return all_colors
    
    #Cycle colours calls interpolate colour to create the list of colours inbetween for each colour pair. 
    def interpolate_colour(self, colour1, colour2, steps):
        # This function will take two colours and return a list of colours that are interpolated between the two colours
        # The resulting colors are converted to integers
        colour1 = (colour1.red, colour1.green, colour1.blue)
        colour2 = (colour2.red, colour2.green, colour2.blue)
        return [list(map(int, (1 - t) * np.array(colour1) + t * np.array(colour2))) for t in np.linspace(0, 1, steps)]