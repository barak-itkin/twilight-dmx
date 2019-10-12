import os
import threading

from twilight.controller import DMXController
from twilight.controller.mock import DMXMockController
from twilight.mixer import DMXMixer


class ConsoleUI:
    def __init__(self, controller: DMXController, mixer: DMXMixer, save_path):
        self.controller = controller
        self.mixer = mixer
        self.waiting = threading.Event()
        self.freeze_dmx = None
        self.save_path = save_path

    def format_single_ascii(self, value, *, size=8, start='*', end='*', mark='#', blank='|'):
        result = [start] + (size - 2) * [blank] + [end]
        index = round((value / 255) * (size - 1))
        result[index] = mark
        return ''.join(result)

    def combine_as_columns(self, values, *, sep=' '):
        values = list(values)
        longest = max(len(v) for v in values)
        lines = [
            sep.join(
                v[l] if l < len(v) else ' '
                for v in values
            )
            for l in range(longest)
        ]
        return os.linesep.join(lines)

    def format_ascii(self, data, *, vertical=True):
        sliders = [self.format_single_ascii(v) for i, v in enumerate(data)]
        if vertical:
            sliders = [s[::-1] for s in sliders]
        sliders = [s + str(i + 1) for i, s in enumerate(sliders)]
        if vertical:
            return self.combine_as_columns(sliders)
        else:
            return os.linesep.join(sliders)

    def _read_input(self, prompt, *, choices=None, lowercase=True):
        while True:
            value = input(prompt).strip()
            if lowercase:
                value = value.lower()
            if choices and value not in choices:
                print(f'Invalid choice, expected one of {", ".join(repr(c) for c in choices)}')
                continue
            return value

    def _get_single_slider(self, prompt):
        while True:
            if isinstance(self.controller, DMXMockController):
                result = input('This is a mock, so just enter a number: ')
                try:
                    if result.strip().lower() == 'q':
                        return
                    result = int(result.strip()) - 1
                    if result < 0:
                        print('ERROR: Please enter a positive number')
                        continue
                    else:
                        return result
                except:
                    print('ERROR: Please enter a valid number')
                    continue
            print(prompt)
            choice = self._read_input('', choices=('', 'q'))
            if choice == 'q':
                return
            data = self.controller.obtain_once()
            high = [i for i, v in enumerate(data) if v > 200]
            low = [i for i, v in enumerate(data) if v < 50]
            if len(high) != 1 or len(low) != len(data) - 1:
                print('ERROR: Please set exactly one slider to max, and the rest to zero')
                continue
            return high[0]

    def _program_scene(self):
        print('****** Entering scene programming ******')
        print('')
        scene = None
        mixer_prev = self.mixer.enable
        self.mixer.enable = False
        while True:
            if scene is None:
                print('Set the scene you want and hit Enter (or [Q]uit)')
                choice = self._read_input('', choices=('', 'q'))
                if choice == 'q':
                    break
                data = self.controller.obtain_once()
                self.freeze_dmx = scene = self.controller.last_input
                self._print(data)
            else:
                slider = self._get_single_slider('Set the slider to assign, and hit Enter (or [Q]uit)')
                if slider is None:
                    break
                if slider in self.mixer.channel_to_scene:
                    print('This slider is already taken by the following scene:')
                    self.freeze_dmx = self.mixer.channel_to_scene[slider]
                    self._print(self.mixer.channel_to_scene[slider])
                    if self._read_input('Are you sure you want to override it? [y/n]', choices=('y', 'n')) != 'y':
                        continue
                self.mixer.add_scene(slider, scene)
                print('** Scene programmed successfully **')
                print('')
                self.freeze_dmx = None
                scene = None
        self.freeze_dmx = None
        self.mixer.enable = mixer_prev

    def _print(self, data):
        print(self.format_ascii(data))
        self.waiting.set()

    def _print_once(self):
        self.controller.subscribe_once(self._print)
        self.waiting.wait()

    def _on_dmx_data(self, data):
        if self.freeze_dmx:
            self.controller.set_dmx(self.freeze_dmx)
        else:
            self.controller.set_dmx(
                self.mixer.mix(data)[:len(data)]
            )

    def run(self):
        try:
            self.controller.subscribe('ui-control', self._on_dmx_data)
            while True:
                print('******** Main menu ********')
                mixer_status = 'enabled' if self.mixer.enable else 'disabled'
                print('You can do the following:')
                print('[P] Print')
                print('[S] Program scenes')
                print(f'[T] Toggle mixer (currently {mixer_status})')
                print(f'[W] Save')
                print('[Q] Quit')
                choice = self._read_input('What would you like to do? ', choices=('p', 's', 't', 'q', 'w'))
                if choice == 'p':
                    self._print(self.controller.obtain_once())
                    continue
                elif choice == 's':
                    self._program_scene()
                    print()
                elif choice == 't':
                    self.mixer.enable = not self.mixer.enable
                elif choice == 'w':
                    self.mixer.save(self.save_path)
                    print('Saved successfully')
                else:
                    self.controller.request_break()
                    break
        finally:
            if self.mixer.channel_to_scene:
                if self._read_input('Save changes? [y/n] ', choices=('y', 'n')) == 'y':
                    path = input(f'Enter a path (keep blank for "{self.save_path}"): ')
                    self.mixer.save(path or self.save_path)
