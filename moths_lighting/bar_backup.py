#This class is used to create an object for an LED bar. It is used to control the LED bar.
#it should be used in conjunction with the artnet.py class to control the LED bar.
#the bar will calculate the values for all of the pixels in the LED bar and then send them to the artnet class to be sent to the LED bar.

import time
import numpy as np
import threading
import sys


class Bar:
    def __init__(self,num_leds = 96,
                 RGB_order = "RGB", 
                 brightness = 1.0,
                 fade = 0.9,
                 fft_queue = None,
                 fps = 45,
                 colours = [(255,0,0),(0,255,0),(0,0,255)],
                 steps_per_transition = 100
                ):
        self.lock = threading.Lock()
        self.thread = None
        self.num_leds = num_leds
        self.num_pixels = num_leds*3
        self.pixels = bytearray([0]*self.num_pixels)
        self.fps = fps
        self.RGB_order = RGB_order
        self.brightness = brightness
        self.fade = fade
        self.fft_queue = fft_queue
        self.colours = colours
        self.steps_per_transition = steps_per_transition
        self.all_colours = self.cycle_colours(colours=colours,steps_per_transition=steps_per_transition)
        self.state = 0

    #write a function to fill the bar a solid colour and slowly fade into different colours
    def interpolate_colour(self, colour1, colour2, steps):
        #this function will take two colours and return a list of colours that are interpolated between the two colours
        return [(1-t) * np.array(colour1) + t * np.array(colour2) for t in np.linspace(0,1,steps)] 


    def cycle_colours(self, colours, steps_per_transition):
        """Cycle through a list of RGB colors smoothly."""
        all_colors = []
        for i in range(len(colours)):
            color1 = colours[i]
            color2 = colours[(i + 1) % len(colours)]  # Wrap to the first color after the last
            all_colors.extend(self.interpolate_colour(color1, color2, steps_per_transition))
        return all_colors

    def stop_generator(self):
        #change the state to 1 to stop the generator function
        #wait for the thread to finish
        self.thread.join()

    def start_generator(self):
        #set the stat to 0 so it will run
        self.state = 0
        #start a thread that will run the generator function
        self.thread = threading.Thread(target=self.generator)
        self.thread.start()

    #Write a function that sets self.pixels to a solid colour and steps through self.all_colours at self.fps frames per second
    def generator(self):

        #start a loop that will run until the state is changed from 0
        while self.state == 0:
            #Grab a colour from the list of colours, need to add some more checks in here otherwise it will only stop once the state is changed and it's finished it's full cycle through the colours 
            for colour in self.all_colours:
                start_time = time.time()
                if self.state == 0:
                    with self.lock:
                        #THis is not working correctly
                        self.pixels = bytearray([int(self.brightness * x) for x in colour for _ in range(self.num_leds)])
                        print(len(self.pixels))
                else:
                    sys.exit()
                #calculate elapsed time
                elapsed_time = time.time() - start_time
            	#calculate the time to sleep
                sleep_time = max(1/self.fps - elapsed_time,0)
            	#sleep to get accurate fps
                time.sleep(sleep_time)
        while self.state == 1:
            #Code for another lighting function here. 
            #Basic strobe that slowly cycles through all of the colours and turns all pixels on if bass frequencys are picked up above a certain level. 
            time.sleep(1) #this is just a placeholder for now.
            
        if self.state == "off":
            self.pixels = bytearray([0]*self.num_pixels)
            self.stop_generator()
            
    #function to allow the Artnet class access to the pixels.
    def get_pixels(self):
        with self.lock:
            return self.pixels
