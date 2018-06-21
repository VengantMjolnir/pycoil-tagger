from bluepy.btle import UUID, Peripheral, Scanner, DefaultDelegate, BTLEException
import struct

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

def log_data(bytes):
    output = ' '.join(format(n,'02X') for n in bytes)
    print "DATA: ", output


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
    def __init__(self, handle):
        DefaultDelegate.__init__(self)
        self.handle = handle
        self.player_id = 0
        self.reload_btn_count = 0
        self.fire_btn_count = 0
        self.power_btn_count = 0
        self.ready = False

    def reset(self, bytes):
        self.ready = True
        self.player_id = bytes[1]
        self.fire_btn_count = bytes[3] & 0x0f
        self.reload_btn_count = bytes[3] & 0xf0
        print "Fire count: %d - Reload count: %d" % (self.fire_btn_count, self.reload_btn_count)

    def handleNotification(self, cHandle, data):
        if cHandle == self.handle:
            bytes = struct.unpack("20B", data)
            if self.ready is False:
                self.reset(bytes)
            if log_telemetry_data is True:
                log_data(bytes)

            fire_btn_count = bytes[3] & 0x0f
            reload_btn_count = bytes[3] & 0xf0
            if fire_btn_count != self.fire_btn_count:
                print "Pressed fire!"
                self.fire_btn_count = fire_btn_count
            if reload_btn_count != self.reload_btn_count:
                print "Pressed reload!"
                self.reload_btn_count = reload_btn_count


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
        self.peripheral.setDelegate(DataDelegate(self.data_handle))

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
    data = tagger.telemetry.read_id()
    bytes = struct.unpack("20B", data)
    if bytes[10] == 1:
        print "Found SR-12 Rogue Rifle!"
        tagger.set_type(TYPE_RIFLE)
    elif bytes[10] == 2:
        print "Found RK-45 Spitfire Pistol!"
        tagger.set_type(TYPE_PISTOL)
    if log_id_data is True:
        log_data(bytes)

while True:
    if tagger.poll_data(1.0) is False:
        break

print "Disconnected"
