BAUDRATE = 115200

HEADER = bytes([
    126, 129, 42
])

HEADER_END = 0
MSG_TYPE_DMX = 1


def guess_port():
    import sys
    if sys.platform.startswith('win'):
        import serial.tools.list_ports
        ports = [e.device for e in serial.tools.list_ports.comports()]
    else:
        raise NotImplementedError('Guessing ports is only supported on Windows')

    if len(ports) == 0:
        raise ValueError('No serial port found!')
    elif len(ports) == 1:
        return ports[0]
    else:
        raise ValueError('Too many options: %s' % ', '.join(ports))
