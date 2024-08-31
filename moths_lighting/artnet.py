from stupidArtnet import StupidArtnet
import time
import random
from scipy.signal import resample
import numpy as np

target_ip = '255.255.255.255'
universe = 0
NUM_LEDS = 144
packet_size = NUM_LEDS*3

a = StupidArtnet(target_ip, universe, packet_size, 30,True,True)
packet = bytearray(packet_size)

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
