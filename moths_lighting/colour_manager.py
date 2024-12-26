
import yaml
import os

class Colour:
    def __init__(self, red, green, blue):
        self.red = red
        self.green = green
        self.blue = blue

        
#A class that stores a list of colours and has functions to remove, add, get and set them.
class ColourManager:
    def __init__(self,controller_idx):
        
        self.controller_idx = controller_idx
        config = self.get_config()
        #print(f"in colour manager: {config}")
        self.colours = []
        self.target_file = 'moths_lighting/config/colour_config.yaml'
        
        for colour in config:
            #print(f"colour: {colour}")
            try:
                red, green, blue = colour
                self.colours.append(Colour(red, green, blue))
            except Exception as e:
                print("the Error is: " ,e) 
                print(f"The colour is : {colour}")
                print(f"the full config is: {config}") 
            
            
    def get_config(self):
        with open('moths_lighting/config/colour_config.yaml', 'r') as file:
            data = yaml.safe_load(file)
        data = data[self.controller_idx]
        return data
        
        
    def add_colour(self, colour):
        #print('in add colour')
        #print(f"len: {len(self.colours)}")
        self.colours.append(colour)
        self.update_config()
        
    def remove_colour(self, idx):
        #print('in remove colour')
        #print(f"idx: {idx}, len: {len(self.colours)}")
        if 0 <= idx < len(self.colours):
            self.colours.pop(idx)
            self.update_config()
            
    def update_colour(self, index, colour):
        #print('in update colour')
        #print(f"index: {index}, len: {len(self.colours)}")
        self.colours[index] = colour
        #self.update_config()
            
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
        #print(f"Current working directory: {current_directory}")
        
        if os.path.exists(target_file):
            with open(target_file, 'r') as file:
                data = yaml.safe_load(file)
        else: 
            print(f"File does not exist: {target_file}")
            print("creating file")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            data = {}         
        
        
        print(f"Data as it comes out of the ymal file: {data}")
        print(f"Data[{self.controller_idx}]: {data[self.controller_idx]}")
        #update that specific controller's colour config
        data[self.controller_idx] = to_print
        print(f"Data after to_print has been added: {data}")
        #Print out to the file.
        with open(target_file, 'w') as file:    
            yaml.dump(data, file)
        print(f"Updated colour config {self.controller_idx}")

        
    
        
        
    
        