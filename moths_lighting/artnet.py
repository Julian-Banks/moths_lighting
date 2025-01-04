import time
import numpy as np
import yaml
import os
from artnet_manager import ArtnetManager
from bar import Bar
import queue
import threading
from colour_manager import ColourManager
from mode_manager import ModeManager

class ArtnetController:
    def __init__(self):
        self.device_bars_map = {}
        self.artnet_devices = []
        self.num_leds = 144      #Need to update to 96 for the new strips
        self.lock = threading.Lock()
        self.initialize_devices()
        self.fps = self.esp_configs[0].get('fps', 40)
        self.esp_config_file = 'moths_lighting/config/esp_config.yaml'

    def initialize_devices(self):
        print("in initialization")
        device_bars_map = {}
        self.artnet_devices = []
        self.esp_configs = self.get_esp_config() 
        print("Got esp config")
        for config in self.esp_configs: 
            target_ip = config['target_ip']
            #universe = config['universe']
            num_bars = config.get('num_bars', 1)
            packet_size = num_bars * self.num_leds * 3
            fps = config.get('fps', 40)
            #Each artnetManger has a property of whether it is in edit_config mode or not.
            edit_config = config.get('edit_config', 1)
            #print(f"edit_config: {edit_config}")
            # Create new Artnet device
            artnet_device = ArtnetManager(target_ip, packet_size, fps, edit_config = edit_config) 
            # Add the new Artnet device to the list
            self.artnet_devices.append(artnet_device)
            
            artnet_device_idx = len(self.artnet_devices) - 1
            #Creat a colour manager for each artnet device 
            colour_manager = ColourManager(artnet_device_idx)
            #create a mode manager for each artnet device
            mode_manager = ModeManager(artnet_device_idx)
            
            # Create new bars for the Artnet device
            bars = [Bar(colour_manager,mode_manager,artnet_device_idx, self.num_leds) for _ in range(num_bars)]
            device_bars_map[artnet_device] = bars
        self.device_bars_map = device_bars_map
        print(self.device_bars_map)
        
    def get_esp_config(self):
        with open(self.esp_config_file, 'r') as file:
            return yaml.safe_load(file)
        
        
    def update_esp_config(self):
        target_file = self.esp_config_file
        to_print = self.dictify_esp_config()
        current_directory = os.getcwd()
        #print(f"Current working directory: {current_directory}")
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
            esp_config_list.append({'target_ip': config['target_ip'], 'fps': config['fps'], 'num_bars': config['num_bars'], 'edit_config': config['edit_config']})
        return esp_config_list

    def update_config(self):
        with self.lock:
            print("updating config")
            #self.esp_configs = esp_configs
            self.update_esp_config()
            #first clear the bars. Need to do this because the number of bars may have decreased and then the extra bars which are not recieving data would stay on. 
            print("all devices cleared")
            self.clear_all()
            #then reinitialize the devices      
            self.initialize_devices()
    
    
    
    def clear_all(self):   
        for artnet_device in self.artnet_devices:
            packet = bytearray(artnet_device.packet_size)
            bars = self.device_bars_map[artnet_device]
            offset = 0
            for bar in bars:
                pixels = bytearray(bar.num_leds)
                packet[offset:offset + len(pixels)] = pixels
                offset += len(pixels)
                artnet_device.send(packet)
        
    
    def change_mode(self,mode = 0):
        for artnet_device in self.artnet_devices:
            if artnet_device.edit_config:
                bars = self.device_bars_map[artnet_device]
                for bar in bars:
                    bar.state = mode  # Set initial state if needed
                if len(bars) > 0:
                    bars[0].update_config()
    
    def set_display_colour(self, value, colour):
        for artnet_device in self.artnet_devices:
            if artnet_device.edit_config:
                if value == 1:
                    bars = self.device_bars_map[artnet_device]
                    for bar in bars:
                        if bar.state != "static":
                            bar.previous_state = bar.state
                        bar.state = "static"
                        bar.colour = colour
                else:
                    bars = self.device_bars_map[artnet_device]
                    for bar in bars:
                        bar.state = bar.previous_state

    def get_display_colour(self):
        static_colour = []
        
        for artnet_device in self.artnet_devices:
            if artnet_device.edit_config:
                bars = self.device_bars_map.get(artnet_device, [])
                for bar in bars:
                    static_colour.append(0 if bar.state != "static" else 1)
        return static_colour[0]
    
    def update_colours(self):
        for artnet_device in self.artnet_devices:
            if artnet_device.edit_config:
                bars = self.device_bars_map[artnet_device]
                for bar in bars:
                    bar.update_colours()
                
    def end_mode(self):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.state = "off"

    ################################### MAIN LOOP FUNCTION TO UPDATE BARS ####################################################################
    def update_bars(self, led_queue):
        start_time = time.time()
        fft_data = self.process_audio(led_queue)
        for artnet_device in self.artnet_devices:
            if self.device_bars_map[artnet_device]:
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
    
    ########################################## END OF MAIN LOOP FUNCTIONS ################################################################
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
            if artnet_device.edit_config:
                bars = self.device_bars_map.get(artnet_device, [])
                for bar in bars:
                    modes.append(bar.get_mode())
        return modes[0]
    
    def remove_auto_cycle_mode(self,idx):
        for artnet_device in self.artnet_devices:
            if artnet_device.edit_config:
                bars = self.device_bars_map[artnet_device]
                for bar in bars:
                    bar.mode_manager.remove_auto_cycle_mode(idx)
                if len(bars) > 0:
                    bars[0].mode_manager.update_mode_config()
    
    def add_auto_cycle_mode(self,idx):
        for artnet_device in self.artnet_devices:
            if artnet_device.edit_config:
                bars = self.device_bars_map[artnet_device]
                for bar in bars:
                    bar.mode_manager.add_auto_cycle_mode(idx)
                if len(bars) > 0:
                    bars[0].mode_manager.update_mode_config()
                
    
