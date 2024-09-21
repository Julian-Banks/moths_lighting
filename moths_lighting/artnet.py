import time
import numpy as np
from stupidArtnet import StupidArtnet
from bar import Bar
import queue

class ArtnetController:
    def __init__(self, esp_configs, colour_manager):
        self.device_bars_map = {}
        self.artnet_devices = []
        self.colour_manager = colour_manager
        self.fps = esp_configs[0].get('fps', 40)
        self.esp_configs = esp_configs
        self.initialize_devices()

    def initialize_devices(self):
        self.device_bars_map.clear()
        self.artnet_devices.clear()
        for config in self.esp_configs:
            target_ip = config['target_ip']
            universe = config['universe']
            num_bars = config.get('num_bars', 1)
            packet_size = num_bars * 96 * 3
            fps = config.get('fps', 40)
            # Create new Artnet device
            artnet_device = StupidArtnet(target_ip, universe, packet_size, fps, True, True)
            # Add the new Artnet device to the list
            self.artnet_devices.append(artnet_device)
            bars = [Bar(self.colour_manager) for _ in range(num_bars)]
            self.device_bars_map[artnet_device] = bars

    def update_bars(self, esp_configs):
        
        self.esp_configs = esp_configs
        self.initialize_devices()
    
    def start_mode(self):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.state = 3  # Set initial state if needed
                
    def change_mode(self,mode = 0):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.state = mode  # Set initial state if needed
    
    def set_display_colour(self, value, colour):
        if value == 1:
            for artnet_device in self.artnet_devices:
                bars = self.device_bars_map[artnet_device]
                for bar in bars:
                    if bar.state != "static":
                        bar.previous_state = bar.state
                    bar.state = "static"
                    bar.colour = colour
        else:
            for artnet_device in self.artnet_devices:
                bars = self.device_bars_map[artnet_device]
                for bar in bars:
                    bar.state = bar.previous_state

    def get_display_colour(self):
        static_colour = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                static_colour.append(0 if bar.state != "static" else 1)
        return static_colour[0]
    
    def update_colours(self):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.update_colours()
                
    def end_mode(self):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.state = "off"

    def update_bars(self, led_queue):
        fft_data = self.process_audio(led_queue)

        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.update(fft_data)

    def process_audio(self, led_queue):
        fft_data_list = []

        # Retrieve all values from the queue
        while True:
            try:
                fft_data = led_queue.get_nowait()
                fft_data_list.append(fft_data)
            except queue.Empty:
                break

        # Compute the average if the list is not empty
        if fft_data_list:
            fft_data_array = np.array(fft_data_list)
            avg_fft_data = np.mean(fft_data_array, axis=0)
            return avg_fft_data
        else:
            # Return a default value if no data was available
            return np.zeros(128)

    def send_data(self):
        for artnet_device in self.artnet_devices:
            packet = bytearray(artnet_device.packet_size)
            bars = self.device_bars_map[artnet_device]
            offset = 0
            for bar in bars:
                pixels = bar.get_pixels()
                packet[offset:offset + len(pixels)] = pixels
                offset += len(pixels)
            artnet_device.send(packet)
        # Timing control is handled in the main loop
        
    ##GET AND SET FUNCTIONS
    #MODE OPTIONS
    #Get all modes
    def get_all_modes(self):
        modes = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                modes.append(bar.menu_manger.get_all_modes())
        return modes[0]
    
    def get_current_mode(self):
        modes = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                modes.append(bar.state)
        return modes[0]
    
    def remove_auto_cycle_mode(self,idx):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.menu_manger.remove_auto_cycle_mode(idx)
    
    def add_auto_cycle_mode(self,idx):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.menu_manger.add_auto_cycle_mode(idx)
    
    def get_auto_cycle(self):
        auto_cycle = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                auto_cycle.append(bar.auto_cycle)
        return auto_cycle[0]
    
    def set_auto_cycle(self, auto_cycle):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.auto_cycle = auto_cycle
        
    
    #LIGHTING OPTIONS
    #Update brightness
    def set_brightness(self, brightness):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.brightness = brightness
    def get_brightness(self):
        brightness = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                brightness.append(bar.brightness)
        return brightness[0]                
    
    #Updated Fade
    def set_fade(self, fade):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.fade = fade
    def get_fade(self):
        fade = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                fade.append(bar.fade)
        return fade[0]
    
    #Time per colour
    def get_time_per_colour(self):
        steps_per_transisiton = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                steps_per_transisiton.append(bar.steps_per_transition)
        time_per_colour = int(steps_per_transisiton[0]/self.fps)
        return time_per_colour
    def set_time_per_colour(self,value):
        steps_per_transition = value*self.fps
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.steps_per_transition  = steps_per_transition
        self.update_colours()
    #AUDIO REACTIVITY OPTIONS
    #Trigger style
    def set_trigger_style(self, trigger_style):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.trigger_style = trigger_style
    def get_trigger_style(self):
        trigger_style = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                trigger_style.append(bar.trigger_style)
        return trigger_style[0]
    
    #Bass trigger
    def set_bass_threshold(self, base_threshold):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.bass_threshold = base_threshold  
    def get_bass_threshold(self):
        bass_threshold = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                bass_threshold.append(bar.bass_threshold)
        return bass_threshold[0]
    
    #Get and set Bass lower bound
    def get_bass_lower_bound(self):
        bass_lower_bound = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                bass_lower_bound.append(bar.bass_lower_bound)
        return bass_lower_bound[0]    
    def set_bass_lower_bound(self, bass_lower_bound):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.bass_lower_bound = bass_lower_bound
        
    #Get and set bass upper bound
    def get_bass_upper_bound(self):
        bass_upper_bound = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                bass_upper_bound.append(bar.bass_upper_bound)
        return bass_upper_bound[0]
    def set_bass_upper_bound(self, bass_upper_bound):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.bass_upper_bound = bass_upper_bound
    
    #Get and set the mid threshold
    def set_mid_threshold(self, mid_threshold):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.mid_threshold = mid_threshold   
    def get_mid_threshold(self):
        thresholds = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                thresholds.append(bar.mid_threshold)
        return thresholds[0]
    
    #Get and set mid lower bound
    def get_mid_lower_bound(self):
        lower_bound = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                lower_bound.append(bar.mid_lower_bound)
        return lower_bound[0]
    def set_mid_lower_bound(self, mid_lower_bound):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.mid_lower_bound = mid_lower_bound
    
    #Get and set mid upper bound    
    def get_mid_upper_bound(self):
        upper_bound = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                upper_bound.append(bar.mid_upper_bound)
        return upper_bound[0]    
    def set_mid_upper_bound(self, mid_upper_bound):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.mid_upper_bound = mid_upper_bound
