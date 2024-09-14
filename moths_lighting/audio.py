import pyaudio
import numpy as np
import threading
from scipy.signal import butter, lfilter

class AudioProcessor:
    def __init__(self, fft_queue, led_queue, audio_sensitivity):
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 88200  # Increased sample rate
        self.chunk = 2048  # Adjusted chunk size
        self.num_bins = 2048  # Adjusted FFT size
        self.fft_queue = fft_queue
        self.led_queue = led_queue
        self.audio_sensitivity = audio_sensitivity
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.lock = threading.Lock()
        # High-pass filter parameters
        self.highpass_cutoff = 150  # Hz
        self.b, self.a = butter(4, self.highpass_cutoff / (0.5 * self.rate), btype='high', analog=False)

    def set_sensitivity(self, sensitivity):
        with self.lock:
            self.audio_sensitivity = sensitivity

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
        # Limit to max frequency
        max_freq = 5000
        freqs = np.fft.rfftfreq(self.num_bins, 1 / self.rate)
        idx_max_freq = np.where(freqs <= max_freq)[0][-1]
        fft_mag = fft_mag[:idx_max_freq + 1]
        if self.fft_queue:
            self.fft_queue.put(fft_mag)
        if self.led_queue:
            self.led_queue.put(fft_mag)

    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()

'''import pyaudio
import numpy as np
import threading

class AudioProcessor:
    def __init__(self, fft_queue, led_queue, audio_sensitivity):
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.chunk = 512
        self.num_bins = 512
        self.fft_queue = fft_queue
        self.led_queue = led_queue
        self.audio_sensitivity = audio_sensitivity
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.lock = threading.Lock()

    def set_sensitivity(self, sensitivity):
        with self.lock:
            self.audio_sensitivity = sensitivity

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
        # Apply sensitivity
        audio_data *= self.audio_sensitivity
        # Apply window function
        window = np.hanning(len(audio_data))
        audio_data *= window
        # Compute FFT
        fft_data = np.fft.rfft(audio_data, n=self.num_bins)
        fft_mag = np.abs(fft_data)
        # Limit to max frequency
        max_freq = 5000
        freqs = np.fft.rfftfreq(self.num_bins, 1 / self.rate)
        idx_max_freq = np.where(freqs <= max_freq)[0][-1]
        fft_mag = fft_mag[:idx_max_freq + 1]
        if self.fft_queue:
            self.fft_queue.put(fft_mag)
        if self.led_queue:
            self.led_queue.put(fft_mag)

    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
'''