#############################################################################
   
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
        
    
#Could nearly all of the above be solved with this simple function?.....
    def get_parameter(self, parameter):
        parameters = []
        for artnet_device in self.artnet_devices:
            if artnet_device.edit_config:
                bars = self.device_bars_map.get(artnet_device, [])
                for bar in bars:
                    parameters.append(getattr(bar, parameter))
                    #
        if len(parameters) > 0:
            return parameters[0]
        else:
            return 0 
    
    def set_parameter(self, parameter, value):
        for artnet_device in self.artnet_devices:
            if artnet_device.edit_config:
                bars = self.device_bars_map[artnet_device]
                for bar in bars:
                    setattr(bar, parameter, value)
                if len(bars) > 0:
                    bars[0].update_config()

#First we need to be able to get and set whether artnetManagers are in edit_config mode or not.
    def get_edit_config(self, controller_idx):
        return self.esp_configs[controller_idx]['edit_config']
    
    def set_edit_config(self, edit_config, controller_idx):
        self.esp_configs[controller_idx]['edit_config'] = edit_config
        self.update_config()
        
        
    #Colour Functions
    def add_colour(self,colour):
            for artnet_device in self.artnet_devices: 
                if artnet_device.edit_config :
                    bars = self.device_bars_map[artnet_device]
                    for bar in bars : 
                        bar.colour_manager.add_colour(colour)
                    if len(bars) > 0:
                        bars[0].update_colours()
                        
    def update_colour(self, idx, colour):
            for artnet_device in self.artnet_devices: 
                if artnet_device.edit_config :
                    bars = self.device_bars_map[artnet_device]
                    for bar in bars : 
                        bar.colour_manager.update_colour(idx, colour)
                        bar.update_colours()
                    if len(bars) > 0:
                        bars[0].colour_manager.update_config()
                        
    def remove_colour(self, idx ):
            for artnet_device in self.artnet_devices: 
                if artnet_device.edit_config :
                    bars = self.device_bars_map[artnet_device]
                    for bar in bars : 
                        bar.colour_manager.remove_colour(idx )
                    if len(bars) > 0:
                        bars[0].update_colours()
                        
    def get_colour_list(self):
        for artnet_device in self.artnet_devices: 
            if artnet_device.edit_config:
                bars = self.device_bars_map[artnet_device]
                return bars[0].colour_manager.get_colour_list()