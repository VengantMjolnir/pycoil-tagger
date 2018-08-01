from bluepy.btle import UUID, Peripheral, Scanner, DefaultDelegate, BTLEException
import struct
from threading import Timer
from blinker import signal
from utils import print_console
import binascii
import tagmsg
import json

log_id_data = False
log_telemetry_data = False

MAIN_SERVICE    = "e6f59d10-8230-4a5c-b22f-c062b1d329e3"
ID_UUID         = "e6f59d11-8230-4a5c-b22f-c062b1d329e3"
TELEMETRY_UUID  = "e6f59d12-8230-4a5c-b22f-c062b1d329e3"
COMMAND_UUID    = "e6f59d13-8230-4a5c-b22f-c062b1d329e3"
CONFIG_UUID     = "e6f59d14-8230-4a5c-b22f-c062b1d329e3"
CLIENT_CONFIG   = "00002902-0000-1000-8000-00805f9b34fb"

TYPE_PISTOL = 2
TYPE_RIFLE = 1
STATE_IDLE = 0
STATE_RELOADING = 1

FIRE_MODE_SINGLE = 0
FIRE_MODE_BURST = 1
FIRE_MODE_AUTO = 2

SHOT_MODE_OUTDOOR_NO_CONE = 0
SHOT_MODE_OUTDOOR_WITH_CONE = 1
SHOT_MODE_INDOOR_NO_CONE = 2

BUTTON_NONE = 0x0
BUTTON_TRIGGER = 0x1
BUTTON_RELOAD = 0x2
BUTTON_WALKIE_TALKIE = 0x4
BUTTON_RESET = 0x8
BUTTON_POWER = 0x10
BUTTON_RECOIL_CNT = 0x20
BUTTON_MAX = 0x20


class TaggerService:
    scanner = None
    recoil_device = None
    tagger = None
    connecting = False
    fire_event = None
    connect_event = None
    recoil_enabled = True
    fire_mode = FIRE_MODE_SINGLE
    shot_mode = SHOT_MODE_INDOOR_NO_CONE
    max_ammo = 30

    def __init__(self):
        self.scanner = Scanner().withDelegate(ScanDelegate(self))
        # button press signals
        tagmsg.on_press_reload.connect(self.reload_pressed)
        tagmsg.on_press_power.connect(self.set_recoil)
        tagmsg.on_press_action.connect(self.toggle_fire_mode)
        # reload vars
        self.reload_state = STATE_IDLE
        self.reload_interval = 3.0
        self.reload_timer = None

    def reset(self):
        self.reload_state = STATE_IDLE
        if self.reload_timer is not None:
            self.reload_timer.cancel()

    def try_connect(self):
        print_console("Scanning for Recoil Tagger")
        tagmsg.on_message.send(self, msg='Scanning')
        self.connecting = True

    def update(self):
        if self.connecting and self.recoil_device is None:
            devices = self.scanner.scan(0.1)

        if self.connecting and self.recoil_device is not None:
            self.connecting = False
            self.tagger = Tagger(self.recoil_device, self)
            self.tagger.connect()
            tagmsg.on_connect.send(self)
        else:
            self.poll_data()

    def poll_data(self):
        if self.tagger is not None:
            if self.tagger.poll_data(1.0) is False:
                self.tagger = None
                self.recoil_device = None
                tagmsg.on_message.send(self, msg='Disconnected')
                print_console("Polling data returned false. Disconnected")

    def set_recoil(self, sender):
        self.recoil_enabled = not self.recoil_enabled
        tagmsg.on_set_recoil.send(self, recoil=self.recoil_enabled)
        message = "Recoil is %s " % ('ENABLED' if self.recoil_enabled else 'DISABLED')
        print_console(message)
        tagmsg.on_message.send(self, msg=message)

    def toggle_fire_mode(self, sender):
        if self.fire_mode is FIRE_MODE_SINGLE:
            self.fire_mode = FIRE_MODE_BURST
            message = 'Burst'
        elif self.fire_mode is FIRE_MODE_BURST:
            self.fire_mode = FIRE_MODE_AUTO
            message = 'Auto'
        else:
            self.fire_mode = FIRE_MODE_SINGLE
            message = 'Single'
        tagmsg.on_set_fire_mode.send(self, mode=self.fire_mode, ir_mode=self.shot_mode)
        tagmsg.on_message.send(self, msg=message)

    def reload_pressed(self, sender):
        if self.reload_state == STATE_IDLE:
            self.start_reload()
        else:
            print_console("Still Reloading!")

    def start_reload(self):
        self.reload_state = STATE_RELOADING
        tagmsg.on_start_reload.send(self)
        self.reload_timer = Timer(self.reload_interval, self.finish_reload)
        self.reload_timer.start()

    def finish_reload(self):
        tagmsg.on_finish_reload.send(self, ammo=self.max_ammo)
        self.reload_state = STATE_IDLE


