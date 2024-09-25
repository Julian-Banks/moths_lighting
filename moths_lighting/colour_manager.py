
import yaml
import os

class Colour:
    def __init__(self, red, green, blue):
        self.red = red
        self.green = green
        self.blue = blue

        
#A class that stores a list of colours and has functions to remove, add, get and set them.
class ColourManager:
    def __init__(self, colours):
        config = self.get_config()
        print(f"in colour manager: {config}")
        self.colours = []
        self.target_file = 'moths_lighting/config/colour_config.yaml'
        
        for colour in config:
            print(f"colour: {colour}")
            red, green, blue = colour
            self.colours.append(Colour(red, green, blue))
            
            
    def get_config(self):
        with open('moths_lighting/config/colour_config.yaml', 'r') as file:
            return yaml.safe_load(file)
        
        
    def add_colour(self, colour):
        print('in add colour')
        print(f"len: {len(self.colours)}")
        self.colours.append(colour)
        self.update_config()
        
    def remove_colour(self, idx):
        print('in remove colour')
        print(f"idx: {idx}, len: {len(self.colours)}")
        if 0 <= idx < len(self.colours):
            self.colours.pop(idx)
            self.update_config()
            
    def update_colour(self, index, colour):
        print('in update colour')
        print(f"index: {index}, len: {len(self.colours)}")
        self.colours[index] = colour
        self.update_config()
            
    def get_colour_list(self):
        return self.colours
    
    def dictify(self):
        colour_list = []
        for colour in self.colours:
            colour_list.append([colour.red, colour.green, colour.blue])
        return colour_list
    
    def update_config(self):

        # Get the current working directory
        target_file = 'moths_lighting/config/colour_config.yaml'
        to_print = self.dictify()
        current_directory = os.getcwd()
        print(f"Current working directory: {current_directory}")
        if os.path.exists(target_file):
            with open(target_file, 'w') as file:
                yaml.dump(to_print, file)
        else:
            print(f"File does not exist: {target_file}")
            print("creating file")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            with open(target_file, 'w') as file:
                yaml.dump(to_print, file)
        
        
    
        
        
    
        