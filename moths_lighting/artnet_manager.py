from stupidArtnet import StupidArtnet

class ArtnetManager:
    def __init__(self,target_ip = '255.255.255.255',packet_size = 512,fps = 30):
        
        self.packet_size = packet_size
        self.num_leds = self.packet_size // 3
        self.target_ip = target_ip
        self.fps = fps
        
        self.artnet_instances = []
        
        self.pixels_per_universe = 512
        
        self.num_universes = self.packet_size // self.pixels_per_universe + 1
        
        if self.packet_size == 0:
            print('Packet size must be greater than 0')
        else:
            for universe in range(self.num_universes):
                packet_size = self.pixels_per_universe if universe < self.num_universes - 1 else self.packet_size % self.pixels_per_universe
                self.artnet_instances.append(StupidArtnet(self.target_ip, universe, packet_size ,self.fps,True, True))
        
    def send(self, data):
        if self.packet_size == 0:
            #print('Packet size must be greater than 0')
            return
        
        for universe, artnet_instance in enumerate(self.artnet_instances):
            #start = universe * self.pixels_per_universe   if universe == 0 else universe * self.pixels_per_universe + 1
            
            if universe == 0:
                start = 0
                end = (universe + 1) * self.pixels_per_universe
            elif universe < self.num_universes - 1:
                start = universe * self.pixels_per_universe + 1
                end = (universe + 1) * self.pixels_per_universe +1
            else:
                start = universe * self.pixels_per_universe + 1
                end = len(data)
            
            #end = (universe + 1) * self.pixels_per_universe if universe < self.num_universes - 1 else len(data)
            
            print(f'Sending {end-start} pixels to universe {universe}, size is supposed to be {artnet_instance.packet_size}')
            artnet_instance.send(data[start:end])
            