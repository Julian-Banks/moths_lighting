from stupidArtnet import StupidArtnet

class ArtnetManager:
    def __init__(self,target_ip = '255.255.255.255',packet_size = 512,fps = 30,edit_config = False):
        
        ###Artnet settings
        self.packet_size = packet_size
        self.num_leds = self.packet_size // 3
        self.target_ip = target_ip
        self.fps = fps
        self.num_leds_per_universe = 170
        self.artnet_instances = []
        self.pixels_per_universe = 512
        self.num_universes = self.packet_size // self.pixels_per_universe + 1
        
        ### Setting for Physical Controller
        self.edit_config = edit_config
        
        
        if self.packet_size != 0:
            for universe in range(self.num_universes):
                packet_size = self.pixels_per_universe if universe < self.num_universes - 1 else self.packet_size % self.pixels_per_universe + universe*2
                self.artnet_instances.append(StupidArtnet(self.target_ip, universe, packet_size ,self.fps,True, True))
        
    def send(self, data):
        if self.packet_size == 0: #don't send anything if packet size is 0
            #print('Packet size must be greater than 0') 
            return
        
        for universe, artnet_instance in enumerate(self.artnet_instances):            
            if universe == 0:
                start = 0
                if self.packet_size>self.pixels_per_universe:
                    end = (universe + 1) * self.pixels_per_universe
                else:
                    end = len(data)
            elif universe < self.num_universes-1:
                start = universe * self.pixels_per_universe - universe*2 # eg. start = 1 * 512 - 1*2 = 510 (This is because 510//3 = 170 which is the number of complete RGB values per universe. ) 
                end = (universe + 1) * self.pixels_per_universe - universe*2
            else:
                start = universe * self.pixels_per_universe - universe*2
                end = len(data) 
            
            #print('Uni',universe,'start:',start,'end:',end)
            #print(f'Sending {end-start} pixels to universe {universe}, size is supposed to be {artnet_instance.packet_size}')
            artnet_instance.send(data[start:end]) 
            
            #Man I worked this out but i have forgotten my logic and need to understand it better. 
            # Okay so there definitely is a bug, the pixels overlap between universes. I think an easy fix may just be to set the number of pixels per universe to 510 instead of 512. Not gonna mess with it now cause I have other more important things to try. 
            
            #Eg.
            #Data len is 1332. 
            #Uni 0, start: 0, end: 512
            #Uni 1, start: 510, end: 1022
            #Uni2, start: 1020, end: 1332
            #print(f'start: {start}, end: {end}')
            
            #LED 170,           LED 171,        LED 172
            #508, 509, 510,     511, 512, 513,  514, 515, 516
            #                             511,  512, 513
            