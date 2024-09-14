from moths_lighting.display_backup import Display
from moths_lighting.encoder_backup import Encoder
from moths_lighting.audio_backup import AudioProcessor
from moths_lighting.artnet_backup import ArtnetController
import threading
import time
from queue import Queue
import pyaudio
import queue

fft_queue = Queue()
led_queue = Queue()
fps_queue = Queue()

FPS_target = 40

# Create Audio class instance
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 512  # Reduced chunk size for lower latency
NUM_BINS = 512  # Reduced number of bins

esp_configs = [
    {'target_ip': '255.255.255.255', 'universe': 0, 'fps': FPS_target, 'num_bars': 1},
    {'target_ip': '192.168.1.102', 'universe': 0, 'fps': FPS_target, 'num_bars': 1},
    {'target_ip': '192.168.1.103', 'universe': 0, 'fps': FPS_target, 'num_bars': 1},
]

def artnet_thread(artnet_controller, led_queue):
    print('Starting the Artnet Thread')
    # Start the bars generating patterns
    artnet_controller.start_mode()
    print('Finished Start mode function')
    while not stop_flag.is_set():
        try:
            fft_data = led_queue.get(timeout=0.1)
            artnet_controller.update_bars(fft_data)
        except queue.Empty:
            pass
        artnet_controller.send_data()
    artnet_controller.end_mode()

def audio_thread(audio_processor):
    print('Starting the Audio Thread')
    audio_processor.start_stream()
    while not stop_flag.is_set():
        audio_processor.process_audio()
    audio_processor.stop_stream()

def on_position_change(display, position):
    display.on_position_change(position)

def on_button_push(display):
    print(f"State: {display.position}")
    if display.state == "Main_Menu":
        if display.position == 0:
            display.on_button_push(fps_queue)
        elif display.position == 1:
            display.on_button_push(fft_queue)
    else:
        display.on_button_push("None")

def main():
    print('About to create Audio class and start thread')
    audio_processor = AudioProcessor(FORMAT, CHANNELS, RATE, CHUNK, NUM_BINS, fft_queue, led_queue)
    audio_thread_instance = threading.Thread(target=audio_thread, args=(audio_processor,))
    audio_thread_instance.start()

    print('About to create ArtnetController and start thread')
    artnet_controller = ArtnetController(esp_configs=esp_configs, num_esps=1)
    artnet_thread_instance = threading.Thread(target=artnet_thread, args=(artnet_controller, led_queue))
    artnet_thread_instance.start()

    print('About to create Display and Encoder')
    display = Display()
    encoder = Encoder(pin_A=22, pin_B=27, pin_button=17, display=display, callback=on_position_change, button_callback=on_button_push)
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
        # Additional cleanup if needed

if __name__ == "__main__":
    stop_flag = threading.Event()
    main()
