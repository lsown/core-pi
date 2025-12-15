#!/usr/bin/env python
"""handler_i2c.py: Wrapper for i2C from periphery."""

__author__ = "Lawrence Own"
__email__ = "aureias@gmail.com"

from periphery import I2C   #write_bytes direct - reference - #https://python-periphery.readthedocs.io/en/latest/i2c.html
from periphery.i2c import I2CError
import logging
logger = logging.getLogger(__name__)

class HandlerI2C:
    """Wrapper for I2C from periphery that adds some niceties like scan_device, try-excepts"""
    def __init__(self, index:int=1, init:bool=True):
        """Take args, try to instantiate a bus"""
        self.index:int = index
        self.exists:bool = False
        self.bus = self._create_bus(self.index)    #sets self.exists if instantiates
        self.device_addresses:list = self.scan_i2c(self.bus)

    def _create_bus(self, index:int=1) -> object:
        """Creates instance of I2C peripheral bus"""
        # note, possibly run an increment range search - i.e. go from 0 -> max_int to auto-search for avaiable buses
        index = self.index if index == None else index  #default use instantiated variant
        try:
            bus = I2C(f"/dev/i2c-{index}")
            self.index = index  #update to index usage
            self.exists = True  #if it passes bus arg
            self.bus = bus
            logger.info(f'Bus created: setting self.index to {self.index}, self.exists to: {self.exists}, self.bus to {self.bus}')
        except I2CError as e:
            logger.exception(f'Check i2cbus enabled & index - Typically 1 on RPi, arg was {index}: {e} - {e.args}')
            self.exists = False #re-set to default false until we instantiate
        return bus

    def scan_i2c(self, bus:object=None) -> list:
        """Loops through 7-bit address on bus and returns found device addresses
        Args: 
            1. object - bus (periphery i2c instance)
        Return: 
            list of device addresses"""
        bus:object = self.bus if bus == None else bus  #default to use self.bus
        device_addresses:list = list()
        i2c_errors:list = list()
        msgs = [I2C.Message([0x00]), I2C.Message([0x00], read=True)]
        with bus as bus:
            for address in range(0, 128):
                try:
                    bus.transfer(address, msgs)
                    device_addresses.append(address)
                except I2CError: #read_byte_data will fail if no address at that byte
                    i2c_errors.append(address)
        hex_addresses = [f'0x{n:02x}' for n in device_addresses]
        logger.info(f'device_addresses: {hex_addresses}')
        return device_addresses
    
if __name__ == "__main__":
    FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s] %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)

    handler_i2c = HandlerI2C(index=1)   #wrapper for periphery I2C bus... just adds some niceties / checks
    logger.info(f'Found device addresses: {handler_i2c.device_addresses}')
