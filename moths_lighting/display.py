from luma.core.interface.serial import i2c
from luma.oled.device import ssd1309
from PIL import Image, ImageDraw
import time
serial = i2c(port = 1, address = 0x3C)
device = ssd1309(serial, width=128, height = 64)

def update(data):
	try:
		while True:
			start_time = time.time()
			data = fft_queue.get()
			max_magnitude = max(data)
			scaled_magnitude = (data/max_magnitude)*device.height
			scaled_magnitude = scaled_magnitude.astype(int)

			image = Image.new('1', (device.width, device.height),0)
			draw = ImageDraw.Draw(image)

			for x in range(min(device.width, len(data))):
				draw.line([(x,device.height), (x,device.height - scaled_magnitude[x])], fill = 255) 

			device.display(image)
			duration = time.time()-start_time
			print(f"Display Loop time: {duration:.6f}seconds")
	except KeyboardInterrupt:
		print("display : Interrupted by user, stopping")