def log_data(data_to_log):
    output = ' '.join(format(n, '02X') for n in data_to_log)
    print_console("DATA: %s" %output)


def log_bytes(original_data, bytes_to_log, struct_to_log):
    print_console('Original values: %s' % original_data)
    print_console('Format string  : %s' % struct_to_log.format)
    print_console('Uses           : %s, %s' % (struct_to_log.size, 'bytes'))
    print_console('Packed Value   : %s' % binascii.hexlify(bytes_to_log))


class ScanDelegate(DefaultDelegate):
    tagger_service = None

    def __init__(self, service):
        DefaultDelegate.__init__(self)
        self.tagger_service = service

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            name = dev.getValueText(9)
            if name is not None and name.startswith('SRG1'):
                self.tagger_service.recoil_device = dev
                print_console("Found Recoil Tagger! %s" % dev.addr)
                tagmsg.on_message.send(self, msg='Tagger Found')


class DataDelegate(DefaultDelegate):

    def __init__(self, handle):
        DefaultDelegate.__init__(self)
        self.handle = handle

    def handleNotification(self, cHandle, data):
        if cHandle == self.handle:
            data_bytes = struct.unpack("20B", data)
            tagmsg.on_telemetry_data.send(self, data=data_bytes)


class TelemetryService:
    svcUUID  = UUID(MAIN_SERVICE)
    idUUID   = UUID(ID_UUID)
    dataUUID = UUID(TELEMETRY_UUID)
    ctrlUUID = UUID(COMMAND_UUID)
    confUUID = UUID(CONFIG_UUID)
    dataCCCD = UUID(CLIENT_CONFIG)

    def __init__(self, peripheral, tagger):
        self.peripheral = peripheral
        self.service = None
        self.control = None
        self.config = None
        self.id = None
        self.data = None
        self.data_descriptor = None
        self.data_handle = 0
        self.tagger = tagger
        tagmsg.on_start_reload.connect(self.start_reload)
        tagmsg.on_finish_reload.connect(self.finish_reload)
        tagmsg.on_set_recoil.connect(self.set_recoil)
        tagmsg.on_set_fire_mode.connect(self.set_ir_config)

    def enable(self):
        if self.service is None:
            self.service = self.peripheral.getServiceByUUID(self.svcUUID)
        if self.id is None:
            self.id = self.service.getCharacteristics(self.idUUID)[0]
        if self.control is None:
            self.control = self.service.getCharacteristics(self.ctrlUUID)[0]
        if self.config is None:
            self.config = self.service.getCharacteristics(self.confUUID)[0]
        if self.data is None:
            self.data = self.service.getCharacteristics(self.dataUUID)[0]
            self.data_handle = self.data.getHandle()
            self.data_descriptor = self.data.getDescriptors(forUUID=self.dataCCCD)[0]
            self.data_descriptor.write(b"\x01\x00")
        self.peripheral.setDelegate(DataDelegate(self.data_handle))

    def start_reload(self, sender):
        data = [0x00] * 20
        data[0] = 0xF0
        data[2] = 0x02
        s = struct.Struct('20B')
        bytes = s.pack(*data)
        self.control.write(bytes)
        print_console("Starting Reload...")

    def finish_reload(self, sender, **kw):
        data = [0x00] * 20
        data[2] = 0x04
        data[6] = 0x1E # TODO - Replace with actual ammo from kw params
        s = struct.Struct('20B')
        byte_data = s.pack(*data)
        self.control.write(byte_data)
        print_console("Reload complete!")

    def set_recoil(self, sender, **kw):
        if 'recoil' not in kw:
            return
        enabled = bool(kw['recoil'])
        data = [0x00] * 20
        data[0] = 0x10
        data[2] = 0x02
        data[3] = 0x03 if enabled else 0x02
        data[4] = 0xFF
        s = struct.Struct('20B')
        data_bytes = s.pack(*data)
        self.config.write(data_bytes)

    def set_ir_config(self, sender, **kw):
        mode = FIRE_MODE_SINGLE
        cone = SHOT_MODE_INDOOR_NO_CONE
        if 'mode' in kw:
            mode = kw['mode']
        if 'ir_mode' in kw:
            cone = kw['ir_mode']
        data = [0x00] * 20
        data[2] = 0x09
        data[7] = 0xFF
        data[8] = 0xFF
        data[9] = 0x80
        data[10] = 0x02
        data[11] = 0x34
        if mode is FIRE_MODE_SINGLE:
            data[3] = 0xFE
            data[4] = 0x00
        elif mode is FIRE_MODE_BURST:
            data[3] = 0x03
            data[4] = 0x03
            if self.tagger.tagger_type is TYPE_RIFLE:
                data[9] = 0x78
        else:
            data[3] = 0xFE
            data[4] = 0x01

        if cone is SHOT_MODE_INDOOR_NO_CONE:
            data[5] = 0x19
            data[6] = 0x00
        elif cone is SHOT_MODE_OUTDOOR_WITH_CONE:
            data[5] = 0xFF
            data[6] = 0xC8
        else:
            data[5] = 0xFF
            data[6] = 0x00

        # write to the config characteristic
        s = struct.Struct('20B')
        data_bytes = s.pack(*data)
        self.config.write(data_bytes)

    def read_control(self):
        print_console(self.control.read())

    def read_id(self):
        return self.id.read()

    def disable(self):
        if self.data_descriptor is not None:
            self.data_descriptor.write(b"\x00\x00")


