from luma.core.interface.serial import i2c
import numpy as np
from luma.oled.device import ssd1309
from PIL import Image, ImageDraw, ImageFont
import time
import threading

class Display:
	def __init__(self):
		serial = i2c(port = 1, address = 0x3C)
		self.device = ssd1309(serial, width=128, height = 64)
		self.font = ImageFont.load_default()
		self.state = "Main_Menu"
		self.main_menu = ["FPS","FFT","Option 2","Option 3", "Option 4", "option 5"]
		self.scroll_position = 0
		self.visible_items = 3
		self.position = 0
		self.thread = None

	def on_position_change(self, position):
		if self.state == "Main_Menu":
			self.position = position % len(self.main_menu)
			self.display_menu()


	def on_button_push(self,option):
		if self.state == "Main_Menu":
			if self.position == 0:
				self.state = "Stats"
				self.thread = threading.Thread(target = self.display_stats, args = (option, ))
				self.thread.start()
			if self.position == 1:
				self.state = "fft"
				self.thread = threading.Thread(target = self.display_fft, args=(option,))
				self.thread.start()
		elif self.state == "Stats":
			self.state = "Main_Menu"
			self.thread.join()
			self.display_menu()
		elif self.state == "fft" :
			self.state="Main_Menu"
			self.thread.join()
			self.display_menu()

	def display_menu(self):
		position = self.position
		with Image.new("1", (self.device.width, self.device.height)) as img:
			draw = ImageDraw.Draw(img)
			y_position = 0
			if position < self.scroll_position:
				self.scroll_position = position
			elif position >= self.scroll_position+self.visible_items:
				self.scroll_position = position - self.visible_items + 1

			for index in range(self.scroll_position, min(self.scroll_position+self.visible_items,len(self.main_menu))):
				option = self.main_menu[index]

				draw.text((5,y_position), f"-> {option}" if index == position else f"   {option}", font = self.font, fill = 255)
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
				fps = round(np.mean(fps_array))
				var = round(np.var(fps_array))
				std_deviation  =round( np.std(fps_array))

			with Image.new("1",(self.device.width, self.device.height)) as img:
				draw = ImageDraw.Draw(img)
				draw.text((10,15), f"FPS: {fps}", font = self.font, fill = 255)
				draw.text((10,30), f"Variance: {var}", font = self.font, fill= 255)
				draw.text((10,45), f"Std Deviation: {std_deviation}", font = self.font, fill=255)
				self.device.display(img)

	def clear(self):
		self.device.clear()


	def display_fft(self, fft_queue):
		device = self.device
		while self.state == "fft":
			start_time = time.time()

			results_buffer = []
			while not fft_queue.empty():
				fft_data=fft_queue.get()
				results_buffer.append(fft_data)

			if results_buffer:
				fft_array = np.array(results_buffer)
				data = np.mean(fft_array, axis = 0)
				results_buffer = []

			max_magnitude = max(data)
			scaled_magnitude = (data/max_magnitude)*device.height
			scaled_magnitude = scaled_magnitude.astype(int)

			image = Image.new('1', (device.width, device.height),0)
			draw = ImageDraw.Draw(image)

			for x in range(min(device.width, len(data))):
				draw.line([(x,device.height), (x,device.height - scaled_magnitude[x])], fill = 255) 
			device.display(image)
			duration = time.time()-start_time
			#print(f"Display Loop time: {duration:.6f}seconds")


