#!/usr/bin/python3
#
#    Copyright (C) 2019  Michael Johnson
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
import serial
import struct
import time

UBLOX_PREFIX = 'B5 62'


def main():
    parser = argparse.ArgumentParser(
        description='This u-blox configuration loader is a python application '
                    'that loads a configuration file saved from u-center via '
                    'the u-blox protocol over a serial port. This code was '
                    'created by an enthusiast, not u-blox.')
    parser.add_argument('--port', '-p', help='The serial port device path.',
                        required=True)
    parser.add_argument('--file', '-f', help='The configuration file path.',
                        required=True)
    parser.add_argument('--speed', '-s', help='The serial port speed/baud '
                        '(default is 9600).', default=9600)
    args = parser.parse_args()

    ser = serial.Serial(args.port, args.speed, serial.EIGHTBITS,
                        serial.PARITY_NONE, serial.STOPBITS_ONE)

    with open(args.file, 'r') as cfg_file:
        for line in cfg_file:
            if line.startswith('CFG-'):
                cfg_data = line.split(' - ')[1].strip()
                cfg_bytes = bytearray.fromhex(cfg_data)
                chk_sum = make_checksum(cfg_bytes)
                bytes_to_send = (bytearray.fromhex(UBLOX_PREFIX) +
                                 cfg_bytes + chk_sum)
                ser.write(bytes_to_send)

            # Give the receiver some time to reset
            if line.startswith('CFG-RST'):
                time.sleep(5)

    ser.close()

def make_checksum(cfg_bytes):
    CK_A = 0
    CK_B = 0
    for byte in cfg_bytes:
        CK_A = (CK_A + byte) % 256
        CK_B = (CK_B + CK_A) % 256
    return bytearray([CK_A, CK_B])

main()
