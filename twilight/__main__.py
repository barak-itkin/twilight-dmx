import argparse
import os
import threading
import time

from twilight.mixer import DMXMixer
from twilight.ui.console import ConsoleUI


def main(argv=None):
    parser = argparse.ArgumentParser('Twilight DMX Controller')
    parser.add_argument('--mock', action='store_true',
                        help='Use a mock input instead of input over serial')
    parser.add_argument('--scenes-path', default='scenes.json', type=str,
                        required=False, help='Path to the scenes file')
    parser.add_argument('--interactive', action='store_true',
                        help='Use a GUI')
    parser.add_argument('--serial-port', type=str, required=False, default=None,
                        help='Which serial port to use?')
    args = parser.parse_args(argv)

    if args.mock:
        from twilight.controller.mock import DMXMockController
        controller = DMXMockController()
    else:
        from twilight.controller.serial import DMXSerialController
        controller = DMXSerialController(port=args.serial_port)

    mixer = DMXMixer()
    if args.scenes_path and os.path.exists(args.scenes_path):
        mixer.load(args.scenes_path)

    if args.interactive:
        ui = ConsoleUI(controller, mixer, args.scenes_path)
        ui_thread = threading.Thread(target=ui.run)
        controller_thread = threading.Thread(target=controller.run)

        try:
            ui_thread.start()
            controller_thread.start()
            while ui_thread.is_alive():
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            controller.request_break()
            ui_thread.join()
            controller_thread.join()
    elif mixer.channel_to_scene:
        controller.subscribe(
            'mix', lambda d: controller.set_dmx(
                mixer.mix(d)[:len(d)]
            )
        )
        controller.run()


if __name__ == '__main__':
    main()
