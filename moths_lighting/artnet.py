from stupidArtnet import StupidArtnet
import time
import random
from scipy.signal import resample
import numpy as np

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
			packet_size = config.get('packet_size',512)
			fps = config.get('fps',40)
			
			#Create new artnet device
			artnet_device = StupidArtnet(target_ip, universe, packet_size, fps, True, True)
			artnet_
			#Add the new artnet device to the list of artnet devices
			self.artnet_devices.append(artnet_device)
  
		self.packet = bytearray(packet_size)
		
	def set(self,packet):
		self.packet = packet
		
	def show(self):
		self.a.set(self.packet)
		self.a.show()
  
	def send_data(self):
		#update packet for each artnet instance using bar.get_pixels 
		for controller in self.artnet_devices:
			controller.set( self.bar.get_pixels())#need to pass bars to the arnet controller and think of how to set number of bars on each controller. 
		#add timing in here with FPS stuff

   
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
