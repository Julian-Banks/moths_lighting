from display import Display
from encoder import Encoder
from audio import AudioProcessor
from artnet import ArtnetController
import threading
import time
from queue import Queue
import pyaudio
import queue

fft_queue = Queue()
led_queue = Queue()
artnet_fps_queue = Queue()
fft_fps_queue = Queue()

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
    
    #start fps counder
    send_count = 0
    start_time = time.time()

    #start the loop
    while not stop_flag.is_set():
        artnet_controller.update_bars(led_queue)
        artnet_controller.send_data()
        
        send_count += 1

        # Calculate FPS every second
        current_time = time.time()
        if current_time - start_time >= 1.0:
            artnet_fps_queue.put(send_count)  # Send FPS to the display
            send_count = 0
            start_time = current_time  
                  
    # End the bars generating patterns
    artnet_controller.end_mode()
    

        

def audio_thread(audio_processor):
    print('Starting the Audio Thread')
    audio_processor.start_stream()
    
    #start fps counder
    send_count = 0
    start_time = time.time()   
    
    while not stop_flag.is_set():
        #need to think of a way to pass it information about Display and Arnet so it's only calculating FFTs if it needs to and it's only posting to a queue if it needs to
        audio_processor.process_audio()
        send_count += 1

        # Calculate FPS every second
        current_time = time.time()
        if current_time - start_time >= 1.0:
            fft_fps_queue.put(send_count)  # Send FPS to the display
            send_count = 0
            start_time = current_time          
        
    audio_processor.stop_stream()



def on_position_change(display, position):
    display.on_position_change(position)

def on_button_push(display):
    print(f"State: {display.position}")
    if display.state == "Main_Menu":
        if display.position == 0:
            display.on_button_push(artnet_fps_queue)
        elif display.position == 1:
            display.on_button_push(fft_queue,fft_fps_queue)
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
        print("All threads joined and cleanup done")
        # Additional cleanup if needed

if __name__ == "__main__":
    stop_flag = threading.Event()
    main()
