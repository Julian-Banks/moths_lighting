import threading
import time
import numpy as np

from colour_manager import Colour
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont

class MenuItem:
    def __init__(self, name, action=None, submenu=None, option1 =None, option2 = None):
        self.name = name
        self.option1 = option1
        self.option2 = option2  
        self.action = action  # Function to call when selected
        self.submenu = submenu  # Submenu if any

class AdjustableMenuItem(MenuItem): 
    def __init__(self, name, get_value_func, set_value_func, min_value=0, max_value=1, step=1, option1 = None, checkbox = False):
        super().__init__(name = name ,option1 = option1)
        self.get_value = get_value_func
        self.set_value = set_value_func
        self.min_value = min_value
        self.max_value = max_value
        self.step = step
        self.checkbox = checkbox #this is pretty shitty, but i'm putting it here so I can remember to add a cooler & better checkbox functionality
        
 
        
class AdjustableOptionItem(MenuItem): # Should look into this more. Understand how to use different super and sub classes. idea to solve some yucky UI vibes. Create another AdjustableOptionItems(MenuItem) which allows you cycle through a 'picklist' rather than numbers.
    def __init__(self, name, get_value_func, set_value_func, values):
        super().__init__(name)
        self.get_value = get_value_func
        self.set_value = set_value_func
        self.min_value = 0
        self.max_value = len(values) #the idea behind this is still integrate with existing adjustable item logic.
        self.values = values
        self.step = 1
        
class DynamicMenuItem(MenuItem):
    def __init__(self, name, submenu_func):
        super().__init__(name)
        self.name = name
        self.submenu_func = submenu_func

class Menu:
    def __init__(self, name, items=[], regenerate_func = None,position = 0,scroll_offset = 0):
        self.name = name
        self.items = items  # List of MenuItems
        self.position = position  # Current selected item
        self.scroll_offset = scroll_offset # Index of the first visible item
        self.regenerate = regenerate_func

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
            if self.current_adjustable_item.option1 != None: 
                option1 = self.current_adjustable_item.option1
                # Adjust the value
                current_value = self.current_adjustable_item.get_value(option1)
                new_value = current_value + delta * self.current_adjustable_item.step
                #Code to wrap the value if it goes above or below the min and max values
                if new_value > self.current_adjustable_item.max_value:
                    new_value = self.current_adjustable_item.min_value
                elif new_value < self.current_adjustable_item.min_value:
                    new_value = self.current_adjustable_item.max_value
                #Code to clamp the value if it goes above or below the min and max values
                new_value = max(self.current_adjustable_item.min_value, min(self.current_adjustable_item.max_value, new_value))
                self.current_adjustable_item.set_value(new_value,option1)
            else: 
                # Adjust the value
                current_value = self.current_adjustable_item.get_value()
                new_value = current_value + delta * self.current_adjustable_item.step
                #Code to wrap the value if it goes above or below the min and max values
                if new_value > self.current_adjustable_item.max_value:
                    new_value = self.current_adjustable_item.min_value
                elif new_value < self.current_adjustable_item.min_value:
                    new_value = self.current_adjustable_item.max_value
                #Code to clamp the value if it goes above or below the min and max values
                new_value = max(self.current_adjustable_item.min_value, min(self.current_adjustable_item.max_value, new_value))
                self.current_adjustable_item.set_value(new_value)
            
        else:
            # Move the menu selection
            menu = self.current_menu
            menu.position = (menu.position + delta) % len(menu.items)
            # Update scroll_offset
            visible_items_count = 4  # Number of items that can be displayed at once
            if menu.position >= menu.scroll_offset + visible_items_count:
                menu.scroll_offset = menu.position - visible_items_count + 1
            elif menu.position < menu.scroll_offset:
                menu.scroll_offset = menu.position

            # Ensure scroll_offset stays within valid range
            max_scroll_offset = max(0, len(menu.items) - visible_items_count)
            menu.scroll_offset = max(0, min(menu.scroll_offset, max_scroll_offset))
            
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
            elif(isinstance(selected_item, DynamicMenuItem) and selected_item.name != "Back"):
                #generate submenu dynamically
                submenu = selected_item.submenu_func()
                self.menu_stack.append(submenu)
                
            elif selected_item.submenu:
                
                # Enter submenu
                self.menu_stack.append(selected_item.submenu)
                
            elif selected_item.name == "Back":
                # Go back to previous menu
                self.go_back()
                        
            #I want to call the submenu AND the action function if they exist
            if selected_item.action:
                option1 = selected_item.option1
                option2 = selected_item.option2
                
                if option2 is not None:
                    selected_item.action(option1, option2)
                elif option1 is not None:
                    selected_item.action(option1)
                else:
                    selected_item.action()
            

    def go_back(self):
        # Go back to previous menu
        if len(self.menu_stack) > 1:
            self.menu_stack.pop()


