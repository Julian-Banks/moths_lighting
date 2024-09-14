import threading
import time
from queue import Queue

from audio import AudioProcessor
from artnet import ArtnetController
from display import Display
from encoder import Encoder

import pyaudio

# Queues for inter-thread communication
fft_queue = Queue()
led_queue = Queue()
artnet_fps_queue = Queue()
fft_fps_queue = Queue()

# Global variables
FPS_target = 40
audio_sensitivity = 0.5  # Initial audio sensitivity

# ESP32 configurations
esp_configs = [
    {'target_ip': '255.255.255.255', 'universe': 0, 'fps': FPS_target, 'num_bars': 1},
    {'target_ip': '192.168.1.102', 'universe': 0, 'fps': FPS_target, 'num_bars': 1},
    {'target_ip': '192.168.1.103', 'universe': 0, 'fps': FPS_target, 'num_bars': 1},
]

def artnet_thread(artnet_controller, led_queue):
    print('Starting the Artnet Thread')
    artnet_controller.start_mode()

    send_count = 0
    start_time = time.time()

    while not stop_flag.is_set():
        start_time = time.time()
        artnet_controller.update_bars(led_queue)
        artnet_controller.send_data()
        end_time = time.time()
        time.sleep(1/FPS_target - (end_time - start_time))
        send_count += 1

        # Calculate FPS every second
        current_time = time.time()
        if current_time - start_time >= 1.0:
            artnet_fps_queue.put(send_count)  # Send FPS to the display
            send_count = 0
            start_time = current_time

    artnet_controller.end_mode()

def audio_thread(audio_processor):
    print('Starting the Audio Thread')
    audio_processor.start_stream()

    send_count = 0
    start_time = time.time()

    while not stop_flag.is_set():
        audio_processor.process_audio()
        send_count += 1

        # Calculate FPS every second
        current_time = time.time()
        if current_time - start_time >= 1.0:
            fft_fps_queue.put(send_count)  # Send FPS to the display
            send_count = 0
            start_time = current_time

    audio_processor.stop_stream()

def on_position_change(position):
    display.on_position_change(position)

def on_button_push():
    display.on_button_push()

def main():
    print('Initializing Audio Processor...')
    audio_processor = AudioProcessor(fft_queue, led_queue, audio_sensitivity)
    audio_thread_instance = threading.Thread(target=audio_thread, args=(audio_processor,))
    audio_thread_instance.start()

    print('Initializing Artnet Controller...')
    artnet_controller = ArtnetController(esp_configs=esp_configs)
    artnet_thread_instance = threading.Thread(target=artnet_thread, args=(artnet_controller, led_queue))
    artnet_thread_instance.start()

    print('Initializing Display and Encoder...')
    global display
    display = Display(audio_processor, artnet_controller, esp_configs, audio_sensitivity,
                      artnet_fps_queue, fft_fps_queue, fft_queue)
    encoder = Encoder(pin_A=22, pin_B=27, pin_button=17,
                      on_position_change=on_position_change,
                      on_button_push=on_button_push)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        stop_flag.set()
        display.stop_flag.set()
        audio_thread_instance.join()
        artnet_thread_instance.join()
        display.thread.join()
        encoder.cleanup()
        print("All threads joined and cleanup done")

if __name__ == "__main__":
    stop_flag = threading.Event()
    main()