class IrEvent:
    event_counter = 0
    last_event_counter = 0
    sensor_source = 0
    payload = 0
    event_gun_id = 0
    event_weapon_type = 0
    event_shot_counter = 0
    event_round_counter = 0

    def __init__(self):
        pass

    @property
    def is_grenade(self):
        return (self.payload & 0x300) == 768


class Tagger:
    player_id = 0
    telemetry_count = 0
    reload_btn_count = 0
    fire_btn_count = 0
    back_btn_count = 0
    power_btn_count = 0
    battery_level = 0
    ammo_count = -1
    ir_events = [IrEvent(), IrEvent()]

    device = None
    peripheral = None
    services = None
    chars = None
    telemetry = None
    tagger_type = TYPE_PISTOL
    service = None
    ready = False

    def __init__(self, device, service):
        self.device = device
        self.service = service
        # Data from tagger
        tagmsg.on_telemetry_data.connect(self.read_telemetry)

    def reset(self, data_bytes):
        self.ready = True
        self.player_id = data_bytes[1]
        self.fire_btn_count = data_bytes[3] & 0x0f
        self.reload_btn_count = data_bytes[3] & 0xf0
        self.back_btn_count = data_bytes[4] & 0x0f
        self.power_btn_count = data_bytes[5] & 0x0f
        self.battery_level = data_bytes[7]
        self.ammo_count = data_bytes[14]
        tagmsg.on_ammo_changed.send(self, ammo=self.ammo_count)

    def connect(self):
        if self.device is not None:
            print_console("Connecting to Tagger")
            tagmsg.on_message.send(self, msg='Connecting')
            self.peripheral = Peripheral(self.device)
            self.services = self.peripheral.getServices()
            self.chars = self.peripheral.getCharacteristics()
            self.telemetry = TelemetryService(self.peripheral, self)
            self.telemetry.enable()
            self.identify_type()

    def read_telemetry(self, sender, **kw):
        if 'data' not in kw:
            return
        data_bytes = kw['data']
        self.telemetry_count += 1

        if self.ready is False:
            self.reset(data_bytes)
        if log_telemetry_data is True:
            log_data(data_bytes)

        player_id = data_bytes[1]
        buttons = data_bytes[2]
        fire_btn_count = data_bytes[3] & 0x0f
        reload_btn_count = data_bytes[3] & 0xf0
        back_btn_count = data_bytes[4] & 0x0f
        power_btn_count = data_bytes[5] & 0x0f

        self.battery_level = data_bytes[7]

        # Check input buttons
        if fire_btn_count != self.fire_btn_count:
            self.fire_btn_count = fire_btn_count
            print_console("Fire button count changed: %d" % self.telemetry_count)
            if self.ammo_count > 0:
                tagmsg.on_press_fire.send(self, empty=False)
            else:
                print_console("EMPTY")
                tagmsg.on_press_fire.send(self, empty=True)
        if reload_btn_count != self.reload_btn_count:
            print_console("Pressed reload!")
            self.reload_btn_count = reload_btn_count
            tagmsg.on_press_reload.send(self)
        if back_btn_count != self.back_btn_count:
            print_console("Pressed Back/Mic!")
            self.back_btn_count = back_btn_count
            tagmsg.on_press_action.send(self)
        if power_btn_count != self.power_btn_count:
            print_console("Pressed Power!")
            self.power_btn_count = power_btn_count
            tagmsg.on_press_power.send(self)

        # Update ammo count
        ammo_count = data_bytes[14]
        if ammo_count != self.ammo_count:
            print_console("Ammo: %d" % ammo_count)
            self.ammo_count = ammo_count
            tagmsg.on_ammo_changed.send(self, ammo=ammo_count)

        # Validate player ID hasn't changed, but ultimately the Tagger IS the authority
        if player_id != self.player_id:
            print_console("Player ID changed! Old/New: %d/%d" % (self.player_id, player_id))
            self.player_id = player_id

        byte10 = data_bytes[10]
        event_id = (byte10 & 0xF)
        if (event_id != 0) and event_id != (self.ir_events[0].last_event_counter & 0xF):
            byte8 = data_bytes[8]
            byte9 = data_bytes[9] << 8
            payload = (byte8 | byte9)
            self.ir_events[0].payload = payload
            self.ir_events[0].last_event_counter = byte10 & 0xF
            self.ir_events[0].sensor_source = byte10 >> 4

            self.ir_events[0].event_weapon_type = (payload & 0x3C0)
            self.ir_events[0].event_gun_id = (payload & 0xFC00) >> 10
            self.ir_events[0].event_shot_counter = (payload & 7) >> 0
            self.ir_events[0].event_round_counter = (payload & 0x38) >> 3
            print_console(json.dumps(vars(self.ir_events[0]), sort_keys=True, indent=4, separators=(',', ': ')))

    def identify_type(self):
        id_data = self.telemetry.read_id()
        id_bytes = struct.unpack("20B", id_data)
        if id_bytes[10] == 1:
            print_console("Found SR-12 Rogue Rifle!")
            tagmsg.on_message.send(self, msg='SR-12 Rogue Rifle')
            self.set_type(TYPE_RIFLE)
        elif id_bytes[10] == 2:
            print_console("Found RK-45 Spitfire Pistol!")
            tagmsg.on_message.send(self, msg='RK-45 Spitfire Pistol')
            self.set_type(TYPE_PISTOL)
        if log_id_data is True:
            log_data(id_bytes)

    def set_type(self, tagger_type):
        self.tagger_type = tagger_type

    def dump_services(self):
        if self.services is not None:
            for service in self.services:
                print_console("Service: ", service.uuid)
            for char in self.chars:
                print_console("Characteristic: ", char.uuid)

    def poll_data(self, time):
        if self.peripheral is not None:
            try:
                self.peripheral.waitForNotifications(1.0)
                return True
            except BTLEException:
                return False
        else:
            return False
