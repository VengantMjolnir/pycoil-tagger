import socket
import sys
import netmsg


def process_data(data, server):
    global server_address
    data = data.replace(netmsg.MESSAGE_PREFIX, '')
    if data.startswith(netmsg.JOIN):
        print 'Got a join message from other client ', server
        return True
    elif data.startswith(netmsg.SERVERREPLY):
        print 'Server replied!'
        server_address = server
        return True
    return False


address = ('192.168.0.255', 17500)
server_address = None

local_ip = netmsg.get_ip()
print "Local IP is: ", local_ip

# Create the datagram socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set a timeout so the socket does not block indefinitely when trying
# to receive data.
udp_socket.settimeout(1)
udp_socket.bind(('', 17500))

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

try:
    # Send join message
    message = netmsg.MESSAGE_PREFIX + netmsg.JOIN + netmsg.NETWORK_VERSION + "02"
    print >>sys.stderr, 'sending "%s"' % message
    sent = udp_socket.sendto(message, address)

    # Look for responses from all recipients
    count = 0
    running = True
    while running:
        try:
            data, server = udp_socket.recvfrom(128)
            handled = False
            local_message = server[0] == local_ip
            if data.startswith(netmsg.MESSAGE_PREFIX):
                if not local_message:
                    handled = process_data(data, server)
        except socket.timeout:
            count += 1
            if count > 10:
                print >>sys.stderr, 'Waiting...'
                count = 0
        else:
            if handled is False and not local_message:
                print >>sys.stderr, 'Unhandled message received "%s" from %s' % (data, server)
except KeyboardInterrupt:
    print "Caught key interrupt"
finally:
    if server_address is not None:
        print >>sys.stderr, 'sending leave message'
        message = netmsg.MESSAGE_PREFIX + netmsg.LEAVE
        udp_socket.sendto(message, address)
    print >>sys.stderr, 'closing socket'
    udp_socket.close()
