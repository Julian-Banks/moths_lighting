import threading
import time
import numpy as np
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

class MenuItem:
    def __init__(self, name, action=None, submenu=None):
        self.name = name
        self.action = action  # Function to call when item is selected
        self.submenu = submenu  # Submenu if any

class AdjustableMenuItem(MenuItem):
    def __init__(self, name, get_value_func, set_value_func, min_value, max_value, step):
        super().__init__(name)
        self.get_value = get_value_func
        self.set_value = set_value_func
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

class Menu:
    def __init__(self, name, items=[]):
        self.name = name
        self.items = items  # List of MenuItems
        self.position = 0  # Current selected item

class MenuManager:
    def __init__(self, root_menu):
        self.menu_stack = [root_menu]
        self.adjusting = False
        self.current_adjustable_item = None

    @property
    def current_menu(self):
        return self.menu_stack[-1]

    def on_position_change(self, delta):
        if self.adjusting and self.current_adjustable_item:
            # Adjust the value
            current_value = self.current_adjustable_item.get_value()
            new_value = current_value + delta * self.current_adjustable_item.step
            new_value = max(self.current_adjustable_item.min_value, min(self.current_adjustable_item.max_value, new_value))
            self.current_adjustable_item.set_value(new_value)
        else:
            # Move the menu selection
            menu = self.current_menu
            menu.position = (menu.position + delta) % len(menu.items)

    def on_button_push(self):
        if self.adjusting:
            # Stop adjusting
            self.adjusting = False
            self.current_adjustable_item = None
        else:
            selected_item = self.current_menu.items[self.current_menu.position]
            if isinstance(selected_item, AdjustableMenuItem):
                # Start adjusting
                self.adjusting = True
                self.current_adjustable_item = selected_item
            elif selected_item.submenu:
                # Enter submenu
                self.menu_stack.append(selected_item.submenu)
            elif selected_item.action:
                # Perform action
                selected_item.action()
            elif selected_item.name == "Back":
                # Go back to previous menu
                if len(self.menu_stack) > 1:
                    self.menu_stack.pop()

    def go_back(self):
        if len(self.menu_stack) > 1:
            self.menu_stack.pop()

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
        self.brightness = 50  # Display range 0-100
        self.internal_brightness = self.brightness / 100.0  # Internal processing range 0-1
        self.bass_threshold = 0.5
        self.last_position = 0

        # Initialize FPS tracking
        self.artnet_fps = 0
        self.fft_fps = 0

        # Initialize MenuManager
        self.showing_fft = False
        self.menu_manager = MenuManager(self.create_menu_structure())

        # Start the display update thread
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.update_display)
        self.thread.start()

    def create_menu_structure(self):
        # Define get and set functions
        def get_brightness():
            return self.brightness

        def set_brightness(value):
            self.brightness = value
            self.internal_brightness = self.brightness / 100.0
            self.artnet_controller.set_brightness(self.internal_brightness)

        def get_bass_threshold():
            return self.bass_threshold

        def set_bass_threshold(value):
            self.bass_threshold = value
            self.artnet_controller.set_bass_threshold(self.bass_threshold)

        def get_audio_sensitivity():
            return self.audio_sensitivity

        def set_audio_sensitivity(value):
            self.audio_sensitivity = value
            self.audio_processor.set_sensitivity(self.audio_sensitivity)

        # Define action functions
        def show_fft_stats():
            self.show_fft_display()

        # Lighting Options Menu
        lighting_options_menu = Menu("Lighting Options", items=[
            AdjustableMenuItem("Brightness", get_brightness, set_brightness, min_value=0, max_value=100, step=1),
            # Add other adjustable items...
            MenuItem("Back")
        ])

        # Audio Options Menu
        audio_options_menu = Menu("Audio Options", items=[
            AdjustableMenuItem("Overall audio sensitivity", get_audio_sensitivity, set_audio_sensitivity, min_value=0, max_value=2, step=0.1),
            AdjustableMenuItem("Bass Threshold", get_bass_threshold, set_bass_threshold, min_value=0, max_value=2, step=0.1),
            # Add other adjustable items...
            MenuItem("Back")
        ])

        # Configure Controllers Menu
        configure_controllers_menu = Menu("Configure Controllers", items=[
            # Add adjustable items...
            MenuItem("Back")
        ])

        # Options Menu
        options_menu = Menu("Options", items=[
            MenuItem("Lighting Options", submenu=lighting_options_menu),
            MenuItem("Audio Options", submenu=audio_options_menu),
            MenuItem("Configure Controllers", submenu=configure_controllers_menu),
            MenuItem("Show FFT Stats", action=show_fft_stats),
            MenuItem("Back")
        ])

        # Main Menu
        main_menu = Menu("Main Screen", items=[
            MenuItem("Options", submenu=options_menu),
            # Add other main menu items...
        ])

        return main_menu

    def get_audio_sensitivity(self):
        return self.audio_sensitivity

    def set_audio_sensitivity(self, value):
        self.audio_sensitivity = value
        self.audio_processor.set_sensitivity(self.audio_sensitivity)

    def on_position_change(self, position):
        with self.lock:
            delta = position - self.last_position
            self.last_position = position
            if not self.showing_fft:
                self.menu_manager.on_position_change(delta)

    def on_button_push(self):
        with self.lock:
            if self.showing_fft:
                self.showing_fft = False
            else:
                self.menu_manager.on_button_push()

    def update_display(self):
        while not self.stop_flag.is_set():
            with self.lock:
                # Update FPS values
                artnet_fps = self.get_fps(self.artnet_fps_queue)
                self.artnet_fps = artnet_fps if artnet_fps is not None else self.artnet_fps

                fft_fps = self.get_fps(self.fft_fps_queue)
                self.fft_fps = fft_fps if fft_fps is not None else self.fft_fps

                if self.showing_fft:
                    self.draw_fft_display()
                else:
                    # Render display based on current menu
                    self.draw_current_menu()

            time.sleep(0.1)

    def draw_current_menu(self):
        menu = self.menu_manager.current_menu
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            if self.menu_manager.adjusting and self.menu_manager.current_adjustable_item:
                # Adjusting screen
                item = self.menu_manager.current_adjustable_item
                draw.text((0, 0), f"Adjust {item.name}", font=self.font, fill=255)
                value = item.get_value()
                if isinstance(value, float):
                    value_str = f"Value: {round(value, 2)}"
                else:
                    value_str = f"Value: {value}"
                draw.text((0, 20), value_str, font=self.font, fill=255)
            else:
                # Header
                draw.text((0, 0), menu.name, font=self.font, fill=255)
                # Menu items
                for idx, item in enumerate(menu.items):
                    y = 16 + idx * 10
                    prefix = "-> " if idx == menu.position else "   "
                    if isinstance(item, AdjustableMenuItem):
                        value = item.get_value()
                        if isinstance(value, float):
                            value_str = f": {round(value, 2)}"
                        else:
                            value_str = f": {value}"
                    else:
                        value_str = ""
                    draw.text((0, y), f"{prefix}{item.name}{value_str}", font=self.font, fill=255)
            self.device.display(img)

    def draw_fft_display(self):
        device = self.device
        heading_offset = 15

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
        scaled_magnitude = (data) * (device.height)
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
            draw.text((64, 0), f"fft per sec: {self.fft_fps}", font=self.font, fill=255)

            # Determine frequency resolution and find indices for 0-200 Hz
            fft_length = len(data)
            frequency_resolution = 5000 / fft_length
            max_index = int(200 / frequency_resolution)  # Find the index corresponding to 200 Hz

            # Map to pixel coordinates
            start_pixel = 0  # Start at the first pixel
            end_pixel = int(max_index / fft_length * device.width)  # Convert max_index to pixel position

            # Draw the bass threshold line across this frequency range
            threshold_y = device.height - int(self.bass_threshold * device.height)
            draw.line([(start_pixel, threshold_y), (end_pixel, threshold_y)], fill=255)

            self.device.display(img)

    def get_fps(self, fps_queue):
        fps = None
        while not fps_queue.empty():
            fps = fps_queue.get()
        return fps

    def show_fft_display(self):
        self.showing_fft = True

    def clear(self):
        self.device.clear()
