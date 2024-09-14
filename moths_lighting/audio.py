import pyaudio
import numpy as np
import time

class AudioProcessor:
    def __init__(self, format=pyaudio.paInt16, channels=1, rate=44100, chunk=512, num_bins=512, fft_queue=None, led_queue=None):
        self.format = format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.num_bins = num_bins
        self.fft_queue = fft_queue
        self.led_queue = led_queue
        self.p = pyaudio.PyAudio()
        self.stream = None

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
        start_time = time.time()
        data = self.stream.read(self.chunk, exception_on_overflow=False)
        audio_data = np.frombuffer(data, dtype=np.int16)
        # Normalize audio data
        audio_data = audio_data.astype(np.float32) / 32768.0
        # Apply window function
        window = np.hanning(len(audio_data))
        audio_data = audio_data * window
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
        end_time = time.time()
        duration = end_time - start_time
        #print(f"Audio processing time: {duration:.6f} seconds")

    def stop_stream(self):
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
