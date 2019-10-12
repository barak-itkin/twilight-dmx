import json
from typing import Dict
from . import dmx


class DMXMixer:
    def __init__(self):
        self.channel_to_scene = {}  # type: Dict[int, bytes]
        self.enable = True
        self.last_load_path = None

    def add_scene(self, channel: int, scene: bytes):
        if len(scene) > dmx.DMX_N_CHANNELS:
            raise ValueError('Invalid scene')
        self.channel_to_scene[channel] = scene

    def mix(self, inputs: bytes) -> bytes:
        if not self.enable:
            return inputs
        result = [0] * dmx.DMX_N_CHANNELS
        for channel, scene in self.channel_to_scene.items():
            factor = inputs[channel] / dmx.DMX_VAL_MAX
            for i, value in enumerate(scene):
                result[i] += value * factor
        return bytes(
            min(round(value), dmx.DMX_VAL_MAX)
            for value in result
        )

    def save(self, path):
        with open(path, 'w') as fp:
            json.dump(
                {
                    channel: list(values)
                    for channel, values in self.channel_to_scene.items()
                },
                fp
            )

    def load(self, path):
        with open(path, 'w') as fp:
            scenes = json.load(fp)
            self.channel_to_scene.clear()
            self.channel_to_scene.update({
                channel: bytes(values)
                for channel, values in scenes.items()
            })
            self.last_load_path = path
