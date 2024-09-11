import pyaudio
import numpy as np
import time
import display

class AudioProcessor:
    #need to spend some time playing with these parameters to speed things up and reducd low frequency noise
    def __init__(self, format = pyaudio.paInt16, channels = 1, rate = 44100, chunk = 1024, num_bins = 1024, fft_queue = None, led_queue= None):
        self.format = format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.num_bins = num_bins
        self.fft_queue = fft_queue
        self.led_queue = led_queue
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.running = False

    def start_stream(self):
        try:
            self.stream = self.p.open(format=self.format,
                                  channels=self.channels,
                                  rate=self.rate,
                                  input=True,
                                  frames_per_buffer=self.chunk)
            print('Audio Stream started successfully')
            while self.running:
                self.process_audio()

        except Exception as e:
            print(f'Failed to start audio stream {e}')

    def process_audio(self):
        start_time = time.time()
        data = self.stream.read(self.chunk, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        audio_data = audio_data - np.mean(audio_data)    
        audio_data = audio_data / np.max(np.abs(audio_data))
        window = np.hanning(self.chunk)
        audio_data = audio_data * window
        fft_data = np.fft.fft(audio_data, n=self.num_bins)
        fft_mag = np.abs(fft_data)[:self.num_bins // 2]
    
        #I need to check that this is doing what I expect it to do
        max_freq = 5000
        idx_max_freq = np.argmax(np.fft.fftfreq(self.num_bins, 1 / self.rate)[:self.num_bins // 2] > max_freq)
        fft_mag = fft_mag[:idx_max_freq]

        if self.fft_queue:
            self.fft_queue.put(fft_mag)
        if self.led_queue:
            self.led_queue.put(fft_mag)

        end_time = time.time()
        duration = end_time - start_time
        print(f"Loop executed in: {duration:.6f} seconds")

       
   
    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()                 