class Display:
    def __init__(self, audio_processor, artnet_controller,
                 artnet_fps_queue, fft_fps_queue, fft_queue):
        # Initialize display device
        self.device = ssd1306(i2c(port=1, address=0x3C), width=128, height=64)
        try:
            self.font = ImageFont.truetype("moths_lighting/Roboto-Light.ttf", 10)  # Change to the path of a TTF font file on your system
        except AttributeError as e:
            print(f"Error: {e}")
            self.font = ImageFont.load_default()

        # Initialize system components
        self.audio_processor = audio_processor
        self.artnet_controller = artnet_controller
        self.artnet_fps_queue = artnet_fps_queue
        self.fft_fps_queue = fft_fps_queue
        self.fft_queue = fft_queue  # FFT data queue

        # Initialize state variables
        self.last_position = 0
        
        # Initialize FPS tracking
        self.artnet_fps = 0
        self.fft_fps = 0
        
        #Colours
        self.red = 100
        self.green = 0
        self.blue = 100
        self.updated_colour_idx = 0
        
        
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
            return self.artnet_controller.get_parameter('brightness')
        def set_brightness(value):
            self.artnet_controller.set_parameter('brightness',value)
       
        #Fade options
        def get_fade():
            return self.artnet_controller.get_parameter('fade')
        def set_fade(value):
            self.artnet_controller.set_parameter('fade',value)
            
        def get_mid_debounce():
            return self.artnet_controller.get_parameter('mid_debounce')
        def set_mid_debounce(value):
            self.artnet_controller.set_parameter('mid_debounce',value)
            
        def get_bass_debounce():
            return self.artnet_controller.get_parameter('bass_debounce')
        def set_bass_debounce(value):
            self.artnet_controller.set_parameter('bass_debounce',value)
        
        
        #Time per mode  
        def get_time_per_mode():
            return self.artnet_controller.get_parameter('time_per_mode')
        def set_time_per_mode(value):
            self.artnet_controller.set_parameter('time_per_mode',value)
        
        #Need to add Colour Cycle Speed
        def get_time_per_colour():
            return self.artnet_controller.get_time_per_colour()
        def set_time_per_colour(value):
            self.artnet_controller.set_time_per_colour(value)
        
        #Need to add Colour Picker
        #here comes the cavalery. IDK how much longer this file can get...
        def set_current_colour(idx, colour):
            set_red(colour.red)
            set_green(colour.green)
            set_blue(colour.blue)
            self.updated_colour_idx = idx
            #print('setting current idx, colour')
        
        def set_red(value):
            self.red = value
            if self.artnet_controller.get_display_colour() == 1:
                colour = Colour(self.red, self.green, self.blue)
                self.artnet_controller.set_display_colour(value = 1, colour = colour)
        def get_red():
            return self.red
        
        def set_green(value):
            self.green = value
            if self.artnet_controller.get_display_colour() == 1:
                colour = Colour(self.red, self.green, self.blue)
                self.artnet_controller.set_display_colour(value = 1, colour = colour)
        def get_green():
            return self.green
        
        def set_blue(value):
            self.blue = value
            if self.artnet_controller.get_display_colour() == 1:
                colour = Colour(self.red, self.green, self.blue)
                self.artnet_controller.set_display_colour(value = 1, colour = colour)
        def get_blue():
            return self.blue
        
        
        def get_display_colour():
            return self.artnet_controller.get_display_colour()
        def set_display_colour(value):
            colour = Colour(self.red, self.green, self.blue)
            self.artnet_controller.set_display_colour(value = value, colour = colour)
        
        def add_colour():
            colour = Colour(self.red, self.green, self.blue)
            self.artnet_controller.add_colour(colour)
            self.artnet_controller.set_display_colour(value = 0, colour = colour)
            self.menu_manager.go_back()   
            
        def update_colour():
            colour = Colour(self.red, self.green, self.blue)
            idx = self.updated_colour_idx
            self.artnet_controller.update_colour(idx, colour) #Very similar name to update_colours()!!! THis updates the colour in the colour manager. 
            self.artnet_controller.set_display_colour(value = 0, colour = colour)
            self.menu_manager.go_back() 
            
        def remove_colour(idx):
            self.artnet_controller.remove_colour(idx)
            self.artnet_controller.set_display_colour(value = 0, colour = Colour(0,0,0))
            self.menu_manager.go_back()
        #Function for generating the colour list!  
        
            
        def edit_colour_list():
            items = [] 
            for idx, colour in enumerate(self.artnet_controller.get_colour_list()):
                colour_name = f"R:{colour.red} G:{colour.green} B:{colour.blue}"
                
                colour_submenu = Menu(colour_name, items=[
                    
                    AdjustableMenuItem("Red", get_red, set_red, min_value=0, max_value=255, step=5),
                    AdjustableMenuItem("Green", get_green, set_green, min_value=0, max_value=255, step=5),
                    AdjustableMenuItem("Blue", get_blue, set_blue, min_value=0, max_value=255, step=5),
                    AdjustableMenuItem("Display Colour", get_display_colour, set_display_colour, min_value=0, max_value=1, step=1),
                    MenuItem("Remove Colour", action= remove_colour, option1=idx),
                    MenuItem("Back & Save", action = update_colour)
                ])
                items.append(MenuItem(colour_name, action=set_current_colour, submenu = colour_submenu, option1 =idx,option2=  colour))
            items.append(MenuItem("Add Colour", submenu = add_colour_menu))
            items.append(MenuItem("Back"))
            return Menu("Colour List", items = items,regenerate_func=edit_colour_list,position = self.menu_manager.current_menu.position, scroll_offset=self.menu_manager.current_menu.scroll_offset)
        

        def select_mode():
            items = []
            current_mode = self.artnet_controller.get_current_mode()
            
            for idx, mode in enumerate(self.artnet_controller.get_all_modes()):
                if idx == current_mode:
                    items.append(MenuItem(f"{mode.name} - Selected"))
                else:
                    items.append(MenuItem(mode.name, action = self.artnet_controller.change_mode, option1 = idx))
            items.append(MenuItem("Back"))
            return Menu("Select Mode", items = items, regenerate_func=select_mode,position = self.menu_manager.current_menu.position,scroll_offset=self.menu_manager.current_menu.scroll_offset)
              
        def select_auto_cycle_modes():
            items = []
            for idx, mode in enumerate(self.artnet_controller.get_all_modes()):
                if mode.auto_cycle:
                    items.append(MenuItem(f"{mode.name} - In Cycle", action= self.artnet_controller.remove_auto_cycle_mode, option1 = idx))
                else:
                    items.append(MenuItem(mode.name, action= self.artnet_controller.add_auto_cycle_mode, option1 = idx))
            
            items.append(MenuItem("Back"))
            return Menu("Select Auto Cycle Modes", items = items, regenerate_func=select_auto_cycle_modes,position = self.menu_manager.current_menu.position,scroll_offset=self.menu_manager.current_menu.scroll_offset)
        
        
        def mode_menu():
            items = []
            items.append(AdjustableMenuItem("Auto Cycle", get_auto_cycle,set_auto_cycle, min_value=0, max_value=1, step=1))
            if get_auto_cycle():
                items.append(DynamicMenuItem("Config Auto Cycle Modes", submenu_func=select_auto_cycle_modes))
                items.append(AdjustableMenuItem("Time per mode", get_time_per_mode, set_time_per_mode, min_value=0, max_value=600, step=10))
            if not get_auto_cycle():
                items.append(DynamicMenuItem("Select Static Mode", submenu_func=select_mode))
            items.append(MenuItem("Back"))
            return Menu("Mode Menu", items = items, regenerate_func=mode_menu, position=self.menu_manager.current_menu.position, scroll_offset= self.menu_manager.current_menu.scroll_offset)

        #Could parameterise these functions to make them more general. (but its already a huge improvement and I need to go to bed)
        
        def get_auto_cycle():
            return self.artnet_controller.get_parameter('auto_cycle')
       
        def set_auto_cycle(value):
            self.artnet_controller.set_parameter('auto_cycle',value)
            #print(f'in display, setting auto cycle to {value}')
            
        #CONFIGURE AUDIO OPTIONS
        #Trigger Style
        def get_trigger_style():
            trigger_style = self.artnet_controller.get_parameter('trigger_style')
            if trigger_style == "max":
                return 0
            else:
                return 1               
        def set_trigger_style(value):
            if value == 0:
                self.artnet_controller.set_parameter('trigger_style',"max")
            elif value == 1:
                self.artnet_controller.set_parameter("trigger_style","mean")
        
        #Bass options
        def get_bass_lower_bound():
            return self.artnet_controller.get_parameter('bass_lower_bound')
        def set_bass_lower_bound(value):
            self.artnet_controller.set_parameter('bass_lower_bound',value)
            
        def get_bass_upper_bound():
            return self.artnet_controller.get_parameter('bass_upper_bound')
        def set_bass_upper_bound(value):
            self.artnet_controller.set_parameter('bass_upper_bound',value)
        
        def get_bass_threshold():
            return self.artnet_controller.get_parameter('bass_threshold')
        def set_bass_threshold(value):
            self.artnet_controller.set_parameter('bass_threshold',value)     
        
        #Mid options
        def get_mid_lower_bound():
            return self.artnet_controller.get_parameter('mid_lower_bound')
        def set_mid_lower_bound(value):
            self.artnet_controller.set_parameter('mid_lower_bound',value)

        def get_mid_upper_bound():
            return self.artnet_controller.get_parameter('mid_upper_bound')        
        def set_mid_upper_bound(value):
            self.artnet_controller.set_parameter('mid_upper_bound',value)
        
        def get_mid_threshold():
            return self.artnet_controller.get_parameter('mid_threshold')     
        def set_mid_threshold(value):
            self.artnet_controller.set_parameter('mid_threshold',value)

        #Audio Sensitivity
        def get_audio_sensitivity():
            return self.audio_processor.get_sensitivity()      
        def set_audio_sensitivity(value):
            self.audio_processor.set_sensitivity(value)
            
        #CONFIGURE CONTROLLERS
        #FPS
        def get_fps():
            return self.artnet_controller.esp_configs[0]['fps']
        def set_fps(value):
            for i,esp in enumerate(self.artnet_controller.esp_configs):
                self.artnet_controller.esp_configs[i]['fps'] = value
            self.artnet_controller.update_config()
            
        #Controller 1 (should update these to be cleaner...)
        def get_num_bars_1():
            return self.artnet_controller.esp_configs[0]['num_bars']
        def set_numbars_1(value):
            self.artnet_controller.esp_configs[0]['num_bars'] = value
            self.artnet_controller.update_config()
            #code to initalise the controller with new number of bars
        
        #Controller 2    
        def get_num_bars_2():
            return self.artnet_controller.esp_configs[1]['num_bars']
        def set_numbars_2(value):
            self.artnet_controller.esp_configs[1]['num_bars'] = value
            self.artnet_controller.update_config()
            #code to initalise the controller with new number of bars
        
        #Controller 3
        def get_num_bars_3():
            return self.artnet_controller.esp_configs[2]['num_bars']
        def set_numbars_3(value):
            self.artnet_controller.esp_configs[2]['num_bars'] = value
            self.artnet_controller.update_config()
            #code to initalise the controller with new number of bars
        
        #Controller 4
        def get_num_bars_4():
            return self.artnet_controller.esp_configs[3]['num_bars']
        def set_numbars_4(value):
            self.artnet_controller.esp_configs[3]['num_bars'] = value
            self.artnet_controller.update_config()
            #code to initalise the controller with new number of bars
        
        
        ##Controller Select
        def set_controller_select(value, controller_num):
            self.artnet_controller.set_edit_config( value, controller_num)
            
        def get_controller_select(controller_num):
            return self.artnet_controller.get_edit_config(controller_num)
        
        
        def set_colour_offset(value):
            self.artnet_controller.set_parameter('colour_offset',value)
            self.artnet_controller.update_bar_colours()
            
        def get_colour_offset():
            return self.artnet_controller.get_parameter('colour_offset')    
        
        
        
        # DEFINE ACTION FUNCTIONS (FOR ON PUSH)
        #Shows the fft_stats
        def show_fft_stats():
            self.show_fft_display()

        #CONFIGURE MENU STRUCTURE
        # Lighting Options Menu
        lighting_options_menu = Menu("Lighting Options", items=[
            AdjustableMenuItem("Brightness", get_brightness, set_brightness, min_value=0.1, max_value=1, step=0.1),
            AdjustableMenuItem("Fade", get_fade, set_fade, min_value=0.02, max_value=0.2, step=0.01),
            
            
          
            # Add other adjustable items...
            
            MenuItem("Back")
        ])

        add_colour_menu = Menu("Select Colour to Add", items=[
        AdjustableMenuItem("Red", get_red,set_red, min_value=0, max_value=255, step=5),
        AdjustableMenuItem("Green", get_green, set_green, min_value=0, max_value=255, step=5),
        AdjustableMenuItem("Blue", get_blue, set_blue, min_value=0, max_value=255, step=5),
        AdjustableMenuItem("Display Colour", get_display_colour, set_display_colour, min_value=0, max_value=1, step=1),
        MenuItem("Confirm Colour", action=add_colour),
        MenuItem("Back")
        ])
        
        colour_options_menu = Menu("Colour Options", items= [
            DynamicMenuItem("Edit Colours", submenu_func=edit_colour_list),
            AdjustableMenuItem("Time per colour", get_time_per_colour, set_time_per_colour, min_value = 5, max_value = 60, step = 5),
            AdjustableMenuItem("Colour Offset",get_colour_offset, set_colour_offset, min_value = 0, max_value = 1, step = 0.05),
            MenuItem("Back")
        ])
        
              
        # Audio Options Menu
        audio_options_menu = Menu("Audio Options", items=[
            AdjustableMenuItem("Sensitivity", get_audio_sensitivity, set_audio_sensitivity, min_value=0, max_value=1, step=0.1),
            AdjustableMenuItem("Triger Style", get_trigger_style, set_trigger_style, min_value=0, max_value=1, step=1),
            AdjustableMenuItem("Bass Trigger", get_bass_threshold,  set_bass_threshold, min_value=0, max_value=1, step=0.1),
            AdjustableMenuItem("Bass LB", get_bass_lower_bound, set_bass_lower_bound, min_value=0, max_value=get_bass_upper_bound(), step=10),
            AdjustableMenuItem("Bass UB", get_bass_upper_bound, set_bass_upper_bound, min_value=get_bass_lower_bound(), max_value=300, step=10),
            AdjustableMenuItem("Bass Debounce",get_bass_debounce, set_bass_debounce, min_value=0, max_value=0.5, step=0.05),
            AdjustableMenuItem("Mid Trigger", get_mid_threshold, set_mid_threshold, min_value=0, max_value=1, step=0.1),
            AdjustableMenuItem("Mid LB", get_mid_lower_bound, set_mid_lower_bound, min_value=200, max_value=5000, step=100),
            AdjustableMenuItem("Mid UB", get_mid_upper_bound, set_mid_upper_bound, min_value=200, max_value=5000, step=100),
            AdjustableMenuItem("Mid Debounce",get_mid_debounce, set_mid_debounce, min_value=0, max_value=0.5, step=0.05),
            
            # Add other adjustable items...
            MenuItem("Back")
        ])

        # Configure Controllers Menu
        configure_controllers_menu = Menu("Configure Controllers", items=[
            AdjustableMenuItem("FPS", get_fps, set_fps, min_value=20, max_value=60, step=1),
            AdjustableMenuItem("ESP One", get_num_bars_1, set_numbars_1, min_value=0, max_value=5, step=1),
            AdjustableMenuItem("ESP Two", get_num_bars_2, set_numbars_2, min_value=0, max_value=5, step=1),
            AdjustableMenuItem("ESP Three", get_num_bars_3, set_numbars_3, min_value=0, max_value=5, step=1),
            AdjustableMenuItem("ESP Four", get_num_bars_4, set_numbars_4, min_value=0, max_value=5, step=1),
            # Add adjustable items...
            MenuItem("Back")
        ])

        #Need to create a menu that allows you to choose which modes to cycle through. Maybe the timing setting can move down here. 

        # Options Menu
        options_menu = Menu("Options", items=[
            MenuItem("Lighting Options", submenu=lighting_options_menu),
            MenuItem("Colour Options", submenu = colour_options_menu),
            MenuItem("Audio Options", submenu=audio_options_menu),
            DynamicMenuItem("Mode Manager", submenu_func=mode_menu),
            MenuItem("Back")
        ])
        
        ''' 
        for idx, controller in range(get_controllers):
        if controller.bars > 0:
            AdjustableMenuItem("Edit Controller idx", get_controller_select,  set_controller_select, checkbox = True ,option1= idx),
        else: 
            set_controller_select(Fal)'''
        esp_select_menu = Menu("Controller Select", items = [
            MenuItem('Continue...', submenu = options_menu),
            AdjustableMenuItem("Edit Controller 1", get_controller_select,  set_controller_select, checkbox = True ,option1= 0),
            AdjustableMenuItem("Edit Controller 2", get_controller_select, set_controller_select,  checkbox = True,option1 = 1),
            AdjustableMenuItem("Edit Controller 3", get_controller_select, set_controller_select,  checkbox = True,option1 = 2),
            AdjustableMenuItem("Edit Controller 4", get_controller_select, set_controller_select, checkbox = True,option1 = 3),
            MenuItem("Back")
        ])
        
        # Main Menu
        main_menu = Menu("Main Screen", items=[
            #MenuItem("ArtNet FPS", action=lambda: print(f"ArtNet FPS: {self.artnet_fps}")),
            MenuItem("Bars Per Controller.", submenu=configure_controllers_menu),
            MenuItem("Edit Config", submenu=esp_select_menu),
            MenuItem("Show FFT Stats", action=show_fft_stats),
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
        
        if self.menu_manager.current_menu.regenerate is not None: 
                submenu = self.menu_manager.menu_stack[-1].regenerate()    #regenerate the menu
                self.menu_manager.menu_stack[-1] = submenu          #display it. 
                
        menu = self.menu_manager.current_menu
            
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            if self.menu_manager.adjusting and self.menu_manager.current_adjustable_item and not(self.menu_manager.current_adjustable_item.checkbox):
                # Adjusting screen 
                #should add a boolean display here as well. 
                item = self.menu_manager.current_adjustable_item
                draw.text((0, 0), f"Adjust {item.name}:", font=self.font, fill=255)
                value = item.get_value()
                if isinstance(value, float):
                    value_str = f"{round(value, 2)}"
                else:
                    value_str = f"{value}"
                draw.text((100, 0), value_str, font=self.font, fill=255)
                if self.menu_manager.current_menu.name == "Audio Options":
                    draw = self.draw_fft_display_inpicture(height=round(self.device.height/2), draw = draw,x = 0,y = round(self.device.height/2 ))
            else:
                # Header
                draw.text((0, 0), menu.name, font=self.font, fill=255)
                # Menu items
                visible_items_count = 5  # Number of items that can be displayed at once
                visible_items = menu.items[menu.scroll_offset:menu.scroll_offset + visible_items_count]
                for idx, item in enumerate(visible_items):
                    y = 16 + idx * 10
                    actual_idx = menu.scroll_offset + idx
                    prefix = "-> " if actual_idx == menu.position else "   "
                    if isinstance(item, AdjustableMenuItem):
                        value = item.get_value(item.option1) if item.option1 != None else item.get_value()
                        if isinstance(value, float):
                            value_str = f"{round(value, 2)}"
                        else:
                            value_str = f"{value}"
                    else:
                        value_str = ""
                    draw.text((0, y), f"{prefix}{item.name}", font=self.font, fill=255)
                    draw.text((100, y), f"{value_str}", font=self.font, fill=255)
            self.device.display(img)
    
    #FOR SHOWING THE FFT DISPLAY
    def draw_fft_display(self):
        
        with Image.new("1", (self.device.width, self.device.height)) as img:
            draw = ImageDraw.Draw(img)
            # Display FFT FPS
            draw.text((0,0),f"Scaler: {self.get_scaler()}",font=self.font, fill = 255)
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
        threshold_y = y + height - int(self.artnet_controller.get_parameter('bass_threshold')* height)
        start_pixel, end_pixel = self.calculate_line(data=data, lower_bound=self.artnet_controller.get_parameter('bass_lower_bound'), upper_bound=self.artnet_controller.get_parameter('bass_upper_bound'), width=width)
        draw.line([(start_pixel, threshold_y), (end_pixel, threshold_y)], fill=255)
        
        # Draw the mid threshold line across this frequency range
        threshold_y = y + height - int(self.artnet_controller.get_parameter('mid_threshold') * height)
        start_pixel, end_pixel = self.calculate_line(data=data, lower_bound=self.artnet_controller.get_parameter('mid_lower_bound'), upper_bound=self.artnet_controller.get_parameter('mid_upper_bound'), width=width)
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

    
            #Dynamic Scaler
    def get_scaler(self):
        return round(self.audio_processor.get_scaler(),2)
    #def set_scaler(value):
        #   self.audio_processor.set_scaler()
        
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
