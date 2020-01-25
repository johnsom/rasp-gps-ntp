#!/usr/bin/python3
#
#    Copyright (C) 2019  Michael Johnson
#
#    Parts of the IMU temperature code come from ozzmaker at:
#    https://github.com/ozzmaker/BerryIMU
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
import argparse
import smbus
import sys
import time

def main():
    parser = argparse.ArgumentParser(
        description='This application returns the current temperature from '
                    'a ozzmaker BerryIMU over the I2C bus.')
    parser.add_argument('--bus', '-b',
                        help='The I2C bus the IMU is attached to. '
                             '(default is 3)', default=3)
    temp_group = parser.add_mutually_exclusive_group(required=True)
    temp_group.add_argument('--celsius', '-c', action='store_true',
                        help='Request the celsius IMU temperature.')
    temp_group.add_argument('--fahrenheit', '-f', action='store_true',
                        help='Request the fahrenheit IMU temperature.')
    args = parser.parse_args()

    # Get I2C bus
    bus = smbus.SMBus(args.bus)

    # BMP280 address, 0x77
    # Read data back from 0x88(136), 24 bytes
    b1 = bus.read_i2c_block_data(0x77, 0x88, 24)

    # Convert the data Temp coefficents
    dig_T1 = b1[1] * 256 + b1[0]
    dig_T2 = b1[3] * 256 + b1[2]
    if dig_T2 > 32767 :
        dig_T2 -= 65536
    dig_T3 = b1[5] * 256 + b1[4]
    if dig_T3 > 32767 :
        dig_T3 -= 65536

    # BMP280 address, 0x77(118)
    # Select Control measurement register, 0xF4(244)
    #           0x27(39)        Pressure and Temperature Oversampling rate = 1
    #                                       Normal mode
    bus.write_byte_data(0x77, 0xF4, 0x27)

    # BMP280 address, 0x77(118)
    # Select Configuration register, 0xF5(245)
    #               0xA0(00)        Stand_by time = 1000 ms
    bus.write_byte_data(0x77, 0xF5, 0xA0)

    time.sleep(0.5)

    # BMP280 address, 0x77(118)
    # Read data back from 0xF7(247), 8 bytes
    # Pressure MSB, Pressure LSB, Pressure xLSB, Temperature MSB,
    # Temperature LSB
    # Temperature xLSB, Humidity MSB, Humidity LSB
    data = bus.read_i2c_block_data(0x77, 0xF7, 8)

    # Convert temperature data to 19-bits
    adc_t = ((data[3] * 65536) + (data[4] * 256) + (data[5] & 0xF0)) / 16

    # Temperature offset calculations
    var1 = ((adc_t) / 16384.0 - (dig_T1) / 1024.0) * (dig_T2)
    var2 = (((adc_t) / 131072.0 - (dig_T1) / 8192.0) * (
        (adc_t)/131072.0 - (dig_T1)/8192.0)) * (dig_T3)

    cTemp = (var1 + var2) / 5120.0
    if args.celsius:
        print('%.2f' % cTemp)
    elif args.fahrenheit:
        print('%.2f' % (cTemp * 1.8 + 32))

main()
