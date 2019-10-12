import time
from ..controller import DMXController


class DMXMockController(DMXController):
    def __init__(self):
        super().__init__()
        self.break_requested = False
        self.mock_data = bytes(range(0, 255, 16))
        self.last_set = None
        self.hz = 1

    def read_data(self):
        time.sleep(1 / self.hz)
        return self.mock_data

    def _run(self):
        while not self.break_requested:
            self._on_data(self.read_data())

    def set_dmx(self, data: bytes):
        if data != self.last_set:
            print(f'DMX set to {data}')
        self.last_set = data
