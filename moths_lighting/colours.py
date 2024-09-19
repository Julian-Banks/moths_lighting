# Add this class inside your Display class
class Colour:
    def __init__(self, red, green, blue):
        self.red = red
        self.green = green
        self.blue = blue

        
#A class that stores a list of colours and has functions to remove, add, get and set them.
class Colour_Manager:
    def __init__(self):
        self.colours = [Colour(255, 0, 0), Colour(255,255,0),Colour(255, 0, 255), Colour(0, 0, 255)]
        
        
    def add_colour(self, colour):
        self.colours.append(colour)
        
    def remove_colour(self, idx):
        if 0 <= idx < len(self.colours):
            self.colours.pop(idx)
            
    def update_colour(self, index, colour):
        self.colours[index] = colour
            
    def get_colour_list(self):
        return self.colours
        
        
    
        
        
    
        