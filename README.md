# The Data Semi-Cube

System and control scripts for the Data Semi-Cube

## Thoughts

* There are two main things to control: the screens and the edge bars. Each should be able to be controlled independently.
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

###  Thoughts on the light bars

- Actor model for receiving commands, backed by one queue per bar, queue holds the pair of colors for that bar
    + Set color: includes null or color for all bars, two colors per bar
        * Optional lock code allows setting during lock
        * Optional priority code, this will initially be used just to determine if it shows the color during more ambient lighting levels
    + Request lock: incudes millis to lock out normal display and which bar(s) to lock
        * Optional priority code, same as Set color
    + Release lock: takes lock code and releases a lock early
    + Set mode: sets the run level of the device for lights to show
        * Includes optional "timeout" paramater after which all colors are cleared to off. This timeout will be restarted for every color set or  animation lock (after it completes) as long as those meet the level requirements to display at all
    + Get mode: Gets the mode level for the device
- Normal set color commands come in and are relayed to lights ASAP via main runtime queue
    + While a bar is locked, incoming values for that bar are cached to a fixed variable, overwriting previous values, and bypass the queue
    + If a requested lock has insufficient priority, it will receive a denial with zero for the time until unlock and an "insufficient priority" flag
- Command can request "animation" lock for a set period of time, for any set of bars, will get back lock code, or denial
    + Requests must specify how long to lock for
    + with lock code, colors for those bars is passed long to queues, colors specified for bars not locked are discarded
    + If currently locked, will respond with next expected unlock time
- Mode levels are: Normal, Ambient, Critical
    + Default mode is Normal and all commands without a specified priority default to Normal as well. Any color set with insufficient priority is immediately thrown away
    + Most services will want to push individual colors (weather, stock, etc) as "Ambient" priority while animations will generally use "Normal" level. Information such as alerts, emergency notifications, etc, may use the "Critical" level.
