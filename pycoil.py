from bluepy.btle import Peripheral, Scanner, DefaultDelegate

recoilDevice = None
telemetryChar = None
commandChar = None
ConfigChar = None
MAIN_SERVICE    = "e6f59d10-8230-4a5c-b22f-c062b1d329e3"
IU_UUID         = "e6f59d11-8230-4a5c-b22f-c062b1d329e3"
TELEMETRY_UUID  = "e6f59d12-8230-4a5c-b22f-c062b1d329e3"
COMMAND_UUID    = "e6f59d13-8230-4a5c-b22f-c062b1d329e3"
CONFIG_UUID     = "e6f59d14-8230-4a5c-b22f-c062b1d329e3"

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
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        print "DATA: ", data


class TaggerService:
    def __init__(self, device):
        self.device = device
        self.peripheral = None
        self.services = None
        self.chars = None

    def connect(self):
        if self.device is not None:
            print "Connecting to Tagger"
            self.peripheral = Peripheral(self.device).withDelegate(DataDelegate())
            self.services = self.peripheral.getServices()
            self.chars = self.peripheral.getCharacteristics()

    def dump_services(self):
        if self.services is not None:
            for service in self.services:
                print "Service: ", service.uuid
            for char in self.chars:
                print "Characteristic: ", char.uuid

    def poll_data(self, time):
        if self.peripheral is not None:
            return self.peripheral.waitForNotifications(1.0)


scanner = Scanner().withDelegate(ScanDelegate())
while recoilDevice is None:
    print "Scanning for Recoil Tagger"
    devices = scanner.scan(3.0)

if recoilDevice is not None:
    tagger = TaggerService(recoilDevice)
    tagger.connect()
    tagger.dump_services()

# for dev in devices:
#    print "Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi)
#    for (adtype, desc, value) in dev.getScanData():
#        print "   %s = %s" % (desc, value)

while True:
    if tagger.poll_data(1.0):
        continue

    print "Waiting..."
