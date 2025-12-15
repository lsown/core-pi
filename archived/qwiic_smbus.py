# class HandlerComms:
#     """Raspberry-Pi based comms to i2c QWIIC chip"""
#     def __init__(self, index:int=1):
#         self.state = {
#             'bus' : False
#         }
#         self.bus = self._create_bus(index=index)
#         self.address_eeprom = self.find_device(0x50, 0x57)
        
#     def _create_bus(self, index:int=1) -> object:
#         """"""
#         self.state['bus'] = False   #default not init - if we run this fxn, assume False, then adjust
#         try:
#             self.bus = smbus.SMBus(1)
#             self.state['bus'] = True    #if we are able to init
#         except FileNotFoundError as e:
#             logging.exception(f'Check bus index - {index} not found! {e} - {e.args}')
#         except Exception as e:
#             logging.exception(f'Failed to init i2c bus - {e} - {e.args}')
#         return self.bus

#     def find_device(self, min:int=0x50, max:int=0x57):
#         """Min/Max range of i2c_scan to find device"""
#             for address in range(min, max+1):
    
#     def scan_i2c(self, bus:object=None) -> list:
#         """Loops through 7-bit address on bus and returns found device addresses
#         Args: object - bus (smbus instance)
#         Return: list of int addresses"""
#         bus = self.bus if bus == None else bus  #default to use self.bus
#         devices = list()
#         try:
#             with bus as bus:
#                 for address in range(0, 128):
#                     bus.read_byte_data(address, 0x00)
#                     devices.append(address)
#         except OSError: #read_byte_data will fail if no address at that byte
#             logging.debug(f'No device found at {address}') 
#         return devices

#     def connect_ucon(self):
#         return

# class HandlerDevice:
#     def __init__(self):
#         self.cmd_to_translation:dict = {
#             #24LC32 EEPROM Memory IC 32Kbit I2C 400 kHz 900 ns 8-SOIC
#             #https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA32A-24LC32A-32-Kbit-I2C-Serial-EEPROM-DS20001713.pdf
#             #<control_byte><R/W> [0b1010xxx] = 0x50 - 0x57
#             #address HI [0b----XXXX XXXXXXXX]
#             #page size: 32 bytes - page address start is (integer multiples of buffer size), end is (page size - 1)
#             #endurance is specified in page sizes (each page is refreshed)
#         }
#         self.address = 0x50 #0b1010000
#         return
    
#     def read(self):
#         return
    
#     def write(self):
#         return
    
#     def write_page(self):
#         return