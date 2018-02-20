import time
import sys
import struct

from bpmicro.usb import usb_wraps
from bpmicro import startup
from bpmicro.cmd import bulk2
from bpmicro.usb import validate_read
from bpmicro import util

def dexit():
    print 'Debug break'
    sys.exit(0)

scalars = {
    # -3.5V: leftover after below
    0x01: -3.476 / 0x38F0,
    # 30V:  best guess based on scaling other readings
    0x10: 37.28 / 0xBA70,
    # -5V: best guess based on scaling other readings
    0x05: -4.93 / 0x31D0,
    # 0V: very likely based on 0 reading
    0x15: 37.28 / 0xBA70,
    # +5V: reasonable confidence
    # removing, reconnecting J1 shifts +5V by 100 mV or so as well as +15V, and +35V
    # +15V and +35V are already known and this was already suspected to be +5V
    0x0c: 5.44 / 0x3310,
    # 15V: confident
    # Disconnecting causes this to go up by 1.5 times, no other channel changes
    # (good thing it didn't damage anything...)
    0x09: 16.00 / 0xA050,
    # 35V: confident
    # Tapped line and varied voltage to confirm is 35V
    # Calibrated with meter
    # I can hear a SMPS moving with voltage
    # meter: 29.76
    #   0x9430 (29.632 V)
    #   0x9420 (29.619 V)
    #   0x9430 (29.632 V)
    0x14: 29.76 / 0x9430,
}

def read_adc(dev):
    bulkRead, bulkWrite, _controlRead, _controlWrite = usb_wraps(dev)

    print 'NOTE: best guess'
    for reg in (0x01, 0x10, 0x05, 0x15, 0x0C, 0x09, 0x14):
        buff = bulk2(dev, "\x19" + chr(reg) + "\x00", target=2)
        b = struct.unpack('<H', buff)[0]
        print '  0x%02X: 0x%04X (%0.3f V)' % (reg, b, scalars[reg] * b)

def cleanup_adc(dev):
    _bulkRead, bulkWrite, _controlRead, _controlWrite = usb_wraps(dev)
    
    # Generated from packet 1220/1221
    bulkWrite(0x02, "\x50\x1A\x00\x00\x00")
    
    # Generated from packet 1222/1223
    buff = bulk2(dev,
            "\x66\xB9\x00\x00\xB2\x02\xFB\xFF\x25\x44\x11\x00\x00\x66\xB9\x00"
            "\x00\xB2\x02\xFB\xFF\x25\x44\x11\x00\x00",
            target=2)
    validate_read("\x83\x00", buff, "packet 1224/1225")
    
    # Generated from packet 1226/1227
    buff = bulk2(dev, "\x02", target=6)
    validate_read("\x84\x00\x50\x01\x09\x00", buff, "packet 1228/1229")
    
    # Generated from packet 1230/1231
    buff = bulk2(dev, "\x57\x83\x00", target=2)
    validate_read("\x00\x00", buff, "packet 1232/1233")

if __name__ == "__main__":
    import argparse 
    
    parser = argparse.ArgumentParser(description='Replay captured USB packets')
    util.add_bool_arg(parser, '--cycle', default=False, help='') 
    args = parser.parse_args()

    bp = startup.get()

    print
    print
    # didn't fix 17/18 issue
    #time.sleep(5)
    print
    
    if 1:
        import os

        try:
            while True:
                os.system('clear')
                read_adc(bp.dev)
                time.sleep(0.2)
        finally:
            print 'Cleaning up on exit'
            cleanup_adc(bp.dev)

    if 0:
        import curses
        import atexit
        
        @atexit.register
        def goodbye():
            """ Reset terminal from curses mode on exit """
            curses.nocbreak()
            if stdscr:
                stdscr.keypad(0)
            curses.echo()
            curses.endwin()        

        stdscr = curses.initscr()
        while True:
            stdscr.clear()
            read_adc(bp.dev)
            time.sleep(0.2)
        
    print 'Complete'
