# SPDX-FileCopyrightText: 2018 Kattni Rembor for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""CircuitPython - BME688 Sensor"""
import time
import board

import busio as io
#import adafruit_bme680
import adafruit_ssd1306
import neopixel
import supervisor

from digitalio import Direction, Pull   #MCP-related, may not be needed.
from adafruit_mcp230xx.mcp23017 import MCP23017


from microcontroller import watchdog as wdog
from watchdog import WatchDogMode


# Create sensor object, communicating over the board's default I2C bus
i2c = io.I2C(board.SCL, board.SDA)

### INIT - OLED
#oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)    #128 x 32 is 0x3C
oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3D)    #128 x 64 is 0x3D

### INIT - LED
led = neopixel.NeoPixel(board.NEOPIXEL, 1)  #control tied to pin8, object list.
led.brightness = 0.3    #global set
led[0] = (0,0,0)    #only 1 neopixel, index 0

### INIT - MCP GPIO XPDR
mcp = MCP23017(i2c, 0x20)   #I2C version
#mcp = MCP23s17(i2c, 0b000)   #SPI version - subaddress (0-8)
mcp_cs = [board.D5, board.D6, board.D9,board.D10]

### INIT - EEPROM
eeprom = adafruit_24lc32.EEPROM_I2C(i2c)

### init - IOs
btn = board.D12
led_ctrl = board.A3 #PWM capable
spi_cs4 = board.D11
mcp_rst = board.D4

#bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, debug=False)
#bme680.sea_level_pressure = 1012
#temperature_offset = -5

#wdog.mode = WatchDogMode.RESET
#wdog.timeout = 10
last_time = time.monotonic()
last_sensor_pull_time = time.monotonic()

#make sure its not accessed at the same time as serial read
sensor_data_buffer1 = []
sensor_data_buffer0 = []
serial_flag = 0
init_flag = 0


def i2c_scan(i2c, hex=1, timeout=3) -> tuple:
    start_time = time.monotonic()
    while not i2c.try_lock():
        if time.monotonic() - start_time > timeout:
            return [], f'try_lock timeout after {timeout}s'
        pass
    if hex:
        val = [hex(x) for x in i2c.scan()]
    else:
        val = i2c.scan()
    i2c.unlock()    #cleanup
    return val, 0

