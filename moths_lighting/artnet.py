import time
import numpy as np
from stupidArtnet import StupidArtnet
import yaml
import os
from artnet_manager import ArtnetManager
from bar import Bar
import queue
import threading
class ArtnetController:
    def __init__(self, colour_manager):
        self.device_bars_map = {}
        self.artnet_devices = []
        self.colour_manager = colour_manager
        
        self.lock = threading.Lock()
        self.initialize_devices()
        self.fps = self.esp_configs[0].get('fps', 40)

    def initialize_devices(self):
        self.device_bars_map = {}
        self.artnet_devices = []
        self.num_leds = 144
        self.esp_config_file = 'moths_lighting/config/esp_config.yaml'
        self.esp_configs = self.get_esp_config() ###THIS IS WHERE I NEED UPDATE SELF.ESP_CONFIGS AFTER FIRST RUN
        
        for config in self.esp_configs: 
            target_ip = config['target_ip']
            #universe = config['universe']
            num_bars = config.get('num_bars', 1)
            packet_size = num_bars * self.num_leds * 3
            fps = config.get('fps', 40)
            # Create new Artnet device
            artnet_device = ArtnetManager(target_ip, packet_size, fps)
            # Add the new Artnet device to the list
            self.artnet_devices.append(artnet_device)
            bars = [Bar(self.colour_manager,self.num_leds) for _ in range(num_bars)]
            
            self.device_bars_map[artnet_device] = bars
            
    def get_esp_config(self):
        with open(self.esp_config_file, 'r') as file:
            return yaml.safe_load(file)
        
        
    def update_esp_config(self):
        target_file = self.esp_config_file
        to_print = self.dictify_esp_config()
        current_directory = os.getcwd()
        print(f"Current working directory: {current_directory}")
        if os.path.exists(target_file):
            with open(target_file, 'w') as file:
                yaml.dump(to_print, file)
            print(f"Config updated: {target_file}")
        else:
            print(f"File does not exist: {target_file}")
            print("creating file")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            with open(target_file, 'w') as file:
                yaml.dump(to_print, file)
    
    def dictify_esp_config(self):
        esp_config_list = []
        for config in self.esp_configs:
            esp_config_list.append({'target_ip': config['target_ip'], 'fps': config['fps'], 'num_bars': config['num_bars']})
        return esp_config_list

    def update_config(self):
        #self.esp_configs = esp_configs
        self.update_esp_config()
        with self.lock:
            #first clear the bars. Should definitely write a function in Bar's to do this. 
            for artnet_device in self.artnet_devices:
                packet = bytearray(artnet_device.packet_size)
                bars = self.device_bars_map[artnet_device]
                offset = 0
                for bar in bars:
                    pixels = bytearray(bar.num_leds)
                    packet[offset:offset + len(pixels)] = pixels
                    offset += len(pixels)
                    artnet_device.send(packet)
            #then reinitialize the devices      
            self.initialize_devices()
    
    def change_mode(self,mode = 0):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.state = mode  # Set initial state if needed
            if len(bars) > 0:
                bars[0].update_config()
    
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
        start_time = time.time()
        fft_data = self.process_audio(led_queue)

        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.update(fft_data)
        end_time = time.time()
        duration = end_time - start_time
        #print(f"Update duration: {duration:.4f}s")

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

            if len(packet) == artnet_device.packet_size: 
                artnet_device.send(packet)
            else:
                print(f"packet size: {len(packet)}")
                print(f"declared packet size: {artnet_device.packet_size}") 
        # Timing control is handled in the main loop
        
    ##GET AND SET FUNCTIONS
    #MODE OPTIONS
    #Get all modes
    def get_all_modes(self):
        modes = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                modes.append(bar.mode_manager.get_all_modes())
        return modes[0]
    
    def get_current_mode(self):
        modes = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                modes.append(bar.get_mode())
        return modes[0]
    
    def remove_auto_cycle_mode(self,idx):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.mode_manager.remove_auto_cycle_mode(idx)
            if len(bars) > 0:
                bars[0].mode_manager.update_mode_config()
    
    def add_auto_cycle_mode(self,idx):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.mode_manager.add_auto_cycle_mode(idx)
            if len(bars) > 0:
                bars[0].mode_manager.update_mode_config()
                
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
            if len(bars) > 0:
                bars[0].update_config()
            
    def get_time_per_mode(self):
        time_per_mode = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                time_per_mode.append(bar.time_per_mode)
        return time_per_mode[0]
    def set_time_per_mode(self, time_per_mode):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.time_per_mode = time_per_mode
            if len(bars) > 0:
                bars[0].update_config()
    
    #LIGHTING OPTIONS
    #Update brightness
    def set_brightness(self, brightness):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.brightness = brightness
            if len(bars) > 0:
                bars[0].update_config()
                    
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
            if len(bars) > 0:
                bars[0].update_config()
            
    def get_fade(self):
        fade = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                fade.append(bar.fade)
        return fade[0]
    
    #Update mid debounce
    def set_mid_debounce(self, mid_debounce):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.mid_debounce = mid_debounce
            if len(bars) > 0:
                bars[0].update_config()
    def get_mid_debounce(self):
        mid_debounce = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                mid_debounce.append(bar.mid_debounce)
        return mid_debounce[0]
    
    def set_bass_debounce(self, bass_debounce):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.bass_debounce = bass_debounce
            if len(bars) > 0:
                bars[0].update_config()
    def get_bass_debounce(self):
        bass_debounce = []
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map.get(artnet_device, [])
            for bar in bars:
                bass_debounce.append(bar.bass_debounce)
        return bass_debounce[0]
    
    
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
            if len(bars) > 0:
                bars[0].update_config()
        self.update_colours()
        
    #AUDIO REACTIVITY OPTIONS
    #Trigger style
    def set_trigger_style(self, trigger_style):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.trigger_style = trigger_style
            if len(bars) > 0:
                bars[0].update_config()
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
            if len(bars) > 0:
                bars[0].update_config()
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
            if len(bars) > 0:
                bars[0].update_config()
        
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
            if len(bars) > 0:
                bars[0].update_config()
    
    #Get and set the mid threshold
    def set_mid_threshold(self, mid_threshold):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.mid_threshold = mid_threshold
            if len(bars) > 0:
                bars[0].update_config()
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
            if len(bars) > 0:
                bars[0].update_config()
    
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
            if len(bars) > 0:
                bars[0].update_config()
