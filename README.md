# Moths Lighting 

[Design doc](https://docs.google.com/document/d/1ZXtoYHQaDJpjE4DkzkGr9mxVCUkp4e3uGdJgVvmxdGU/edit?tab=t.0#heading=h.3579bywh7hd1)

## Physical Setup & OS
Main controller 
- Raspberry Pi 5 8gb (with active cooling)
- Debian 12 (bookworm)
- Adafruit - Mini USB Microphone
- OLED 2.42" SSD1309 White on Black - I2C	
- Cheap Rotary Encoder Module

Recievers: 
- Basic ESP modules controlling LEDs, physical setup is up to you. Remember to change the number of LEDs in the Bar config
- Running LED with option to receive ARTNET

## Setup
**Disclaimer: I have not done a fresh install and tried to get this working, there will be bugs/steps I have left out/ different steps for different hardware configurations. This is a very custom solution.**
- Wire up your Pi according to the info in the build document (link at top of page)
- Clone this repo
- Use a virtual environment and install libraries from requirements.txt
- run main.py

## Description of contents

**Disclaimer: In the process of adding type systems and unittests.** 
**Disclaimer: very repetitive code, especially in the display file, I know it sucks and will change soon haha**

**main.py:** The entry point for the application, coordinating the initialization and running of different modules.\
**artnet.py:** Manages Art-Net communication for sending lighting data to network-connected fixtures. \
**artnet_manager.py:** Handles the interface between Stupid_artnet Library and artnet.py. (packages data into correct format) \
**audio.py:** Handles audio input and processing, performing tasks like FFT analysis to drive lighting effects. \
**bar.py:** Represents lighting bars, managing their state and visual output based on processed audio data. \
**colour_manager.py:** Handles the user's colour configuration, adding, deleting, editing colours as well as generating and moving through colour palettes. \
**mode_manager.py:** Handles the current mode, and mode menus/selection. \
**display.py:** Controls the visual output on connected displays, showing the current lighting patterns and effects. \
**encoder.py:** Integrates with hardware encoders to allow manual adjustment of lighting settings. \
