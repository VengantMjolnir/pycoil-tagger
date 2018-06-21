from bluepy.btle import UUID, Peripheral, Scanner, DefaultDelegate, BTLEException
import struct
from threading import Timer
import binascii

recoilDevice = None
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


def log_data(data_to_log):
    output = ' '.join(format(n, '02X') for n in data_to_log)
    print "DATA: ", output


def log_bytes(original_data, bytes_to_log, struct_to_log):
    print 'Original values:', original_data
    print 'Format string  :', struct_to_log.format
    print 'Uses           :', struct_to_log.size, 'bytes'
    print 'Packed Value   :', binascii.hexlify(bytes_to_log)


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        global recoilDevice
        if isNewDev:
            name = dev.getValueText(9)
            if name is not None and name.startswith('SRG1'):
                recoilDevice = dev
                print "Found Recoil Tagger! ", dev.addr


class DataDelegate(DefaultDelegate):
    def __init__(self, handle, telemetry):
        DefaultDelegate.__init__(self)
        self.handle = handle
        self.telemetry = telemetry
        self.ready = False
        self.reload_state = STATE_IDLE
        self.reload_interval = 3.0
        self.reload_timer = None
        # Data from tagger
        self.player_id = 0
        self.reload_btn_count = 0
        self.fire_btn_count = 0
        self.back_btn_count = 0
        self.power_btn_count = 0
        self.battery_level = 0
        self.ammo_count = 0

    def reset(self, bytes):
        self.ready = True
        self.player_id = bytes[1]
        self.fire_btn_count = bytes[3] & 0x0f
        self.reload_btn_count = bytes[3] & 0xf0
        self.back_btn_count = bytes[4] & 0x0f
        self.power_btn_count = bytes[5] & 0x0f
        self.battery_level = bytes[7]
        self.ammo_count = bytes[14]
        if self.reload_timer is not None:
            self.reload_timer.cancel()

    def start_reload(self):
        if self.reload_state == STATE_IDLE:
            self.reload_state = STATE_RELOADING
            self.telemetry.start_reload()
            self.reload_timer = Timer(self.reload_interval, self.finish_reload)
            self.reload_timer.start()
        else:
            print "Still Reloading!"

    def finish_reload(self):
        self.telemetry.finish_reload(30)
        self.reload_state = STATE_IDLE

    def handleNotification(self, cHandle, data):
        if cHandle == self.handle:
            bytes = struct.unpack("20B", data)
            if self.ready is False:
                self.reset(bytes)
            if log_telemetry_data is True:
                log_data(bytes)

            player_id = bytes[1]
            fire_btn_count = bytes[3] & 0x0f
            reload_btn_count = bytes[3] & 0xf0
            back_btn_count = bytes[4] & 0x0f
            power_btn_count = bytes[5] & 0x0f

            self.battery_level = bytes[7]
            ammo_count = bytes[14]

            # Update ammo count first
            if ammo_count != self.ammo_count:
                print "Ammo: ", ammo_count
                self.ammo_count = ammo_count

            # Check input buttons
            if fire_btn_count != self.fire_btn_count:
                print "Pressed fire!"
                self.fire_btn_count = fire_btn_count
                if self.ammo_count <= 0:
                    print "Ammo: EMPTY"
            if reload_btn_count != self.reload_btn_count:
                print "Pressed reload!"
                self.reload_btn_count = reload_btn_count
                self.start_reload()
            if back_btn_count != self.back_btn_count:
                print "Pressed Back/Mic!"
                self.back_btn_count = back_btn_count
            if power_btn_count != self.power_btn_count:
                print "Pressed Power!"
                self.power_btn_count = power_btn_count

            # Validate player ID hasn't changed, but ultimately the Tagger IS the authority
            if player_id != self.player_id:
                print"Player ID changed! Old/New: %d/%d" % (self.player_id, player_id)
                self.player_id = player_id


class TelemetryService:
    svcUUID  = UUID(MAIN_SERVICE)
    idUUID   = UUID(ID_UUID)
    dataUUID = UUID(TELEMETRY_UUID)
    ctrlUUID = UUID(COMMAND_UUID)
    dataCCCD = UUID(CLIENT_CONFIG)

    def __init__(self, peripheral):
        self.peripheral = peripheral
        self.service = None
        self.control = None
        self.id = None
        self.data = None
        self.config = None
        self.data_handle = 0

    def enable(self):
        if self.service is None:
            self.service = self.peripheral.getServiceByUUID(self.svcUUID)
        if self.id is None:
            self.id = self.service.getCharacteristics(self.idUUID)[0]
        if self.control is None:
            self.control = self.service.getCharacteristics(self.ctrlUUID)[0]
        if self.data is None:
            self.data = self.service.getCharacteristics(self.dataUUID)[0]
            self.data_handle = self.data.getHandle()
            self.config = self.data.getDescriptors(forUUID=self.dataCCCD)[0]
            self.config.write(b"\x01\x00")
        self.peripheral.setDelegate(DataDelegate(self.data_handle, self))

    def start_reload(self):
        data = [0x00] * 20
        data[0] = 0xF0
        data[2] = 0x02
        s = struct.Struct('20B')
        bytes = s.pack(*data)
        self.control.write(bytes)
        print "Starting Reload..."

    def finish_reload(self, ammo):
        data = [0x00] * 20
        data[2] = 0x04
        data[6] = 0x1E
        s = struct.Struct('20B')
        bytes = s.pack(*data)
        self.control.write(bytes)
        print "Reload complete!"

    def read_control(self):
        return self.control.read()

    def read_id(self):
        return self.id.read()

    def disable(self):
        if self.config is not None:
            self.config.write(b"\x00\x00")


class TaggerService:
    def __init__(self, device):
        self.device = device
        self.peripheral = None
        self.services = None
        self.chars = None
        self.telemetry = None
        self.tagger_type = TYPE_PISTOL

    def connect(self):
        if self.device is not None:
            print "Connecting to Tagger"
            self.peripheral = Peripheral(self.device)
            self.services = self.peripheral.getServices()
            self.chars = self.peripheral.getCharacteristics()
            self.telemetry = TelemetryService(self.peripheral)
            self.telemetry.enable()

    def set_type(self, type):
        self.tagger_type = type

    def dump_services(self):
        if self.services is not None:
            for service in self.services:
                print "Service: ", service.uuid
            for char in self.chars:
                print "Characteristic: ", char.uuid

    def poll_data(self, time):
        if self.peripheral is not None:
            try:
                self.peripheral.waitForNotifications(1.0)
                return True
            except BTLEException:
                return False
        else:
            return False


scanner = Scanner().withDelegate(ScanDelegate())
while recoilDevice is None:
    print "Scanning for Recoil Tagger"
    devices = scanner.scan(3.0)

if recoilDevice is not None:
    tagger = TaggerService(recoilDevice)
    tagger.connect()
    id_data = tagger.telemetry.read_id()
    id_bytes = struct.unpack("20B", id_data)
    if id_bytes[10] == 1:
        print "Found SR-12 Rogue Rifle!"
        tagger.set_type(TYPE_RIFLE)
    elif id_bytes[10] == 2:
        print "Found RK-45 Spitfire Pistol!"
        tagger.set_type(TYPE_PISTOL)
    if log_id_data is True:
        log_data(id_bytes)

while True:
    if tagger.poll_data(1.0) is False:
        break

print "Disconnected"
