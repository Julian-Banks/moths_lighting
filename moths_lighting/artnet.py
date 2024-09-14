from stupidArtnet import StupidArtnet
import time
import numpy as np
from bar import Bar

class ArtnetController:
    def __init__(self, num_esps, esp_configs, fps=45):
        self.device_bars_map = {}
        self.artnet_devices = []
        self.fps = fps
        for config in esp_configs:
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

    def end_mode(self):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.state = "off"

    def update_bars(self, fft_data):
        for artnet_device in self.artnet_devices:
            bars = self.device_bars_map[artnet_device]
            for bar in bars:
                bar.update(fft_data)

    def send_data(self):
        start_time = time.time()
        for artnet_device in self.artnet_devices:
            packet = bytearray(artnet_device.packet_size)
            bars = self.device_bars_map[artnet_device]
            offset = 0
            for bar in bars:
                pixels = bar.get_pixels()
                packet[offset:offset + len(pixels)] = pixels
                offset += len(pixels)
            artnet_device.send(packet)
        # Timing control to ensure constant FPS
        elapsed_time = time.time() - start_time
        sleep_time = max(0, 1 / self.fps - elapsed_time)
        time.sleep(sleep_time)
