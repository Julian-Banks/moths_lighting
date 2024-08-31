import pyaudio
import numpy as np
import time
import display

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
NUM_BINS = 256

p = pyaudio.PyAudio()

stream = p.open(format = FORMAT,
		channels = CHANNELS,
		rate = RATE,
		input = True,
		frames_per_buffer = CHUNK)

print("Listening...")
i = 0
fft_avg = [0]
for j in range(NUM_BINS//2-1):
	fft_avg.append(0)
print(len(fft_avg))
try:
	while True:
		start_time = time.time()

		data = stream.read(CHUNK, exception_on_overflow=False)

		audio_data = np.frombuffer(data, dtype = np.int16)
		audio_data = audio_data - np.mean(audio_data)
		window = np.hanning(CHUNK)
		audio_data = audio_data * window

		fft_data = np.fft.fft(audio_data,n = NUM_BINS)
		fft_mag = np.abs(fft_data)[:NUM_BINS//2]
		#fft_mag_db = 20 * np.log10(fft_mag + 1e-6)
		#fft_mag_db[fft_mag_db < -60] = -60

		if i < 10:
			i = i+1
			fft_avg = fft_avg+fft_mag
		else:
			fft_avg = fft_avg/i
			display_test.draw_response(fft_avg)
			i = 0

		max_freq_idx = np.argmax(fft_mag)
		freq = max_freq_idx * RATE/CHUNK
		max_mag = fft_mag[max_freq_idx]
		#print(f"highest magnitude frequency: {freq:.2f} Hz. Max Mag: {max_mag:2f}")

		end_time = time.time()
		duration = end_time - start_time
		print(f"Loop executed in: {duration:.6f} seconds")

except KeyboardInterrupt:
	print('Interrupted by user, stopping...')

stream.stop_stream()
stream.close()
p.terminate()
