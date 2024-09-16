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
        try:
            self.font = ImageFont.truetype("Roboto-Light.ttf", 10)  # Change to the path of a TTF font file on your system
        except AttributeError as e:
            print(f"Error: {e}")
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
        
    #DEFINE ALL MENUS, SUBMENUS AND MENU ITEMS, AND THEIR GET and Set FUNCTIONS
    def create_menu_structure(self):
        
        #DEFINE FUNCTIONS TO GET AND SET CONFIGURATIONS
        #LIGHTING OPTIONS                
        #Brightness options
        def get_brightness():
            return self.artnet_controller.get_brightness()
        def set_brightness(value):
            self.artnet_controller.set_brightness(value)
       
        #Fade options
        def get_fade():
            return self.artnet_controller.get_fade()
        def set_fade(value):
            self.artnet_controller.set_fade(value)
        
        #Time per mode  
        def get_time_per_mode():
            return "X"      
        def set_time_per_mode(value):
            pass
        
        #Need to add Colour Cycle Speed
        
        #Need to add Colour Picker
        
        #CONFIGURE AUDIO OPTIONS
        #Trigger Style
        def get_trigger_style():
            trigger_style = self.artnet_controller.get_trigger_style()
            if trigger_style == "max":
                return 0
            else:
                return 1           
        def set_trigger_style(value):
            if value == 0:
                self.artnet_controller.set_trigger_style("max")
            elif value == 1:
                self.artnet_controller.set_trigger_style("mean")
        
        #Bass options
        def get_bass_lower_bound():
            return self.artnet_controller.get_bass_lower_bound()
        def set_bass_lower_bound(value):
            self.artnet_controller.set_bass_lower_bound(value)
            
        def get_bass_upper_bound():
            return self.artnet_controller.get_bass_upper_bound()
        def set_bass_upper_bound(value):
            self.artnet_controller.set_bass_upper_bound(value)
        
        def get_bass_threshold():
            return self.artnet_controller.get_bass_threshold()
        def set_bass_threshold(value):
            self.artnet_controller.set_bass_threshold(value)     
        
        #Mid options
        def set_mid_lower_bound(value):
            self.artnet_controller.set_mid_lower_bound(value)
        def get_mid_lower_bound():
            return self.artnet_controller.get_mid_lower_bound()
        
        def set_mid_upper_bound(value):
            self.artnet_controller.set_mid_upper_bound(value)
        def get_mid_upper_bound():
            return self.artnet_controller.get_mid_upper_bound()
            
        def get_mid_threshold():
            return self.artnet_controller.get_mid_threshold()     
        def set_mid_threshold(value):
            self.artnet_controller.set_mid_threshold(value)

        #Audio Sensitivity
        def get_audio_sensitivity():
            return self.audio_processor.get_sensitivity()      
        def set_audio_sensitivity(value):
            self.audio_processor.set_sensitivity(value)
            
        #CONFIGURE CONTROLLERS
        #Controller 1
        def get_num_bars_1():
            return self.esp_configs[0]['num_bars']
        def set_numbars_1(value):
            self.esp_configs[0]['num_bars'] = value
            #code to initalise the controller with new number of bars
        
        #Controller 2    
        def get_num_bars_2():
            return self.esp_configs[1]['num_bars']
        def set_numbars_2(value):
            self.esp_configs[1]['num_bars'] = value
            #code to initalise the controller with new number of bars
        
        #Controller 3
        def get_num_bars_3():
            return self.esp_configs[2]['num_bars']
        def set_numbars_3(value):
            self.esp_configs[2]['num_bars'] = value
            #code to initalise the controller with new number of bars
        
        #Controller 4
        def get_num_bars_4():
            return self.esp_configs[3]['num_bars']
        def set_numbars_4(value):
            self.esp_configs[3]['num_bars'] = value
            #code to initalise the controller with new number of bars
        
        # DEFINE ACTION FUNCTIONS (FOR ON PUSH)
        #Shows the fft_stats
        def show_fft_stats():
            self.show_fft_display()
        #Reinitialise the whole setup (should I do this each time a controller is changed or make it something that is done at the end?) 
        def reinitialise():
            pass
        
        #Add an action function for each mode to switch to that mode. 
        def set_static():
            self.artnet_controller.change_mode(0)          
        def set_wave():
            self.artnet_controller.change_mode(1)
        def set_pulse():
            self.artnet_controller.change_mode(2)
        def set_bass_strobe():
            self.artnet_controller.change_mode(3)
        def set_bass_mid_strobe():
            self.artnet_controller.change_mode(4)
    

        #CONFIGURE MENU STRUCTURE
        # Lighting Options Menu
        lighting_options_menu = Menu("Lighting Options", items=[
            AdjustableMenuItem("Brightness", get_brightness, set_brightness, min_value=0, max_value=1, step=0.1),
            AdjustableMenuItem("Fade", get_fade, set_fade, min_value=0, max_value=1, step=0.1),
            AdjustableMenuItem("Time per mode", get_time_per_mode, set_time_per_mode, min_value=0, max_value=100, step=1),
            # Add other adjustable items...
            MenuItem("Back")
        ])

        # Audio Options Menu
        audio_options_menu = Menu("Audio Options", items=[
            AdjustableMenuItem("Sensitivity", get_audio_sensitivity, set_audio_sensitivity, min_value=0, max_value=1, step=0.1),
            AdjustableMenuItem("Triger Style", get_trigger_style, set_trigger_style, min_value=0, max_value=1, step=1),
            AdjustableMenuItem("Bass Trigger", get_bass_threshold,  set_bass_threshold, min_value=0, max_value=1, step=0.1),
            AdjustableMenuItem("Bass LB", get_bass_lower_bound, set_bass_lower_bound, min_value=0, max_value=200, step=10),
            AdjustableMenuItem("Bass UB", get_bass_upper_bound, set_bass_upper_bound, min_value=0, max_value=200, step=10),
            AdjustableMenuItem("Mid Trigger", get_mid_threshold, set_mid_threshold, min_value=0, max_value=1, step=0.1),
            AdjustableMenuItem("Mid LB", get_mid_lower_bound, set_mid_lower_bound, min_value=200, max_value=5000, step=100),
            AdjustableMenuItem("Mid UB", get_mid_upper_bound, set_mid_upper_bound, min_value=200, max_value=5000, step=100),
            # Add other adjustable items...
            MenuItem("Back")
        ])

        # Configure Controllers Menu
        configure_controllers_menu = Menu("Configure Controllers", items=[
            AdjustableMenuItem("ESP One", get_num_bars_1, set_numbars_1, min_value=0, max_value=5, step=1),
            AdjustableMenuItem("ESP Two", get_num_bars_2, set_numbars_2, min_value=0, max_value=5, step=1),
            AdjustableMenuItem("ESP Three", get_num_bars_3, set_numbars_3, min_value=0, max_value=5, step=1),
            AdjustableMenuItem("ESP Four", get_num_bars_4, set_numbars_4, min_value=0, max_value=5, step=1),
            #Menuitem to reinitialise the whole setup 
            MenuItem("Reinitialise", reinitialise),
            # Add adjustable items...
            MenuItem("Back")
        ])
        
        #choose modes menu
        choose_modes_menu = Menu("Choose Modes", items=[
            MenuItem("Static", action = set_static),
            MenuItem("Wave", action = set_wave),
            MenuItem("Pulse", action = set_pulse),
            MenuItem("Bass Strobe", action =  set_bass_strobe),
            MenuItem("Bass & Mid Strobe", action = set_bass_mid_strobe),
            MenuItem("Back")
        ])
        
        #Need to create a menu that allows you to choose which modes to cycle through. Maybe the timing setting can move down here. 
        
        # Options Menu
        options_menu = Menu("Options", items=[
            MenuItem("Lighting Options", submenu=lighting_options_menu),
            MenuItem("Audio Options", submenu=audio_options_menu),
            MenuItem("Controller Config.", submenu=configure_controllers_menu),
            MenuItem("Choose Modes", submenu=choose_modes_menu),
            MenuItem("Show FFT Stats", action=show_fft_stats),
            MenuItem("Back")
        ])

        # Main Menu
        main_menu = Menu("Main Screen", items=[
            MenuItem("ArtNet FPS", action=lambda: print(f"ArtNet FPS: {self.artnet_fps}")),
            MenuItem("Options", submenu=options_menu),
            # Add other main menu items...
        ])

        return main_menu


    #HANDLE CALLBACKS FROM THE ENCODER  
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

    #THE DISPLAY THREAD, RUNS CONTINUALLY AND MONTIORS/UPDATES THE DISPLAY
    def update_display(self):
        while not self.stop_flag.is_set():
            with self.lock:
                # Update FPS values
                artnet_fps = self.get_fps(self.artnet_fps_queue)
                self.artnet_fps = artnet_fps if artnet_fps is not None else self.artnet_fps

                fft_fps = self.get_fps(self.fft_fps_queue)
                self.fft_fps = fft_fps if fft_fps is not None else self.fft_fps

                if self.showing_fft:
                    # Render FFT display
                    self.draw_fft_display()
                else:
                    # Render display based on current menu
                    self.draw_current_menu()

            time.sleep(0.1)

    #DRAW THE CURRENT MENU, HANDLES THE LOGIC OF WHAT TO DISPLAY
    def draw_current_menu(self):
        menu = self.menu_manager.current_menu
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            if self.menu_manager.adjusting and self.menu_manager.current_adjustable_item:
                # Adjusting screen
                item = self.menu_manager.current_adjustable_item
                draw.text((0, 0), f"Adjust {item.name}:", font=self.font, fill=255)
                value = item.get_value()
                if isinstance(value, float):
                    value_str = f"{round(value, 2)}"
                else:
                    value_str = f"{value}"
                draw.text((110, 0), value_str, font=self.font, fill=255)
                if self.menu_manager.current_menu.name == "Audio Options":
                    draw = self.draw_fft_display_inpicture(height=round(self.device.height/2), draw = draw,x = 0,y = round(self.device.height/2 ))
                    #if item.name == "Bass Trigger":
                    #    draw = self.draw_fft_display_inpicture(height=round(self.device.height/2), draw = draw,x = 0,y = round(self.device.height/2 ))
                    #if item.name == "Mid Trigger":
                    #    draw = self.draw_fft_display_inpicture(height=round(self.device.height/2), draw = draw,x = 0,y = round(self.device.height/2 ))
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
                            value_str = f"{round(value, 2)}"
                        else:
                            value_str = f"{value}"
                    else:
                        value_str = ""
                    draw.text((0, y), f"{prefix}{item.name}", font=self.font, fill=255)
                    draw.text((110, y), f"{value_str}", font=self.font, fill=255)
            self.device.display(img)
    
    #FOR SHOWING THE FFT DISPLAY
    def draw_fft_display(self):
        
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            # Display FFT FPS
            draw.text((60, 0), f"fft per sec: {self.fft_fps}", font=self.font, fill=255)
            draw = self.draw_fft_display_inpicture(draw=draw)
            self.device.display(img)
    
    #FOR SHOWING EMBEDDED FFT DISPLAYS.        
    def draw_fft_display_inpicture(self, height = None, width = None, draw = None , y = 0, x = 0):
        
        device = self.device
        
        if height is None:
            height = device.height
        if width is None:
            width = device.width
        
        data = self.get_audio_data()

        max_magnitude = max(data) if np.max(data) > 0 else 1
        max_freq = self.get_max_freq(data)
        
        scaled_magnitude = (data) * (height)
        scaled_magnitude = scaled_magnitude.astype(int)

        num_bars = min(width, len(scaled_magnitude))
        bar_width = max(1, width // num_bars)
        
        for i in range(num_bars):
            x_pos = x + i * bar_width
            y_top = y + height - scaled_magnitude[i]
            draw.rectangle([x_pos, y_top, x_pos + bar_width - 1, y + height], fill=255)
            
        # Draw the bass threshold line across this frequency range
        threshold_y = y + height - int(self.artnet_controller.get_bass_threshold()* height)
        start_pixel, end_pixel = self.calculate_line(data=data, lower_bound=self.artnet_controller.get_bass_lower_bound(), upper_bound=self.artnet_controller.get_bass_upper_bound(), width=width)
        draw.line([(start_pixel, threshold_y), (end_pixel, threshold_y)], fill=255)
        
        # Draw the mid threshold line across this frequency range
        threshold_y = y + height - int(self.artnet_controller.get_mid_threshold() * height)
        start_pixel, end_pixel = self.calculate_line(data=data, lower_bound=self.artnet_controller.get_mid_lower_bound(), upper_bound=self.artnet_controller.get_mid_upper_bound(), width=width)
        draw.line([(start_pixel, threshold_y), (end_pixel, threshold_y)], fill=255)

        draw.text((60, 10), f"max freq: {max_freq:.2f} Hz", font=self.font, fill=255)
        draw.text((60, 20), f"max mag: {max_magnitude:.2f}", font=self.font, fill=255)

        return draw

    #HELPER FUNCTION TO CALCULATE THE LINE TO DISPLAY THRESHOLDS        
    def calculate_line(self, data, lower_bound, upper_bound, width):
        # Determine frequency resolution and find indices for 0-200 Hz
        fft_length = len(data)
        frequency_resolution = 5000 / fft_length
        max_index = int(upper_bound / frequency_resolution)
        min_index = int(lower_bound / frequency_resolution)
        
        # Map to pixel coordinates  
        start_pixel = int(min_index / fft_length * width)
        end_pixel = int(max_index / fft_length * width)
        
        return start_pixel, end_pixel
    
    #GET THE AUDIO DATA FROM QUEUE
    def get_audio_data(self):
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
        return data

    #GET THE MAX FREQUENCY FROM THE DATA
    def get_max_freq(self, data):
        
        fft_length = len(data)
        frequency_resolution = 5000 / fft_length
        max_index = np.argmax(data)
        max_freq = max_index * frequency_resolution
        return max_freq
    #GET THE FPS FROM THE QUEUE
    def get_fps(self, fps_queue):
        fps = None
        while not fps_queue.empty():
            fps = fps_queue.get()
        return fps

    def show_fft_display(self):
        self.showing_fft = True

    def clear(self):
        self.device.clear()
