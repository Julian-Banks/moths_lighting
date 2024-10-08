from gpiozero import Button
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device

Device.pin_factory = LGPIOFactory(chip=4)

class Encoder:
    def __init__(self, pin_A, pin_B, pin_button, callback, button_callback):
    
        self.callback = callback
        self.button_callback = button_callback
        self.position = 0

        self.rotary_A = Button(pin_A, pull_up=True)
        self.rotary_B = Button(pin_B, pull_up=True)

        self.button = Button(pin_button, bounce_time=0.2, pull_up=True)

        self.rotary_A.when_pressed = self._rotary_callback
        self.button.when_pressed = self._button_callback

    def _rotary_callback(self):
        if self.rotary_A.is_pressed != self.rotary_B.is_pressed:
            self.position -= 1
        else:
            self.position += 1
        self.callback(self.position)

    def _button_callback(self):
        self.button_callback()

    def cleanup(self):
        pass  # Add cleanup code if necessary


