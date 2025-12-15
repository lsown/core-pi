import logging
# import smbus2 as smbus    #Do not use, no native support of 16-bit registers
from periphery import I2C   #write_bytes direct - reference - #https://python-periphery.readthedocs.io/en/latest/i2c.html
from periphery.i2c import I2CError
import time

#https://forums.raspberrypi.com/viewtopic.php?t=157872

logger = logging.getLogger(__name__)

class HandlerBus:
    def __init__(self, index:int=1, init:bool=True):
        """Take args, try to instantiate a bus"""
        self.index:int = index
        self.exists:bool = False
        self.bus = self._create_bus(self.index)    #sets self.exists if instantiates
        self.device_addresses:list = self.scan_i2c(self.bus)

    def _create_bus(self, index:int=1) -> object:
        """Creates instance of I2C peripheral bus"""
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
        Args: object - bus (smbus instance)
        Return: list of device addresses"""
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

class EEPROM24LCxx:
    """
    24LC32 EEPROM Memory IC 32Kbit I2C 400 kHz 900 ns 8-SOIC
    https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA32A-24LC32A-32-Kbit-I2C-Serial-EEPROM-DS20001713.pdf
    <control_byte><R/W> [0b1010xxx] = 0x50 - 0x57
    address HI [0b----XXXX XXXXXXXX]
    page size: 32 bytes - page address start is (integer multiples of buffer size), end is (page size - 1)
    endurance is specified in page sizes (each page is refreshed)
    1st 4kB rated at 10 million, last 28kB rated at 100K
    """
    def __init__(self, i2c_bus:object, address:int=0x50, delay:float = 0.001, size:int=32768):
        self.bus = I2C("/dev/i2c-1")
        self.address:int = address  #0x50 - 0x57 expected
        self.delay:float = delay    #typical 4 byte translation is ~0.5 mS, theoretical 100kBits is 0.32 mS. To be safe probably do a 1 mS delay between r/w to account for dead time.
        self.size:int = size    #register size - depends on HW variant of 24LCxx (32kB, 64kB, etc. - 2**12, 2**13, etc.)
        self._max_reg:int = int(size / 8 - 1)    #32768 bits / 8 -> 4096 - 1 = 4095
        self.exists:bool = self._exists_on_bus(self.address)    #flag for whether device is found on the bus
        self.cmd_to_translation:dict = {

        }

    def _exists_on_bus(self, address:int, bus:object=None) -> bool:
        """Used on init, used to set flag for whether device exists"""
        bus == self.bus if bus == None else bus
        self.exists = False # reset to default False until we validate
        try:
            #logger.debug(self.bus)
            msgs = [I2C.Message([0x00]), I2C.Message([0x00], read=True)]
            self.read_byte(0x00, address)
            self.exists=True
        except Exception as e:
            logger.exception(f"Read error from address: 0x{address:02x} - {e} - {e.args}")
        return self.exists

    def read_byte(self, register:int, address:int = 0x50) -> tuple:
        """
        Args:
            register: int representing desired address
            address: i2c address (0 - 127)
        Returns:
            tuple: (<success>, <int response of requested register>)
        """
        valid = self._valid_reg_and_data(register, data=0)
        success=False
        if not valid[0]:    #check before we attempt to rw to device
            raise ValueError(valid[1])
        reg:list = self._split_reg(register)    #[0x01, 0x00]
        msgs:list = [I2C.Message(reg), I2C.Message([0x00], read=True)]
        logger.debug(f'got here in read: {msgs} - wanted reg is {reg}')
#msgs = [I2C.Message([0x00, 0x00]), I2C.Message([0x00], read=True)]
        try:
          start_time = time.time()
          self.bus.transfer(0x50, msgs)    #periphery.i2c.I2CError: [Errno 121] I2C transfer: Remote I/O error
          success = True
          end_time = time.time()
          logger.debug(f'self.bus.transfer time was {end_time - start_time}s')
        except I2CError as e:  #periphery.i2c.I2CError: [Errno 121] I2C transfer: Remote I/O error
          logger.exception(f'{e} - {e.args} - if Errno 121 - possible bus was busy from prior request, add a delay in request')
        resp:int = msgs[1].data[0]
        logger.debug(f"0x100: 0x{resp:02x}")
        return (success, resp) #int (0-255)

    def write_byte(self, register:int, data:int, address:int = None) -> tuple:
        """
        Args:
            register: int representing desired address
            data: int (byte)
            address: i2c address (0 - 127)
        Returns: tuple on format (<success>, <list of byte payload>)
        """
        address = self.address if address == None else address
        valid = self._valid_reg_and_data(register, data)
        if not valid[0]:    #check before we attempt to rw to device
            raise ValueError(valid[1])
        reg:list = self._split_reg(register)    #[0x01, 0x00]
        payload:list = reg + [data]   #[0x01, 0x00, 0x03]
        logger.debug(f'reg: {reg}, data: {data}, payload is: {payload}')
        msgs:list = [I2C.Message(payload)]
        try:
            start_time = time.time()
            self.bus.transfer(address, msgs)    #periphery.i2c.I2CError: [Errno 121] I2C transfer: Remote I/O error
            end_time = time.time()
            logger.debug(f'self.bus.transfer time was {end_time - start_time}s')
            success = True
        except I2CError as e:
            logger.exception(f'{e} - {e.args} - if Errno 121 - possible bus was busy from prior request, add a delay')
        return (success, payload)  #list

    def write_read_byte(self, register:int, data:int, address:int = None, delay:float = None) -> bool:
        """R/W convenience fxn, returns True if expected data written matches data read at register
        Args:
            register: 12-bit for register (0-4095)
            data: byte of data to load (0-8)
            address: (0x50 - 0x57)
            delay: Time between the write and read transaction - for 4 bytes, measured time is ~0.5 mS... so to be safe... do ~1 mS
        """
        data_written = False
        address = self.address if address == None else address
        delay = self.delay if delay == None else delay
        write_success, payload = self.write_byte(register, data, address)
        time.sleep(delay)	#typical transaction is ~0.5 mS for 1 byte read. force a delay!
        read_success, resp = self.read_byte(register, address)
        if write_success and read_success and data == resp:
            data_written = True
        else:
            logger.exception(f'Error - write_success: {write_success}, read_success: {read_success}, or data != resp {data} vs. {resp}')
        return data_written #bool

    def _split_reg(self, register:int) -> list:
        """Convenience - splits register value into separate lists"""
        byte1 = register >> 8 & 0xFF    #0x100 -> 0x1
        byte2 = register & 0xFF         #0x100 -> 0x00
        logger.debug(f'byte 1: {byte1}, byte 2: {byte2}')
        return [byte1, byte2]

    def _valid_reg_and_data(self, register:int, data:int) -> tuple:
        """Checks register and data for expected lengths, returns a tuple: (<valid>, <msg>)"""
        valid:bool = True
        msg:str = str()
        #if not self.exists: #check against if device was found at expected address
            #msg += f'Instantiation likely failed - self.exists = {self.exists}. Re-run fxn self._exists_on_bus to check & reset flag!'
            #valid = False
        if register > self._max_reg:    #check against input arg for register vs. max register avail
            msg += f'Register Address: Requested > expected - {register} > {self._max_reg}. Check device instantiation & expected size!'
            valid = False
        if data > 255:  #check against input arg for data byte val
            msg += f'Data Error: {data} > 0xFF.'
            valid = False
        return (valid, msg)

    def write_page(self):
        return
    
if __name__ == "__main__":
    FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s] %(message)s"
    logging.basicConfig(format=FORMAT, level=logging.DEBUG)
    handler_bus = HandlerBus(index=1)

    eeprom = EEPROM24LCxx(handler_bus.bus, address=0x50, delay = 0.002, size=32768)
    write_success, payload1 = eeprom.write_byte(register=0x02, data=0x04, address=0x50)
    time.sleep(0.01)
    read_success, reg0x02_val = eeprom.read_byte(register=0x02, address=0x50)
    logger.info(f'payload1: {payload1}, reg0x02_val: {reg0x02_val}')

    time.sleep(0.01)
    example2_reg, example2_data = 0x03, 0x0a
    data_written = eeprom.write_read_byte(register=example2_reg, data = example2_data, address=0x50)
    logger.info(f'write_read_byte example - confirmed data_written: {data_written}')
    handler_bus.bus.close()  #close the bus
