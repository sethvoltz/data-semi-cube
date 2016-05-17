# The Data Semi-Cube

System and control scripts for the Data Semi-Cube

## Thoughts

* There are two main things to control: the screens and the edge bars. Each should be able to be controlled independently or together.
* There should be a central service which knows which services are in use (screen or edge bars) and a common library which can be used to programmatically check this and request to use one or both.
* There should also be a cron cycle to start actions at specified times and turn the screen off late at night.
* The central service should also be checked for whether the display is in day or night mode to determine if it can stay on forever or turn off after a minimum run time.
* An individual service should be accessible via the command line
* An optional mode could be ambient/full where in ambient mode just the edge bars would light up with specific status information (weather would have temp rising/falling, risk soon/today, pressure rising/falling, etc.)
* The FauxMo service should be integrated to publish certain services for control.
    - https://github.com/sethvoltz/fauxmo
    - TBD: whether a service turned "OFF" should return to the previous running thing, or back to the default.
* Mode ideas:
    - Weather - show icon or animation on the top, current weather data on one side and forecast (temp, ran, etc) on the other
    - Bus / Train - Show next bus for specified area or routes by config
    - Dance / Party - Cycle through a series of dance animations which show off the lights
    - Device Status - Poll the network for smart devices (or check cache or specified list) and show their status. Lights would be on/off, thermostat could be current temp/mode (heating/cooling), etc.
