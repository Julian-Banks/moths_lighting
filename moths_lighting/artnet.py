from stupidArtnet import StupidArtnet
import time
import random
from scipy.signal import resample
import numpy as np
from bar import Bar
#delete this shit
target_ip = '255.255.255.255'
universe = 0
NUM_LEDS = 144
packet_size = NUM_LEDS*3

#move config into the main foloder, 


class ArtnetController: 
	def __init__(self,num_bars, num_esps,esp_configs):
		
		self.artnet_devices = []
		for config in esp_configs:
			target_ip = config['target_ip']
			universe = config['universe']
			packet_size = (config.get('num_bars')*96*3)
			fps = config.get('fps',40)
		
			#Create new artnet device
			artnet_device = StupidArtnet(target_ip, universe, packet_size, fps, True, True)

			#Add the new artnet device to the list of artnet devices
			self.artnet_devices.append(artnet_device)
   
			bars = [Bar(bar_id) for bar_id in range(config.get('num_bars'))]
			self.device_bars_map[artnet_device] = bars
  
		self.packet = bytearray(packet_size)
		
	def start_mode(self):
		for artnet_device in self.artnet_devices:
			bars = self.device_bars_map[artnet_device]
			for bar in bars:
				bar.start_generator()
				#MAYBE I WRITE A FUNCTION THAT STARTS ONE THREAD IN THIS CLASS THAT CONTINOUSLY CYCLES THROUGH THE BAR CLASSES TO UPDATED PIXELS RATHER THAN HAVING 20 THREADS RUNNING....
	
	def end_mode(self):
		for artnet_device in self.artnet_devices:
			bars = self.device_bars_map[artnet_device]
			for bar in bars:
				bar.stop_generator()
    
	def send_data(self):
		#update packet for each artnet instance using bar.get_pixels
		start_time = time.time()
		for artnet_device in self.artnet_devices:
			packet = bytearray(self.packet_size)
			bars = self.device_bars_map[artnet_device]
			offset = 0
			for bar in bars:
				pixels = bar.get_pixels()
				packet[offset:offset + len(pixels)] = pixels
				offset += len(pixels)
   			#this handles setting the packet and sending at the sametime. Is this faster than setting the packet and sending asynchonously?
			artnet_device.send(packet)
		
  		#Timing control to ensure constant FPS
		elapsed_time = time.time() - start_time
		sleep_time = max(0, 1/self.fps - elapsed_time)
		time.sleep(sleep_time)
   
	#haven't changed any of this yet, probably all broken as well. 
	def update(led_queue):
		buffer = []
		packet = bytearray(packet_size)
		while not led_queue.empty():
			led_data = led_queue.get()
			buffer.append(led_data)
			#print('buffer had some stuff')
		if len(buffer)>1:
			#print('buffer was not false')
			led_array = np.array(buffer)
			led_avg = np.mean(led_array,axis=0)
			buffer = []
			max_mag = max(led_avg)
			scaled_mag = (led_avg/max_mag)*200
			scaled_mag = scaled_mag.astype(int)
			new_indices = np.linspace(0, len(scaled_mag),packet_size,dtype = int)
			#print(f"length of linspace {new_indices}")
			data = np.interp(new_indices, np.arange(len(scaled_mag)),scaled_mag)
			#print(f"length of packet before to bytes {len(packet)}")
			packet = data.astype(np.int8).tobytes()
			#print(len(packet))
			#packet[:] = [i]*len(packet)
			a.set(packet)
			a.show()
