#!/usr/bin/python3
#
#    Copyright (C) 2022  Michael Johnson
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
import binascii
import configparser
import requests
import serial
import sys
import time
import urllib

DEBUG = False


def main():
    parser = argparse.ArgumentParser(
       description='This u-blox assitnow loader is a python application '
                   'that loads AssistNow data from u-blox into a receiver '
                   'using the u-blox protocol over a serial port. '
                   'This code was created by an enthusiast, not u-blox.')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Print debug information about the data being '
                             'loaded.')
    parser.add_argument('--file', '-f', help='The configuration file path.',
                        required=True)
    parser.add_argument('--speed', '-s', help='The serial port speed/baud '
                        '(default is 9600).', default=9600)
    parser.add_argument('--port', '-p', help='The serial port device path.',
                        required=True)
    args = parser.parse_args()

    if args.debug:
        global DEBUG
        DEBUG = True

    config = configparser.ConfigParser()
    if not config.read(args.file):
        sys.exit("Invalid configuration file path.")
    if not config.has_section('AssistNowOnline'):
        sys.exit("Invalid configuration file.")
    if not config.get('AssistNowOnline', 'token', fallback=None):
        print("No AssistNow API token provided. Skipping AssistNow.")
        return

    params = get_assistnow_params(config)
    params = urllib.parse.urlencode(params, safe=',')

    try:
        response = requests.get(
            'https://online-live1.services.u-blox.com/GetOnlineData.ashx',
            params=params)
        response.raise_for_status()
    except Exception as e:
        print('Got an error getting AssistNow data from server 1, '
              'trying server 2: %s' % str(e))
        try:
            response = requests.get(
                'https://online-live2.services.u-blox.com/GetOnlineData.ashx',
                params=params)
            response.raise_for_status()
        except Exception as e:
            print('Got an error getting AssistNow data from server 2, '
                  'skipping AssistNow: %s' % str(e))
            return

    ser = serial.Serial(args.port, args.speed, serial.EIGHTBITS,
                        serial.PARITY_NONE, serial.STOPBITS_ONE)

    msg_sep = bytearray.fromhex('B5 62')

    byte_data = response.content
    messages = byte_data.split(msg_sep)
    for msg in messages:
        if msg == b'':
            continue
        # Check for non-MGA messages from AssistNow
        if msg[0] != 19:
            print('Warning: Non-Multiple GNSS Assitance Message Received, '
                  'skipping: %s' % binascii.hexlify(msg_sep + msg))
            continue
        msg_chksum = msg[-2:]
        if msg_chksum != make_checksum(msg[:-2]):
            print('Message failed UBX checksum test, skipping: %s' %
                  binascii.hexlify(msg_sep + msg))
            continue
        if DEBUG:
            print_debug(msg)
        ser.write(msg_sep + msg)
        time.sleep(int(config.get('AssistNowOnline', 'delay', fallback=100)) /
                   1000)
    ser.close()

def get_assistnow_params(config):
    params = {'token': config['AssistNowOnline']['token']}

    datatype = config.get('AssistNowOnline', 'datatype', fallback=None)
    if datatype:
        params['datatype'] = datatype

    format = config.get('AssistNowOnline', 'format', fallback='mga')
    if format:
        params['format'] = format

    gnss = config.get('AssistNowOnline', 'gnss', fallback=None)
    if gnss:
        params['gnss'] = gnss

    lat = config.get('AssistNowOnline', 'lat', fallback=None)
    if lat:
        params['lat'] = lat

    lon = config.get('AssistNowOnline', 'lon', fallback=None)
    if lon:
        params['lon'] = lon

    alt = config.get('AssistNowOnline', 'alt', fallback=None)
    if alt:
        params['alt'] = lon

    pacc = config.get('AssistNowOnline', 'pacc', fallback=None)
    if pacc:
        params['pacc'] = pacc

    tacc = config.get('AssistNowOnline', 'tacc', fallback=None)
    if tacc:
        params['tacc'] = tacc

    latency = config.get('AssistNowOnline', 'latency', fallback=None)
    if latency:
        params['latency'] = latency

    filteronpos = config.get('AssistNowOnline', 'filteronpos', fallback=False)
    if filteronpos.lower() == 'true':
        params['filteronpos'] = 'True'

    return params


