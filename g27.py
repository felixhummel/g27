#!/usr/bin/env python
"""
Example::

    A0 B7 A3 04 5C 7D 02 02
     0  1  2  3  4  5  6  7


    0, 1, 2, 3: sequence, little endian
    3, 5: value, little endian
    6: group
    7: axis

NOTE! From here on, I talk big endian -- also in hex!

Wheel values::

            left               dead           right
            <-------------------XX---------------->
    dec     32769      65535     0      1     32767
    hex     80 01      ff ff  00 00 00 01     7F FF


Pedal values:

- no pressure: 7F FF
- halfway: 00 00
- full: 80 01
"""
from binascii import hexlify


# 32769 -> 0
# 0 -> 0.5
# 65535 -> 0.49
# 32767 -> 1
def _normalize(x):
    if 32769 <= x <= 65535:
        return (x - 32769) / 65535
    elif 0 == x:
        return 0.5
    elif 0 < x <= 32767:
        return (x + 32768) / 65535


BUTTON2NAME = """
0200=wheel axis
0105=paddle left
0104=paddle right
0107=wheel button left 1
0114=wheel button left 2
0115=wheel button left 3
0106=wheel button right 1
0112=wheel button right 2
0113=wheel button right 3
0201=clutch
0203=brake
0202=gas
0101=shifter button left
0102=shifter button right
0103=shifter button up
0100=shifter button down
0204=dpad left/right
0205=dpad up/down
010b=shifter button 1
0108=shifter button 2
0109=shifter button 3
010a=shifter button 4
010c=gear 1
010d=gear 2
010e=gear 3
010f=gear 4
0110=gear 5
0111=gear 6
0116=gear R
"""
def f():
    for line in BUTTON2NAME.strip().split('\n'):
        a, b = line.split('=')
        yield a.encode('ascii'), b
BUTTON2NAME_DICT = dict(f())


def powergenerator(start=0):
    """Generate powers of 256"""
    i = start
    while True:
        yield 256 ** i
        i += 1


class Bytewurst:

    def __init__(self, bs):
        self.raw = bs
        self.ints = [x for x in bs]

    def __repr__(self):
        return ' '.join(map(hexlify, self.raw))

    @property
    def bits(self):
        return ' '.join(f'{x:08b}' for x in self.ints)

    @property
    def hex(self):
        return hexlify(self.raw)

    @property
    def int(self):
        """
        For "01 00 03 0A" ints would be [1, 0, 3, 10], so::

            >>> bs = '\x01\x00\x03\x0A'
            >>> bw = Bytewurst(bs)
            >>> bw.int == (1 * 1) + (0 * 256) + (3 * 65536) + (10 * 16777216)
            True
        """
        return sum(a * b for a, b in zip(self.ints, powergenerator()))


class Button(Bytewurst):
    @property
    def name(self):
        return BUTTON2NAME_DICT.get(self.hex, f'UNKNOWN: {self.hex}')


class Value(Bytewurst):
    def __repr__(self):
        if self.int == 0:
            return '  off'
        elif self.int == 1:
            return '   on'
        else:
            return f'{self.int:5d}'

    @property
    def normalized(self):
        return _normalize(self.int)


class Message:

    def __init__(self, bs):
        self.bs = bs
        self.ints = [x for x in bs]
        self.sequence = Bytewurst(bs[0:4])
        self.value = Value(bs[4:6])
        self.button = Button(bs[6:8])

    def __repr__(self):
        return f'{self.sequence.int} {self.value.normalized:5.0%} {self.button.name}'

    @property
    def bits(self):
        return ' '.join([self.sequence.bits, self.value.bits, self.button.bits])

    @property
    def hex(self):
        """
        Human-readable hex format. LITTLE ENDIAN!
        """
        return ' '.join(f'{x:02X}' for x in self.ints)

    @property
    def grouped_hex(self):
        return f'{self.sequence.int:06X} {self.value.int:04X} {self.button.int:04X}'

    @property
    def dec(self):
        """Human-readable decimal format"""
        return ' '.join(f'{x:03d}' for x in self.ints)


class G27:
    """
    >>> import g27
    >>> wheel = g27.G27()
    >>> wheel.handlers.append(print)
    >>> wheel.loop()

    Other examples:

    >>> wheel.handlers = [lambda msg: print(msg.bits)]
    >>> wheel.handlers = [lambda msg: print(msg.hex)]
    >>> wheel.handlers = [lambda msg: print(msg.dec)]
    >>> wheel.handlers = [lambda msg: print(msg.grouped_hex)]

    >>> wheel.handlers = [g27.PressHandler('gas', lambda: print('pressed'))]
    """
    def __init__(self, path='/dev/input/js0'):
        self.path = path
        self.handlers = []

    def loop(self):
        with open(self.path, 'rb') as device:
            while True:
                bs = device.read(8)
                msg = Message(bs)
                for handler in self.handlers:
                    handler(msg)


class PressHandler:
    """
    Get a single event per press. Optionally get a release event.

    >>> on_gas_press = g27.PressHandler('gas', lambda: print('press'))
    >>> wheel.handlers = [on_gas_press]
    >>> wheel.loop()
    """
    def __init__(self, button_name=None, on_press=None, on_release=None, press_value=0.5, release_value=0.5):
        self.is_pressed = False
        self.button_name = button_name
        self.press_value = press_value
        self.release_value = release_value
        assert self.press_value <= self.release_value, 'press_value must be less than release value; range is 0...1'
        if on_press is not None:
            self.on_press = on_press
        if on_release is not None:
            self.on_release = on_release

    def on_press(self):
        pass

    def on_release(self):
        pass

    def __call__(self, msg):
        x = msg.value.normalized
        if self.button_name is not None and msg.button.name != self.button_name:
            return
        if x < 0.5:
            if not self.is_pressed:
                self.is_pressed = True
                self.on_press()
        else:
            if self.is_pressed:
                self.on_release()
            self.is_pressed = False


def main():
    """
    Print nicely formatted event messages
    """
    wheel = G27()
    wheel.handlers = [print]
    wheel.loop()


if __name__ == '__main__':
    main()
