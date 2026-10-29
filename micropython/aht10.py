"""
Minimal MicroPython driver for the AHT10 temperature/humidity sensor.

Usage:
    from machine import I2C, Pin
    from aht10 import AHT10

    i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=100000)
    sensor = AHT10(i2c)
    print(sensor.temperature, sensor.humidity)
"""

import time

AHT10_ADDR = 0x38

_CMD_INIT = b"\xE1\x08\x00"      # initialise + enable calibration
_CMD_MEASURE = b"\xAC\x33\x00"   # trigger measurement
_CMD_RESET = b"\xBA"             # soft reset

_STATUS_BUSY = 0x80
_STATUS_CALIBRATED = 0x08


class AHT10:
    def __init__(self, i2c, address=AHT10_ADDR):
        self.i2c = i2c
        self.address = address
        self.reset()
        self._init_sensor()

    def reset(self):
        self.i2c.writeto(self.address, _CMD_RESET)
        time.sleep_ms(20)

    def _init_sensor(self):
        self.i2c.writeto(self.address, _CMD_INIT)
        time.sleep_ms(10)
        if not self._status() & _STATUS_CALIBRATED:
            raise RuntimeError("AHT10 failed to calibrate")

    def _status(self):
        return self.i2c.readfrom(self.address, 1)[0]

    def read(self):
        """Return (temperature_C, humidity_percent)."""
        self.i2c.writeto(self.address, _CMD_MEASURE)
        time.sleep_ms(80)  # datasheet: measurement takes ~75 ms

        # Wait until the sensor is no longer busy (max ~100 ms extra)
        for _ in range(10):
            data = self.i2c.readfrom(self.address, 6)
            if not data[0] & _STATUS_BUSY:
                break
            time.sleep_ms(10)
        else:
            raise OSError("AHT10 measurement timed out")

        raw_hum = (data[1] << 12) | (data[2] << 4) | (data[3] >> 4)
        raw_temp = ((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5]

        humidity = raw_hum * 100 / 1048576          # 2^20
        temperature = raw_temp * 200 / 1048576 - 50
        return temperature, humidity

    @property
    def temperature(self):
        return self.read()[0]

    @property
    def humidity(self):
        return self.read()[1]