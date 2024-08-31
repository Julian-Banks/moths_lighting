import pyaudio
import numpy as np
import time
import display

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
NUM_BINS = 1024

p = pyaudio.PyAudio()

def process(fft_queue,led_queue):

	stream = p.open(format = FORMAT,
			channels = CHANNELS,
			rate = RATE,
			input = True,
			frames_per_buffer = CHUNK)

	try:
		while True:
			start_time = time.time()

			data = stream.read(CHUNK, exception_on_overflow=False)

			audio_data = np.frombuffer(data, dtype = np.int16)
			audio_data = audio_data - np.mean(audio_data)
			audio_data = audio_data/np.max(np.abs(audio_data))
			window = np.hanning(CHUNK)
			audio_data = audio_data * window

			fft_data = np.fft.fft(audio_data,n = NUM_BINS)
			fft_mag = np.abs(fft_data)[:NUM_BINS//2]

			max_freq = 5000
			idx_max_freq = np.argmax(np.fft.fftfreq(NUM_BINS, 1/RATE)[:NUM_BINS//2] > max_freq)
			fft_mag = fft_mag[:idx_max_freq]

			#fft_mag_db = 20 * np.log10(fft_mag + 1e-6)
			#fft_mag_db[fft_mag_db < -60] = -60
			#max_freq_idx = np.argmax(fft_mag)
			#freq = max_freq_idx * RATE/CHUNK
			#max_mag = fft_mag[max_freq_idx]
			#print(f"highest magnitude frequency: {freq:.2f} Hz. Max Mag: {max_mag:2f}")
			fft_queue.put(fft_mag)
			led_queue.put(fft_mag)
			end_time = time.time()
			duration = end_time - start_time
			#print(f"Loop executed in: {duration:.6f} seconds")

	except KeyboardInterrupt:
		print('Interrupted by user, stopping...')

	finally:
		stream.stop_stream()
		stream.close()
		p.terminate()
