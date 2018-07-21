# Python G27
Inspired by http://upgrayd.blogspot.de/2011/03/logitech-dual-action-usb-gamepad.html


## Requirements
Python 3.6+


## Usage

### Dump Events
```
./g27.py
```

### From Python
```
import g27
wheel = g27.G27()
wheel.handlers = [print]
wheel.loop()
```

`handlers` are given a `g27.Message` object. See the source for details.