# Old school switch statement for python version compatibility
def print_debug(msg):
    # 0x13 0x00 - UBX-MGA-GAL
    if msg.startswith(b'\x13\x00'):
        # 0x01
        if msg[4] == 1:
            print('UBX-MGA-GPS-EPH: GPS Ephemeris Assistance')
            return
        if msg[4] == 2:
            print('UBX-MGA-GPS-ALM: GPS Almanac Assistance')
            return
        if msg[4] == 4:
            print('UBX-MGA-GPS-HEALTH: GPS Health Assistance')
            return
        if msg[4] == 5:
            print('UBX-MGA-GPS-UTC: GPS UTC Assistance')
            return
        if msg[4] == 6:
            print('UBX-MGA-GPS-IONO: GPS Ionosphere Assistance')
            return
     # 0x13 0x02 - UBX-MGA-GAL
    if msg.startswith(b'\x13\x02'):
        # 0x01
        if msg[4] == 1:
            print('UBX-MGA-GAL-EPH: Galileo Ephemeris Assistance')
            return
        # 0x02
        if msg[4] == 2:
            print('UBX-MGA-GAL-ALM: Galileo Almanac Assistance')
            return
        # 0x03
        if msg[4] == 3:
            print('UBX-MGA-GAL-TIMEOFFSET: Galileo GPS time offset assistance')
            return
        # 0x05
        if msg[4] == 5:
            print('UBX-MGA-GAL-UTC: Galileo UTC Assistance')
            return
    # 0x13 0x03 - UBX-MGA-BDS
    if msg.startswith(b'\x13\x03'):
        # 0x01
        if msg[4] == 1:
            print('UBX-MGA-BDS-EPH: BDS Ephemeris Assistance')
            return
        # 0x02
        if msg[4] == 2:
            print('UBX-MGA-BDS-ALM: BDS Almanac Assistance')
            return
        # 0x04
        if msg[4] == 4:
            print('UBX-MGA-BDS-HEALTH: BDS Health Assistance')
            return
        # 0x05
        if msg[4] == 5:
            print('UBX-MGA-BDS-UTC: BDS UTC Assistance')
            return
        # 0x06
        if msg[4] == 6:
            print('UBX-MGA-BDS-IONO: BDS Ionospheric Assistance')
            return
    # 0x13 0x05 - UBX-MGA-QZSS
    if msg.startswith(b'\x13\x05'):
        # 0x01
        if msg[4] == 1:
            print('UBX-MGA-QZSS-EPH: QZSS Ephemeris Assistance')
            return
        # 0x02
        if msg[4] == 2:
            print('UBX-MGA-QZSS-ALM: QZSS Almanac Assistance')
            return
        # 0x04
        if msg[4] == 4:
            print('UBX-MGA-QZSS-HEALTH: QZSS Health Assistance')
            return
    # 0x13 0x06 - UBX-MGA-GLO
    if msg.startswith(b'\x13\x06'):
        if msg[4] == 1:
            print('UBX-MGA-GLO-EPH: GLONASS Ephemeris Assistance')
            return
        if msg[4] == 2:
            print('UBX-MGA-GLO-ALM: GLONASS Almanac Assistance')
            return
        if msg[4] == 3:
            print('UBX-MGA-GLO-TIMEOFFSET: GLONASS Auxiliary Time Offset '
                  'Assistance')
            return
    # 0x13 0x20 - UBX-MGA-ANO
    if msg.startswith(b'\x13\x20'):
        # 0x00
        if msg[4] == 0:
            print('UBX-MGA-ANO: Multiple GNSS AssistNow Offline Assistance')
            return
    # 0x13 0x21 - UBX-MGA-FLASH
    if msg.startswith(b'\x13\x21'):
        # 0x01
        if msg[4] == 1:
            print('UBX-MGA-FLASH-DATA: Transfer MGA-ANO data block to flash')
            return
        # 0x02
        if msg[4] == 2:
            print('UBX-MGA-FLASH-STOP: Finish flashing MGA-ANO data')
            return
        # 0x03 - Should not see this from AssitNow
        if msg[4] == 3:
            print('UBX-MGA-FLASH-ACK: Acknowledge last FLASH-DATA or -STOP')
            return
    # 0x13 0x40 - UBX-MGA-INI
    if msg.startswith(b'\x13\x40'):
        # 0x00
        if msg[4] == 0:
            print('UBX-MGA-INI-POS_XYZ: Initial Position Assistance')
            return
        # 0x01
        if msg[4] == 1:
            print('UBX-MGA-INI-POS_LLH: Initial Position Assistance')
            return
        # 0x10
        if msg[4] == 16:
            print('UBX-MGA-INI-TIME_UTC: Initial Time Assistance')
            return
        # 0x11
        if msg[4] == 17:
            print('UBX-MGA-INI-TIME_GNSS: Initial Time Assistance')
            return
        # 0x20
        if msg[4] == 32:
            print('UBX-MGA-INI-CLKD: Initial Clock Drift Assistance')
            return
        # 0x21
        if msg[4] == 33:
            print('UBX-MGA-INI-FREQ: Initial Frequency Assistance')
            return
        # 0x30
        if msg[4] == 48:
            print('UBX-MGA-INI-EOP: Earth Orientation Parameters Assistance')
            return
    # 0x13 0x60 - UBX-MGA-ACK - Should not see this from AssitNow
    if msg.startswith(b'\x13\x60'):
        print('UBX-MGA-ACK-DATA0: Multiple GNSS Acknowledge message')
        return
    # 0x13 0x80 - UBX-MGA-DBD - Should not see this from AssitNow
    if msg.startswith(b'\x13\x80'):
        print('UBX-MGA-DBD: Navigation Database Dump Entry')
        return
    print('Unkown Message: %s' % binascii.hexlify(msg))


def make_checksum(cfg_bytes):
    CK_A = 0
    CK_B = 0
    for byte in cfg_bytes:
        CK_A = (CK_A + byte) % 256
        CK_B = (CK_B + CK_A) % 256
    return bytearray([CK_A, CK_B])

main()
