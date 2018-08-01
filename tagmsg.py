from blinker import signal

ON_CONNECT = 'connect'
ON_TELEMETRY = 'telemetry'
ON_PRESS_FIRE = 'fire'
ON_PRESS_RELOAD = 'reload'
ON_PRESS_POWER = 'power'
ON_PRESS_ACTION = 'action'
ON_START_RELOAD = 'start_reload'
ON_FINISH_RELOAD = 'finish_reload'
ON_SET_RECOIL = 'set_recoil'
ON_SET_FIRE_MODE = 'set_fire_mode'
ON_AMMO_CHANGE = 'ammo_change'
ON_MESSAGE = 'message'

on_message = signal(ON_MESSAGE)
on_telemetry_data = signal(ON_TELEMETRY)
on_ammo_changed = signal(ON_AMMO_CHANGE)

on_press_fire = signal(ON_PRESS_FIRE)
on_press_reload = signal(ON_PRESS_RELOAD)
on_press_power = signal(ON_PRESS_POWER)
on_press_action = signal(ON_PRESS_ACTION)

on_connect = signal(ON_CONNECT)
on_start_reload = signal(ON_START_RELOAD)
on_finish_reload = signal(ON_FINISH_RELOAD)
on_set_recoil = signal(ON_SET_RECOIL)
on_set_fire_mode = signal(ON_SET_FIRE_MODE)
