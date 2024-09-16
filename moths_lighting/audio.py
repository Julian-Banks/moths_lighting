import pyaudio
import numpy as np
import threading
from scipy.signal import butter, lfilter

class AudioProcessor:
    def __init__(self, fft_queue, led_queue, audio_sensitivity):
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 96200  # Increased sample rate
        self.chunk = 1024  # Adjusted chunk size
        self.num_bins = 1024  # Adjusted FFT size
        self.fft_queue = fft_queue
        self.led_queue = led_queue
        self.audio_sensitivity = audio_sensitivity
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.lock = threading.Lock()
        # High-pass filter parameters
        self.highpass_cutoff = 20  # Hz
        self.b, self.a = butter(4, self.highpass_cutoff / (0.5 * self.rate), btype='high', analog=False)
        self.global_max_mag = 0
        self.decay_factor = 0.999 # Decay factor to reduce the max over time
        
    def set_sensitivity(self, sensitivity):
        with self.lock:
            self.audio_sensitivity = sensitivity
            
    def get_sensitivity(self): 
        return self.audio_sensitivity 

    def start_stream(self):
        try:
            self.stream = self.p.open(format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      frames_per_buffer=self.chunk)
            print('Audio Stream started successfully')
        except Exception as e:
            print(f'Failed to start audio stream: {e}')

    def process_audio(self):
        data = self.stream.read(self.chunk, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        # Normalize audio data
        audio_data /= 32768.0
        # Remove DC offset
        audio_data -= np.mean(audio_data)
        # Apply high-pass filter
        audio_data = lfilter(self.b, self.a, audio_data)
        # Apply sensitivity
        audio_data *= self.audio_sensitivity
        # Apply window function
        window = np.hanning(len(audio_data))
        audio_data *= window
        # Compute FFT
        fft_data = np.fft.rfft(audio_data, n=self.num_bins)
        fft_mag = np.abs(fft_data)
        fft_mag = self.normalise_to_global_max(fft_mag)
        # Limit to max frequency
        max_freq = 5000
        freqs = np.fft.rfftfreq(self.num_bins, 1 / self.rate)
        idx_max_freq = np.where(freqs <= max_freq)[0][-1]
        fft_mag = fft_mag[:idx_max_freq + 1]
        if self.fft_queue:
            self.fft_queue.put(fft_mag)
        if self.led_queue:
            self.led_queue.put(fft_mag)

    def normalise_to_global_max(self,fft_data):
        
        # Apply the decay to the global max magnitude
        self.global_max_mag *= self.decay_factor
        
        #get the current max
        current_max = np.max(fft_data)
        #update max if neccessary
        if current_max > self.global_max_mag:
            self.global_max_mag = current_max
        #normalise
        if self.global_max_mag > 0:
            fft_data /= self.global_max_mag
            
        return fft_data
            
    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
