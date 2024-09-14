import threading
import time
import numpy as np
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

class Display:
    def __init__(self, audio_processor, artnet_controller, esp_configs, audio_sensitivity,
                 artnet_fps_queue, fft_fps_queue, fft_queue):
        # Initialize display device
        self.device = ssd1306(i2c(port=1, address=0x3C), width=128, height=64)
        self.font = ImageFont.load_default()

        # Initialize system components
        self.audio_processor = audio_processor
        self.artnet_controller = artnet_controller
        self.esp_configs = esp_configs
        self.audio_sensitivity = audio_sensitivity
        self.artnet_fps_queue = artnet_fps_queue
        self.fft_fps_queue = fft_fps_queue
        self.fft_queue = fft_queue  # FFT data queue

        # Initialize state variables
        self.state = "MainScreen"
        self.position = 0
        self.last_position = 0
        self.menu_items = ["Lighting Mode", "Brightness", "Audio Sensitivity", "FPS", "Options"]
        self.selected_mode = 0
        self.brightness = 50  # Display range 0-100
        self.internal_brightness = self.brightness / 100.0  # Internal processing range 0-1

        # Initialize FPS tracking
        self.artnet_fps = 0
        self.fft_fps = 0

        # Start the display update thread
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.update_display)
        self.thread.start()

    def on_position_change(self, position):
        with self.lock:
            if self.state == "MainScreen":
                # Update menu position
                self.position = position % len(self.menu_items)
            elif self.state == "Adjusting":
                # Calculate position delta
                delta = position - self.last_position
                self.last_position = position

                # Adjust parameters based on delta
                if self.current_parameter == "brightness":
                    self.brightness = max(0, min(100, self.brightness + delta))
                    self.internal_brightness = self.brightness / 100.0
                    self.artnet_controller.set_brightness(self.internal_brightness)
                elif self.current_parameter == "audio_sensitivity":
                    self.audio_sensitivity = max(0, min(2, self.audio_sensitivity + (delta * 0.1)))
                    self.audio_processor.set_sensitivity(self.audio_sensitivity)

    def on_button_push(self):
        with self.lock:
            if self.state == "MainScreen":
                selected_item = self.menu_items[self.position]
                if selected_item == "Brightness":
                    # Enter Adjusting state for brightness
                    self.state = "Adjusting"
                    self.current_parameter = "brightness"
                    self.last_position = self.position
                elif selected_item == "Audio Sensitivity":
                    # Enter Adjusting state for audio sensitivity
                    self.state = "Adjusting"
                    self.current_parameter = "audio_sensitivity"
                    self.last_position = self.position
                elif selected_item == "Options":
                    # Enter Options menu
                    self.state = "OptionsMenu"
                    self.position = 0
            elif self.state == "OptionsMenu":
                options = ["Configure Controllers", "Show FFT Stats", "Select Modes"]
                selected_option = options[self.position % len(options)]
                if selected_option == "Configure Controllers":
                    self.configure_controllers()
                elif selected_option == "Show FFT Stats":
                    self.show_fft_stats()
                elif selected_option == "Select Modes":
                    self.select_modes()
            elif self.state == "Adjusting":
                # Return to MainScreen from Adjusting state
                self.state = "MainScreen"
            elif self.state == "FFT_Display":
                # Return to MainScreen from FFT display
                self.state = "MainScreen"

    def configure_controllers(self):
        # Placeholder for controller configuration
        with self.lock:
            self.state = "InDevelopment"

    def show_fft_stats(self):
        # Enter FFT display state
        with self.lock:
            self.state = "FFT_Display"

    def select_modes(self):
        # Placeholder for mode selection
        with self.lock:
            self.state = "InDevelopment"

    def update_display(self):
        while not self.stop_flag.is_set():
            with self.lock:
                # Update FPS values
                self.artnet_fps = self.get_fps(self.artnet_fps_queue)
                self.fft_fps = self.get_fps(self.fft_fps_queue)

                # Render display based on current state
                if self.state == "MainScreen":
                    self.draw_main_screen()
                elif self.state == "OptionsMenu":
                    self.draw_options_menu()
                elif self.state == "Adjusting":
                    self.draw_adjusting_screen()
                elif self.state == "FFT_Display":
                    self.draw_fft_display()
                elif self.state == "InDevelopment":
                    self.draw_in_development()
            time.sleep(0.1)

    def draw_main_screen(self):
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            # Header with logo
            draw.text((0, 0), "Moths Inc", font=self.font, fill=255)
            draw.line([(60, 0), (64, 8), (68, 0)], fill=255)  # Moth logo

            # Menu items with current values
            for idx, item in enumerate(self.menu_items):
                y = 16 + idx * 10
                prefix = "-> " if idx == self.position else "   "
                value_str = ""
                if item == "Brightness":
                    value_str = f": {int(self.brightness)}"
                elif item == "Audio Sensitivity":
                    value_str = f": {round(self.audio_sensitivity, 2)}"
                elif item == "FPS":
                    value_str = f": Art {self.artnet_fps} FFT {self.fft_fps}"
                draw.text((0, y), f"{prefix}{item}{value_str}", font=self.font, fill=255)
            self.device.display(img)

    def draw_options_menu(self):
        options = ["Configure Controllers", "Show FFT Stats", "Select Modes"]
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            # Options header
            draw.text((0, 0), "Options", font=self.font, fill=255)
            # Options items
            for idx, option in enumerate(options):
                y = 16 + idx * 10
                prefix = "-> " if idx == self.position else "   "
                draw.text((0, y), f"{prefix}{option}", font=self.font, fill=255)
            self.device.display(img)

    def draw_adjusting_screen(self):
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            # Header
            draw.text((0, 0), f"Adjust {self.current_parameter.replace('_', ' ').title()}", font=self.font, fill=255)
            # Display current value
            if self.current_parameter == "brightness":
                value = int(self.brightness)
                draw.text((0, 20), f"Value: {value}", font=self.font, fill=255)
            elif self.current_parameter == "audio_sensitivity":
                value = round(self.audio_sensitivity, 2)
                draw.text((0, 20), f"Value: {value}", font=self.font, fill=255)
            self.device.display(img)

    def draw_fft_display(self):
        device = self.device

        # Get latest FFT data
        results_buffer = []
        while not self.fft_queue.empty():
            fft_data = self.fft_queue.get()
            results_buffer.append(fft_data)

        if results_buffer:
            fft_array = np.mean(np.array(results_buffer), axis=0)
            data = fft_array
        else:
            data = np.zeros(64)

        max_magnitude = max(data) if np.max(data) > 0 else 1
        scaled_magnitude = (data / max_magnitude) * device.height
        scaled_magnitude = scaled_magnitude.astype(int)

        with Image.new('1', (device.width, device.height)) as img:
            draw = ImageDraw.Draw(img)

            # Draw FFT bars
            num_bars = min(device.width, len(scaled_magnitude))
            bar_width = max(1, device.width // num_bars)
            for i in range(num_bars):
                x = i * bar_width
                y_top = device.height - scaled_magnitude[i]
                draw.rectangle([x, y_top, x + bar_width - 1, device.height], fill=255)

            # Display FFT FPS
            draw.text((0, 0), f"FFT FPS: {self.fft_fps}", font=self.font, fill=255)
            self.device.display(img)

    def draw_in_development(self):
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            # Placeholder message
            draw.text((0, 0), "Feature in Development", font=self.font, fill=255)
            self.device.display(img)

    def get_fps(self, fps_queue):
        fps = None
        while not fps_queue.empty():
            fps = fps_queue.get()
        return fps if fps is not None else 0

    def clear(self):
        self.device.clear()
