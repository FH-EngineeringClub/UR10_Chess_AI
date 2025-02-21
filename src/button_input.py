from time import sleep
import hid
from colorama import Fore

gamepad = hid.device()

global connectionStatus
connectionStatus = False


def connectToButton():
    gamepad.close()
    try:
        gamepad.open(0x2E8A, 0x010A)
        print(Fore.GREEN + "Connected to button")
        global connectionStatus
        connectionStatus = True
    except IOError:
        print(Fore.RED + "Could not connect to button")

def listenForButton():
    gamepad.set_nonblocking(True)
    previous_state = 0
    while True:
        try:
            report = gamepad.read(64)
            if report:
                pressed = report[8:-3]
                if pressed[0] == 1 and previous_state == 0:
                    print(Fore.BLUE + "Button pressed!")
                    break
                previous_state = pressed[0]
        except IOError:
            print(Fore.YELLOW + "Error reading from button")
            connectionStatus = False
            gamepad.close()
            while connectionStatus is False:
                try:
                    print(Fore.YELLOW + "Reconnecting to button")
                    connectToButton()
                    sleep(1)
                except IOError:
                    print(Fore.RED + "Could not reconnect to button")
                    sleep(1)
