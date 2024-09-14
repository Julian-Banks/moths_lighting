from luma.core.interface.serial import i2c
import numpy as np
from luma.oled.device import ssd1309
from PIL import Image, ImageDraw, ImageFont
import time
import threading
import queue

class Display:
    def __init__(self):
        serial = i2c(port=1, address=0x3C)
        self.device = ssd1309(serial, width=128, height=64)
        self.font = ImageFont.load_default()
        self.state = "Main_Menu"
        self.main_menu = ["FPS", "FFT", "Option 2", "Option 3", "Option 4", "Option 5"]
        self.scroll_position = 0
        self.visible_items = 3
        self.position = 0
        self.thread = None

    def on_position_change(self, position):
        if self.state == "Main_Menu":
            self.position = position % len(self.main_menu)
            self.display_menu()

    def on_button_push(self, option, option2 = None):
        if self.state == "Main_Menu":
            if self.position == 0:
                self.state = "Stats"
                self.thread = threading.Thread(target=self.display_stats, args=(option,))
                self.thread.start()
            elif self.position == 1:
                self.state = "FFT_Display"
                self.thread = threading.Thread(target=self.display_fft, args=(option,option2))
                self.thread.start()
        elif self.state in ["Stats", "FFT_Display"]:
            self.state = "Main_Menu"
            if self.thread:
                self.thread.join()
            self.display_menu()

    def display_menu(self):
        position = self.position
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            y_position = 0
            if position < self.scroll_position:
                self.scroll_position = position
            elif position >= self.scroll_position + self.visible_items:
                self.scroll_position = position - self.visible_items + 1
            for index in range(self.scroll_position, min(self.scroll_position + self.visible_items, len(self.main_menu))):
                option = self.main_menu[index]
                draw.text((5, y_position), f"-> {option}" if index == position else f"   {option}", font=self.font, fill=255)
                y_position += 15
            self.device.display(img)

    def display_stats(self, fps_queue):
        while self.state == "Stats":
            results_buffer = []
            while not fps_queue.empty():
                fps_data = fps_queue.get()
                results_buffer.append(fps_data)
            if results_buffer:
                fps_array = np.array(results_buffer)
                fps = round(np.mean(fps_array),2)
                var = round(np.var(fps_array),2)
                std_deviation = round(np.std(fps_array),2)
            else:
                fps = var = std_deviation = 0
            with Image.new("1", (self.device.width, self.device.height)) as img:
                draw = ImageDraw.Draw(img)
                draw.text((10, 15), f"FPS: {fps}", font=self.font, fill=255)
                draw.text((10, 30), f"Variance: {var}", font=self.font, fill=255)
                draw.text((10, 45), f"Std Dev: {std_deviation}", font=self.font, fill=255)
                self.device.display(img)
            time.sleep(0.5)

    def display_fft(self, fft_queue,fft_fps_queue):
        device = self.device
        while self.state == "FFT_Display":
            start_time = time.time()
            
            results_buffer = []
            while not fft_queue.empty():
                fft_data = fft_queue.get()
                results_buffer.append(fft_data)

            if results_buffer:
                fft_array = np.mean(np.array(results_buffer), axis=0)
                data = fft_array
            else:
                data = np.zeros(64)

            max_magnitude = max(data) if np.max(data) > 0 else 1
            scaled_magnitude = (data / max_magnitude) * device.height
            scaled_magnitude = scaled_magnitude.astype(int)

            image = Image.new('1', (device.width, device.height), 0)
            draw = ImageDraw.Draw(image)

            # Draw FFT bars
            for x in range(min(device.width, len(scaled_magnitude))):
                draw.line([(x, device.height), (x, device.height - scaled_magnitude[x])], fill=255)

            # Add axis labels (simple implementation)
            num_labels = 5
            max_freq = 5000  # Hz
            for i in range(num_labels):
                freq = (i / (num_labels - 1)) * max_freq
                label_x = (i / (num_labels - 1)) * (device.width // 2)  # Only use half the screen
                draw.text((label_x, device.height - 10), f"{int(freq)}", font=self.font, fill=255)

            results_buffer = []
            while not fft_fps_queue.empty():
                fps_data = fft_fps_queue.get()
                results_buffer.append(fps_data)

            if results_buffer:
                fps = np.mean(np.array(results_buffer), axis=0)
                
            else:
                fps = 0
            
            # Optional: Display FFT FPS on the right side
            draw.text((device.width - 40, 5), f"FFT FPS: {fps}", font=self.font, fill=255)

            device.display(image)
            duration = time.time() - start_time
            time.sleep(max(0, 0.05 - duration))


    def clear(self):
        self.device.clear()
