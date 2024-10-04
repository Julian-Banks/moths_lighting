import pyaudio
import numpy as np
import threading
import time
from scipy.signal import butter, lfilter
from scipy.signal import find_peaks

class AudioProcessor:
    def __init__(self, fft_queue, led_queue, audio_sensitivity):
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100  # Increased sample rate
        self.chunk = 512  # Adjusted chunk size
        self.num_bins = 512  # Adjusted FFT size
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
        
        #BPM variables
        '''
        self.energy_history = np.zeros(int(self.rate))
        self.beat_interval_history = []  # Stores intervals between beats
        self.bpm = 0                  # Current BPM
        self.last_beat_time = None    # Timestamp of the last detected beat
        self.min_bpm = 40            # Minimum BPM to consider
        self.max_bpm = 240            # Maximum BPM to consider
        self.beat_threshold = 0.8     # Threshold for beat detection
        '''
                # Beat detection parameters
        self.beat_interval_history = []
        self.bpm = 0
        self.last_beat_time = None
        self.min_bpm = 60
        self.max_bpm = 180
        self.beat_threshold = 1.5  # Adjust as needed
        self.energy_history = np.zeros(43)  # Store energies of recent chunks
        self.energy_index = 0

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
                
        #Detect beat
        #self.detect_beat(audio_data)
        
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
            
    '''
    def detect_beat(self, audio_data):
        # Calculate the energy of the audio signal
        energy = audio_data ** 2

        # Update energy history
        self.energy_history = np.roll(self.energy_history, -len(energy))
        self.energy_history[-len(energy):] = energy

        # Use find_peaks to detect peaks in the energy signal
        peaks, properties = find_peaks(self.energy_history, height=np.mean(self.energy_history) * self.beat_threshold, distance=int(self.chunk))

        current_time = time.time()

        # Process detected peaks
        for peak in peaks:
            # Convert peak index to time
            peak_time = current_time - (len(self.energy_history) - peak) / self.rate
            with self.lock:
                if self.last_beat_time is not None:
                    interval = peak_time - self.last_beat_time
                    bpm = 60 / interval
                    if self.min_bpm <= bpm <= self.max_bpm:
                        self.beat_interval_history.append(interval)
                        if len(self.beat_interval_history) > 5:
                            self.beat_interval_history.pop(0)
                        avg_interval = np.mean(self.beat_interval_history)
                        self.bpm = 60 / avg_interval
                self.last_beat_time = peak_time
            # You can add code here to trigger visual effects on beat
            print(f"Beat detected! BPM: {self.bpm:.2f}")'''
            
    
    def detect_beat(self, audio_data):
        # Calculate the energy of the audio chunk
        energy = np.sum(audio_data ** 2) / len(audio_data)

        # Update energy history
        self.energy_history[self.energy_index % len(self.energy_history)] = energy
        self.energy_index += 1
        average_energy = np.mean(self.energy_history)

        # Beat detection logic
        if energy > self.beat_threshold * average_energy:
            current_time = time.time()
            with self.lock:
                min_interval = 60 / self.max_bpm  # Minimum interval between beats
                if self.last_beat_time is not None:
                    interval = current_time - self.last_beat_time
                    if interval < min_interval:
                        # Ignore this beat; too soon after previous beat
                        return
                    bpm = 60 / interval
                    if self.min_bpm <= bpm <= self.max_bpm:
                        self.beat_interval_history.append(interval)
                        if len(self.beat_interval_history) > 5:
                            self.beat_interval_history.pop(0)
                        avg_interval = np.mean(self.beat_interval_history)
                        self.bpm = 60 / avg_interval
                else:
                    # First beat detected
                    self.bpm = 0  # Initialize BPM
                self.last_beat_time = current_time
                print(f"Beat detected! BPM: {self.bpm:.2f}")



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
    
    #Helper Get and Set functions
    
    def get_scaler(self):
        return self.global_max_mag
    
    def set_sensitivity(self, sensitivity):
        with self.lock:
            self.audio_sensitivity = sensitivity
            
    def get_sensitivity(self): 
        return self.audio_sensitivity 