def i2c_read(i2c, address:hex, register:hex, byte_array_size:int -> bytearray):
    try:
        i2c.writeto(address, bytes([register])
        result = bytearray(byte_array_size)
        i2c.readfrom_into(address, result)
        return result  #returns a bytearray
    finally:
        i2c.unlock()

def update_LED(serial_data):
    rgbi = serial_data.rstrip().split(',')
    led[0] = (int(rgbi[1]), int(rgbi[2]), int(rgbi[3]))
    led.brightness = float(rgbi[4])
    print(f"Updated LED - serial_data: {rgbi}")

def i2c_oled_parse_serial(serial_data) -> list:
    msg = serial_data.rstrip().split(',') #expect split here
    return msg

def i2c_oled_write(msg:list):
    #generic function that accepts a list and writes
    try:
        if len(msg) > 6:
            print(f'ALERT! msg rows: {len(msg)} > 6, will likely run offscreen!')
        oled.fill(0)    #wipe screen
        y_pos = 0
        for i in msg:
            oled.text(f'{msg[i]}', 0, y_pos, 1) #msg, x_pos, y_pos, white
            y_pos += 10 #move 10 pixels down
        oled.show()
        return 0
    except Exception as e:
        return e

def i2c_oled_progress():
    return

def serial_translate(serial_data:str -> list):
    msg = serial_data.rstrip().split(',') #expect split here
    return msg  #list

def spi_mcp_scan(mcp):
    #returns a list of cs: <cs>_<addr> - ex 0_001 [device on CS0, 001-subaddress]
    return mcps #[<mcp_obj_1>, <mcp_obj_2>, ..n]

def spi_mcp_configure(mcp):
    return

#######
def i2c_oled_display(serial_data):
    msg = serial_data.rstrip().split(',') #expect split here
    oled.fill(0)
    oled.text(f'{msg[1]}', 0, 0, 1)
    oled.text(f'{msg[2]}', 0, 10, 1)
    oled.text(f'{msg[3]}', 0, 20, 1)
    oled.show()

def get_sensor_data():
    #405 SPS alone, 175 SPS w/ all enabled`
    temperature = bme680.temperature + temperature_offset
    humidity = bme680.relative_humidity
    pressure = bme680.pressure
    altitude = bme680.altitude
    gas = bme680.gas
    return [temperature,humidity,pressure,altitude,gas]

def update_OLED_sensor_data():
    msg = get_sensor_data()
    oled.fill(0)
    oled.text(f'T:{msg[0]:.2f} C  A:{msg[3]:.2f} ft', 0, 0, 1)
    oled.text(f'H:{msg[1]:.2f} %  G:{msg[4]} R', 0, 10, 1)
    oled.text(f'P:{msg[2]:.1f} hPa    ', 0, 20, 1)
    oled.show()

sensor_data_buffer0 = get_sensor_data()
sensor_data_buffer1 = get_sensor_data()

while True:
    if supervisor.runtime.serial_bytes_available:
        inText = input().strip()
        if inText == "":
            continue
        elif inText.lower().startswith("self-check"): #used for self-check
            print('True')
        elif inText.lower().startswith("calib"): #update calibration
            msg = inText.rstrip().split(',')
            temperature_offset = int(msg[1])
            bme680.sea_level_pressure = int(msg[2])
            print(f'Calibration updated - temp_offset: {msg[1]} C, sea level pressure: {msg[2]} hPa.')
        elif inText.lower().startswith("led"):
            update_LED(inText)
        elif inText.lower().startswith("sensor"):
            #sensor_data = get_sensor_data()
            if serial_flag == 1:
                sensor_data = sensor_data_buffer1
                print(f'{sensor_data[0]},{sensor_data[1]},{sensor_data[2]},{sensor_data[3]},{sensor_data[4]},C,%,hPa,ft,ohm')

                serial_flag = 0
            else:
                sensor_data = sensor_data_buffer0
                print(f'{sensor_data[0]},{sensor_data[1]},{sensor_data[2]},{sensor_data[3]},{sensor_data[4]},C,%,hPa,ft,ohm')

                serial_flag = 1
            #print(f'{sensor_data[0]},{sensor_data[1]},{sensor_data[2]},{sensor_data[3]},{sensor_data[4]},C,%,hPa,ft,ohm')
            #print(f"{temperature:.3f} C, {humidity:.3f} %,{pressure:.3f} hPa,{altitude:.3f} ft, {gas} ohm")
        elif inText.lower().startswith("@5"):
            temperature = bme680.temperature + temperature_offset
            oled.fill(0)
            oled.text(f'Temp: {temperature:.3f}', 0, 0, 1)
            oled.show()
            led[0] = (127, 127, 255)
            print('Updated OLED')
        elif inText.lower().startswith("oled"):
            update_OLED(inText)
        elif inText.lower().startswith("green"):
            led[0] = (0, 255, 0)
        else: #Unknown Command
            led[0] = (255,0,255)
            print('ERROR - Unknown command sent - Setting Error LED')
    #else: #default send environmental data
    if time.monotonic() - last_time >= 0.5:
        #print(f'Temp: {bme680.temperature + temperature_offset}')
        last_time = time.monotonic()
        #wdog.feed() #feed watchdog
        update_OLED_sensor_data()
    #demo
    if time.monotonic() - last_sensor_pull_time > 3:    #every 3 seconds update what is in buffer
        if serial_flag == 1:
            serial_flag = 0
            sensor_data_buffer0 = get_sensor_data()
        elif serial_flag == 0:
            sensor_data_buffer1 = get_sensor_data()
            serial_flag = 1
        #print(f'Sensor_data: Buf1: {sensor_data_buffer1} & Buf0: {sensor_data_buffer0}')
        last_sensor_pull_time = time.monotonic()
