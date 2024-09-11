from display import Display
from encoder import Encoder
from audio import AudioProcessor
from artnet import ArtnetController
import threading
import time
from queue import Queue
import pyaudio

fft_queue = Queue()
led_queue = Queue()
fps_queue = Queue()

FPS_target = 40

	#create Audio class. create an  instance of the class.
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
NUM_BINS = 1024



esp_configs = [
    {'target_ip': '255.255.255.255', 'universe': 0, 'fps': FPS_target, 'num_bars': 1},
    {'target_ip': '192.168.1.102', 'universe': 0,'fps': FPS_target, 'num_bars': 1},
    {'target_ip': '192.168.1.103', 'universe': 0,'fps': FPS_target, 'num_bars': 1},
]

def artnet_thread(artnet_controller):
	print('Starting the Artnet Thread')
	#start the bars generating patterns
	artnet_controller.start_mode()
	print('finished Start mode function')
	while not stop_flag.is_set():
		artnet_controller.send_data()
		'''
		start_time = time.time()
		artnet.update(led_queue)
		time.sleep(0.05)
		elapsed_time = time.time() - start_time
		fps = 1/elapsed_time
		fps_queue.put(fps)'''

	artnet_controller.end_mode()

def audio_thread(audio_processor):

	print('Starting the Audio Thread')
	audio_processor.running = True
	audio_processor.start_stream()

	while not stop_flag.is_set():
		#audio_processor.process_audio()
		time.sleep(1)
	audio_processor.running = False
	audio_processor.stop_stream()


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
	#get the class to run the fft in a state and change the state when needed.
	#start the audio thread
	print('About to create Audio class and start thread')
	audio_processor = AudioProcessor(FORMAT, CHANNELS, RATE, CHUNK, NUM_BINS, fft_queue, led_queue)
	#audio_thread_instance = threading.Thread(target=audio_thread(audio_processor))
	#audio_thread_instance.start()

	print('About to create ArtnetController and start thread')
	#create Artnet class. create an instance of the class.
	artnet_controller = ArtnetController(esp_configs=esp_configs, num_esps = 1)

	#start the artnet Thread
	artnet_thread_instance = threading.Thread(target=artnet_thread(artnet_controller))
	artnet_thread_instance.start()

	print('About to create Display and encoder')
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
		#display Cleanup

		#artnet cleanup
  
		#audio cleanup


if  __name__ == "__main__":
	stop_flag = threading.Event()
	main()
