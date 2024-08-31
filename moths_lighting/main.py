import display
import audio
import artnet
import threading
import time
import queue

fft_queue = queue.Queue()
led_queue = queue.Queue()
def display_thread():
	while not stop_flag.is_set():
		if not fft_queue.empty():
			display.update(fft_queue)


#def artnet_thread():
#	while not stop_flag.is_set():
		#artnet.update()

def audio_thread():
	while not stop_flag.is_set():
		audio.process(fft_queue,led_queue)


def main():
	audio_thread_instance = threading.Thread(target=audio_thread)
	display_thread_instance = threading.Thread(target=display_thread)

	audio_thread_instance.start()
	display_thread_instance.start()

	try:
		
		while True:
			artnet.update(led_queue)
			time.sleep(0.05)
	except KeyboardInterrupt:
		print("Interrupted by user")

	stop_flag.set()

	audio_thread_instance.join()
	display_thread_instance.join()


if  __name__ == "__main__":
	stop_flag = threading.Event()
	main()
