import time
import numpy as np
from stupidArtnet import StupidArtnet
from bar import Bar
import queue

class ArtnetController:
    def __init__(self, esp_configs):
        self.device_bars_map = {}
        self.artnet_devices = []
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
            bars = [Bar() for _ in range(num_bars)]
            self.device_bars_map[artnet_device] = bars

    def start_mode(self):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.state = 0  # Set initial state if needed
                
    def change_mode(self,mode = 0):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.state = mode  # Set initial state if needed

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
        
    def set_brightness(self, brightness):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.brightness = brightness
                
    def set_bass_threshold(self, base_threshold):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.bass_threshold = base_threshold     
