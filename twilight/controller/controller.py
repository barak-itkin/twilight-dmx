import abc
import uuid
import threading
from typing import Callable


class DMXController(metaclass=abc.ABCMeta):
    def __init__(self):
        self.callbacks = dict()
        self.last_input = None
        self.break_requested = False

    def subscribe(self, subscriber_name, callback: Callable[[bytes], None]):
        self.callbacks[subscriber_name] = callback

    def unsubscribe(self, subscriber_name):
        del self.callbacks[subscriber_name]

    def subscribe_once(self, callback: Callable[[bytes], None]):
        subscriber_id = uuid.uuid4()
        def action(data):
            self.unsubscribe(subscriber_id)
            callback(data)
        self.subscribe(subscriber_id, action)

    def obtain_once(self):
        event = threading.Event()
        result = None
        def callback(data):
            nonlocal result
            result = data
            event.set()
        self.subscribe_once(callback)
        event.wait()
        return result

    @abc.abstractmethod
    def set_dmx(self, data: bytes):
        raise NotImplementedError()

    def _on_data(self, data: bytes):
        self.last_input = data
        for cb in tuple(self.callbacks.values()):
            cb(data)

    def request_break(self):
        self.break_requested = True

    @abc.abstractmethod
    def _run(self):
        raise NotImplementedError()

    def _wait_till_complete(self):
        pass

    def run(self):
        try:
            self.break_requested = False
            self._run()
        except KeyboardInterrupt:
            self.request_break()
        self._wait_till_complete()
