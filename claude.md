# Moths Lighting Project

## Overview
A Raspberry Pi-based audio-reactive lighting controller that manages LED strips via Art-Net protocol. Features a rotary encoder with push button and OLED display for menu-based configuration.

## Architecture

### Core Components
- **main.py** - Entry point, thread coordination, encoder callbacks
- **encoder.py** - GPIO-based rotary encoder with button (pins: A=22, B=27, button=17)
- **display.py** - OLED display (SSD1306 via I2C), menu system, MenuManager
- **artnet.py** - ArtnetController managing multiple ESP devices
- **bar.py** - Individual LED bar logic and rendering
- **colour_manager.py** - Color palette management per controller
- **mode_manager.py** - Lighting mode management
- **audio.py** - FFT audio processing

### Threading Model
```
Main Thread
├── audio_thread (FFT processing)
├── artnet_thread (LED data @ configured FPS)
└── display.update_display() (OLED rendering @ ~10 FPS)

Encoder hardware interrupts → callbacks → Display methods (with lock)
```

### Menu System State Machine
```
MenuManager states:
- adjusting=False: Encoder rotation navigates menu items
- adjusting=True: Encoder rotation adjusts selected AdjustableMenuItem value

Button press:
- If adjusting=True → exit edit mode (adjusting=False)
- If adjusting=False → enter edit mode for AdjustableMenuItem OR navigate submenu
```

### MenuItem Types
- **MenuItem** - Basic navigation item with optional action/submenu
- **AdjustableMenuItem** - Has get/set functions, min/max/step, optional checkbox flag
- **AdjustableOptionItem** - Picklist-style selection (partially implemented)
- **DynamicMenuItem** - Regenerates submenu dynamically via submenu_func()

### Configuration Files (config/)
- **esp_config.yaml** - ESP IP addresses, FPS, num_bars, edit_config flags
- **bar_config.yaml** - Per-controller bar settings (brightness, fade, thresholds)
- **colour_config.yaml** - Per-controller color palettes
- **mode_config.yaml** - Per-controller mode configurations

## Key Code Locations

### Encoder Handling
- `encoder.py:7-35` - Encoder class with A/B pins and button
- `encoder.py:17` - Button with 0.2s bounce_time
- `encoder.py:22-27` - Rotation callback logic

### Menu State Management
- `display.py:54-149` - MenuManager class
- `display.py:64-106` - on_position_change (navigation vs adjustment)
- `display.py:107-143` - on_button_push (enter/exit edit mode)

### Display Rendering
- `display.py:605-648` - draw_current_menu()
- `display.py:615` - Checkbox items skip "adjusting" UI display

### Value Wrapping (AdjustableMenuItem)
- `display.py:72-77` and `84-89` - Values wrap from max→min and min→max

## Known Design Notes
- Lock (`self.lock`) protects menu state from concurrent access
- Dynamic menus regenerate on each draw cycle (but NOT while adjusting values)
- Checkbox AdjustableMenuItems don't show special "Adjusting" screen

## Recent Fixes (Jan 2026)

### Save-on-exit instead of save-on-every-rotation
**Problem:** File I/O on every encoder rotation while adjusting values caused:
- Lock contention (display.lock held during slow YAML writes)
- Queued rotation callbacks flooding in
- Button callbacks getting starved
- Values "cycling through" uncontrollably

**Fix:**
- Added `set_parameter_no_save()` in artnet.py for live adjustments
- Added `save_bar_config()` to save when done
- All setter functions in display.py now use `set_parameter_no_save()`
- Config is saved once when exiting adjust mode (button press)
- Dynamic menu regeneration disabled while in adjust mode
