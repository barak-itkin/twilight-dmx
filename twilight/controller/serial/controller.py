import serial
import struct

from . import protocol
from ..controller import DMXController


class DMXSerialController(DMXController):
    def __init__(self, *, port=None, baudrate=protocol.BAUDRATE, **serial_kwargs):
        super().__init__()
        self.port = port or protocol.guess_port()
        self.baudrate = baudrate
        self.serial_kwargs = serial_kwargs
        self._conn = None

    def _write_msg(self, msg_type, data):
        self._conn.write(protocol.HEADER)
        self._conn.write(protocol.HEADER)
        self._conn.write(protocol.HEADER)
        self._conn.write(bytes([protocol.HEADER_END]))
        self._conn.write(bytes([msg_type]))
        self._conn.write(struct.pack('>H', len(data)))
        self._conn.write(data)
        self._conn.write(bytes(self._compute_checksum(msg_type, data)))

    def _read_byte(self):
        val = self._conn.read(1)
        if not val:
            return -1
        return val[0]

    @staticmethod
    def _compute_checksum(msg_type, data):
        return (sum(data) + msg_type) & 0xff

    def read_msg(self):
        fail_ret = (False, None, None)
        header_index = 0
        finished_header = False
        while not self.break_requested:
            val = self._read_byte()
            if val == -1:
                return fail_ret
            if header_index < len(protocol.HEADER) and val == protocol.HEADER[header_index]:
                header_index += 1
            elif header_index == len(protocol.HEADER) and val == protocol.HEADER_END:
                finished_header = True
                break
            elif header_index == len(protocol.HEADER) and val == protocol.HEADER[0]:
                header_index = 1
                finished_header = False
            else:
                header_index = 0
                finished_header = False

        if not finished_header:
            return fail_ret

        msg_type = self._read_byte()
        if msg_type == -1:
            return fail_ret

        len_bytes = self._conn.read(2)
        if len(len_bytes) != 2:
            return fail_ret
        msg_len = struct.unpack('>H', len_bytes)[0]

        data = self._conn.read(msg_len)
        if len(data) != msg_len:
            return fail_ret

        checksum = self._read_byte()
        if checksum == -1:
            return fail_ret

        computed = self._compute_checksum(msg_type, data)
        if computed != checksum:
            return fail_ret

        return True, msg_type, data

    def _run(self):
        try:
            self._conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                **self.serial_kwargs
            )
            while not self.break_requested:
                read_ok, msg_type, msg_data = self.read_msg()
                if not read_ok:
                    continue

                if msg_type == protocol.MSG_TYPE_DMX:
                    self._on_data(msg_data)
                    self._conn.flushOutput()
                else:
                    print(msg_type, repr(msg_data))
        finally:
            if self._conn:
                self._conn.close()
                self._conn = None

    def set_dmx(self, data: bytes):
        self._write_msg(protocol.MSG_TYPE_DMX, data)
