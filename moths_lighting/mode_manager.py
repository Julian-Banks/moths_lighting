import yaml
import os 

class mode:
    def __init__(self, name = None, audio_reactive = False, mode_func = None, auto_cycle = False):  
        self.name = name
        self.audio_reactive = audio_reactive
        self.auto_cycle = auto_cycle
        self.mode_func = mode_func

class ModeManager:
    def __init__(self, controller_idx):
        self.mode_config_file = 'moths_lighting/config/mode_config.yaml'
        self.modes = []
        self.modes_menu = []
        self.auto_cycle_modes = []
        self.controller_idx = controller_idx
        self.set_mode_config()
        self.generate_auto_cycle_modes()
        
    def add_mode(self,mode):
        self.modes.append(mode)
        self.modes_menu.append(mode.name)
        
    def generate_auto_cycle_modes(self):
        self.auto_cycle_modes = self.get_auto_cycle_modes()
        
    def remove_auto_cycle_mode(self,idx):
        if 0 <= idx < len(self.modes):
            if self.modes[idx].auto_cycle:
                self.modes[idx].auto_cycle = False
        self.generate_auto_cycle_modes()
                
    def add_auto_cycle_mode(self,idx):
        if 0 <= idx < len(self.modes):
            if not self.modes[idx].auto_cycle:
                self.modes[idx].auto_cycle = True
        self.generate_auto_cycle_modes()
            
    def get_all_modes(self):
        return self.modes
    
    def get_all_mode_menu(self):
        return self.modes_menu
    
    def get_auto_cycle_modes(self):
        return [mode for mode in self.modes if mode.auto_cycle]
    
    def get_auto_cycle_menu(self):
        return [mode.name for mode in self.modes if mode.auto_cycle]
    
    def dictify_modes(self):  #I think this can stay the same.
        return [{'name': mode.name, 'audio_reactive': mode.audio_reactive, 'auto_cycle': mode.auto_cycle} for mode in self.modes]
    
    def update_mode_config(self): 
        target_file = self.mode_config_file
        to_print = self.dictify_modes()
        current_directory = os.getcwd()
        print(f"Current working directory: {current_directory}")
        
        if os.path.exists(target_file):
            with open(target_file, 'r') as file:
                data = yaml.safe_load(file)
        else:
            print(f"File does not exist: {target_file}")
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            data = {}

        data[self.controller_idx] = to_print
        
        with open(target_file, 'w') as file:
            yaml.dump(data, file)
        print(f"Config created: {target_file}, Controller {self.controller_idx}")
            
            
    def set_mode_config(self): 
        with open(self.mode_config_file, 'r') as file:
            data = yaml.safe_load(file)
        data = data[self.controller_idx]   
        self.generate_mode_menu(data)
    
   
    def generate_mode_menu(self,data): 
        for config in data:
            name = config["name"]
            audio_reactive = config["audio_reactive"]
            auto_cycle = config["auto_cycle"]
            new_mode = mode(name = name, audio_reactive = audio_reactive, auto_cycle = auto_cycle)
            self.add_mode(new_mode)
        print(f'Modes added: {[mode.name for mode in self.modes]}')