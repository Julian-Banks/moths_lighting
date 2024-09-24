
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
        print(f"in colour manager: {colours}")
        self.colours = []
        for colour in colours:
            print(f"colour: {colour}")
            red, green, blue = colour
            self.colours.append(Colour(red, green, blue))
        
        
    def add_colour(self, colour):
        print('in add colour')
        print(f"len: {len(self.colours)}")
        self.colours.append(colour)
        self.update_yaml()
        
    def remove_colour(self, idx):
        print('in remove colour')
        print(f"idx: {idx}, len: {len(self.colours)}")
        if 0 <= idx < len(self.colours):
            self.colours.pop(idx)
            self.update_yaml()
            
    def update_colour(self, index, colour):
        print('in update colour')
        print(f"index: {index}, len: {len(self.colours)}")
        self.colours[index] = colour
        self.update_yaml()
            
    def get_colour_list(self):
        return self.colours
    
    def update_yaml(self):

        # Get the current working directory
        target_file = '/moths_lighting/config/lighting_config.yaml'
        current_directory = os.getcwd()
        print(f"Current working directory: {current_directory}")
        if os.path.exists(target_file):
            with open(target_file, 'w') as file:
                yaml.dump(self.colours, file)
        else:
            print(f"File does not exist: {target_file}")
            print("creating file")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            with open(target_file, 'w') as file:
                yaml.dump(self.colours, file)
        
        
    
        
        
    
        