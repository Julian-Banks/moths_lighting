from luma.core.interface.serial import i2c
from luma.oled.device import ssd1309
from PIL import Image, ImageDraw

serial = i2c(port = 1, address = 0x3C)
device = ssd1309(serial, width=128, height = 64)

def draw_response(data):
	max_magnitude = max(data)
	scaled_magnitude = (data/max_magnitude)*device.height
	scaled_magnitude = scaled_magnitude.astype(int)

	image = Image.new('1', (device.width, device.height),0)
	draw = ImageDraw.Draw(image)
	
	for x in range(min(device.width, len(data))):
		draw.line([(x,device.height), (x,device.height - scaled_magnitude[x])], fill = 255) 
	
	device.display(image)

