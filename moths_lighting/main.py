from display import Display
from encoder import Encoder
import audio
from artnet import ArtnetController
import threading
import time
import queue

fft_queue = queue.Queue()
led_queue = queue.Queue()
fps_queue = queue.Queue()

FPS_target = 40

esp_configs = [
    {'target_ip': '255.255.255.255', 'universe': 0, 'fps': FPS_target},
    {'target_ip': '192.168.1.102', 'universe': 0,'fps': FPS_target},
    {'target_ip': '192.168.1.103', 'universe': 0,'fps': FPS_target},
]

def artnet_thread(artnet_controller):
	artnet_controller.start()
	while not stop_flag.is_set():
		artnet_controller.send_data()
		'''
		start_time = time.time()
		artnet.update(led_queue)
		time.sleep(0.05)
		elapsed_time = time.time() - start_time
		fps = 1/elapsed_time
		fps_queue.put(fps)'''

def audio_thread():
	while not stop_flag.is_set():
		audio.process(fft_queue,led_queue)


def on_position_change(display,position):
	display.on_position_change( position)

def on_button_push(display):
	print(f"State: {display.position}")
	if display.state == "Main_Menu":
		if display.position == 0:
			display.on_button_push(fps_queue)
		if display.position == 1:
			display.on_button_push(fft_queue)
	else:
		display.on_button_push("None")
def main():

	#create Audio class. create an  instance of the class.
	#get the class to run the fft in a state and change the state when needed.
	#start the audio thread
	audio_thread_instance = threading.Thread(target=audio_thread)
	audio_thread_instance.start()

	#create Artnet class. create an instance of the class.
	artnet_controller = ArtnetController(esp_configs)
	#Create Bar classes here? 
	
	#start the artnet Thread
	artnet_thread_instance = threading.Thread(target=artnet_thread(artnet_controller))
	artnet_thread_instance.start()

	#initialise the display and encoder
	display = Display()
	encoder = Encoder(pin_A = 22, pin_B = 27, pin_button = 17, display= display, callback= on_position_change, button_callback = on_button_push)
	display.display_menu()


	try:

		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		print("Interrupted by user")

	finally:
		stop_flag.set()
		audio_thread_instance.join()
		artnet_thread_instance.join()
		encoder.cleanup()


if  __name__ == "__main__":
	stop_flag = threading.Event()
	main()
