import threading
import time
from queue import Queue
import yaml
import pyaudio
from collections import deque

from audio import AudioProcessor
from artnet import ArtnetController
from display import Display
from encoder import Encoder
from colour_manager import ColourManager



# Queues for inter-thread communication
fft_queue = Queue()  #this queue is for fft_mag data and is used by the display to process and show information to the user
led_queue = Queue()  # this queue is the same fft_mag data but it is used by artnet controller to update led strips 
artnet_fps_queue = Queue() #this queue is used to store how many frames of Artnet are being sent per second.
fft_fps_queue = Queue()   #this queue is used to store how many frames of FFT are being processed per second.


def artnet_thread(artnet_controller, led_queue):
    print('Starting the Artnet Thread')
    send_count = 0
    start_time = time.time()
    loop_durations = deque(maxlen=1000)  
    
    while not stop_flag.is_set():
        iteration_start_time = time.time()
        
        with artnet_controller.lock:
            update_start_time = time.time()
            artnet_controller.update_bars(led_queue)
            update_end_time = time.time()
            
            send_start_time = time.time()
            artnet_controller.send_data()
            send_end_time = time.time()

        iteration_end_time = time.time()
        loop_duration = iteration_end_time - iteration_start_time
        loop_durations.append(loop_duration)
        
        computation_time = iteration_end_time - iteration_start_time
        sleep_time = max(1/artnet_controller.esp_configs[0]['fps'] - computation_time, 0)
        time.sleep(sleep_time)
        
        send_count += 1

        # Calculate FPS every second
        current_time = time.time()
        if current_time - start_time >= 1.0:
            # Calculate statistics
            avg_loop_duration = sum(loop_durations) / len(loop_durations)
            max_loop_duration = max(loop_durations)
            min_loop_duration = min(loop_durations)
            update_duration = update_end_time - update_start_time
            send_duration = send_end_time - send_start_time

            # Log the statistics
            #print(f"FPS: {send_count}, Avg Loop Duration: {avg_loop_duration:.4f}s, Max: {max_loop_duration:.4f}s, Min: {min_loop_duration:.4f}s")
            #print(f"Update Duration: {update_duration:.4f}s, Send Duration: {send_duration:.4f}s")

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
    
    print('Initializing Colour Manager...')
    colour_manager = ColourManager()
    
    print('Initializing Audio Processor...')
    audio_processor = AudioProcessor(fft_queue=fft_queue, led_queue=led_queue)
    audio_thread_instance = threading.Thread(target=audio_thread, args=(audio_processor,))
    audio_thread_instance.start()

    print('Initializing Artnet Controller...')
    artnet_controller = ArtnetController(colour_manager=colour_manager)
    artnet_thread_instance = threading.Thread(target=artnet_thread, args=(artnet_controller, led_queue))
    artnet_thread_instance.start()

    print('Initializing Display and Encoder...')
    global display
    display = Display(audio_processor, artnet_controller, colour_manager,
                      artnet_fps_queue, fft_fps_queue, fft_queue)
    encoder = Encoder(pin_A=22, pin_B=27, pin_button=17,
                      callback=on_position_change,
                      button_callback=on_button_push)

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

