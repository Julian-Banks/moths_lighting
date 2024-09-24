
import yaml

class Colour:
    def __init__(self, red, green, blue):
        self.red = red
        self.green = green
        self.blue = blue

        
#A class that stores a list of colours and has functions to remove, add, get and set them.
class ColourManager:
    def __init__(self, colours):
        self.colours = []
        for colour in colours:
            red, green, blue = colour
            self.colours.append(Colour(red, green, blue))
        
        
    def add_colour(self, colour):
        print('in add colour')
        print(f"len: {len(self.colours)}")
        self.colours.append(colour)
        
    def remove_colour(self, idx):
        print('in remove colour')
        print(f"idx: {idx}, len: {len(self.colours)}")
        if 0 <= idx < len(self.colours):
            self.colours.pop(idx)
            
    def update_colour(self, index, colour):
        print('in update colour')
        print(f"index: {index}, len: {len(self.colours)}")
        self.colours[index] = colour
            
    def get_colour_list(self):
        return self.colours
    
    def update_yaml(self):
        with open('/moths_lighting/config/lighting_config.yaml', 'w') as file:
            yaml.dump(self.colours, file)
        
        
    
        
        
    
        