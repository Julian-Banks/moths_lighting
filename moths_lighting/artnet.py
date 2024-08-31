from stupidArtnet import StupidArtnet
import time
import random

target_ip = '255.255.255.255'
universe = 0
num_leds = 144
packet_size = num_leds * 3

a = StupidArtnet(target_ip, universe,packet_size, 30,True,True)
print(a)

packet = bytearray(packet_size)

a.start()
a.start()

for x in range(100):
	for i in range(packet_size):
		packet[i] = random.randint(0,150)
	a.set(packet)
	time.sleep(.2)

a.blackout()
a.stop()

del a
