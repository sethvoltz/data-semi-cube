# The Data Semi-Cube

System and control scripts for the Data Semi-Cube

## Edge Daemon

The Edge Daemon, or `edged`, is the control service for running and querying the Data Semi-Cube's light bar edges. Under the hood, it is implemented as a simple reactor model hooked up to TCP:8300, speaking JSON one line at a time. The service will allow any number of commands to be run in a single connection, with an empty line signalling end of commands and closing the connection.

Three classes of commands are available, each paired in a getter/setter fashion:

- `setColors`, `getColors` -- Manage the colors of individual lights on the edge. Optional lock codes and mode settings may be passed.
- `requestLock`, `releaseLock` -- Request a lockout of one or more lights for a specified amount of time. Locks may be released early. Optional mode setting may be passed. Locks will auto-release after the requested time.
- `setMode`, `getMode` -- Set the current run mode of the device to one of three levels: `normal`, the default level for lowest priority info; `ambient`, for persistent data presentation; and `critical`, which will interrupt all other information.

Color data passed in will either overwrite the existing colors if there is no lock set, as long as the mode priority is met, or will only be displayed if requested through a lock code. If a non-lock color is passed to a currently locked light, the color is saved to be displayed after the lock releases.

### Example Commands

```json
{"command": "requestLock", "lights": [0,1], "duration": 60000}
{"command": "releaseLock", "lock": "32cf1b11-2f03-43fd-9f64-01aca3d8fde0"}

{"command": "setColors", "colors": ["00ff00", "00ff00", "00ff00", "00ff00", "00ff00", "00ff00"]}
{"command": "setColors", "colors": ["0000ff", "0000ff", "0000ff", "0000ff", "0000ff", "0000ff"], "mode": "critical"}
{"command": "setColors", "colors": ["ff0000", "ff0000", "ff0000", "ff0000", "ff0000", "ff0000"], "lock": "32cf1b11-2f03-43fd-9f64-01aca3d8fde0"}

{"command": "setMode", "mode": "normal"}
{"command": "setMode", "mode": "ambient"}
```


## Thoughts

* There are two main things to control: the screens and the edge bars. Each should be able to be controlled independently.
* There should be a central service which knows which services are in use (screen or edge bars) and a common library which can be used to programmatically check this and request to use one or both.
* There should also be a cron cycle to start actions at specified times and turn the screen off late at night.
* The central service should also be checked for whether the display is in normal, ambient, or critical mode to determine if it can stay on forever or turn off after a minimum run time.
* Individual services should have a set of command line scripts to expose common features for scripting. The full capabilities should be accessible via a multi-client network protocol.
* Ambient mode is where just the edge bars would light up with specific status information (weather would have temp rising/falling, risk soon/today, pressure rising/falling, etc.) and the main displays would be off
* The FauxMo service should be integrated to publish certain services for control.
    - https://github.com/sethvoltz/fauxmo
    - TBD: whether a service turned "OFF" should return to the previous running thing, or back to the default.
* Mode ideas:
    - Weather - show icon or animation on the top, current weather data on one side and forecast (temp, ran, etc) on the other
    - Bus / Train - Show next bus for specified area or routes by config
    - Dance / Party - Cycle through a series of dance animations which show off the lights
    - Device Status - Poll the network for smart devices (or check cache or specified list) and show their status. Lights would be on/off, thermostat could be current temp/mode (heating/cooling), etc.
