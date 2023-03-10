# Multicast sender
# Guidance:  https://stackoverflow.com/a/1794373
import socket

MCAST_GRP = '224.0.0.251'
MCAST_PORT = 5007
MESSAGE = b'snap'
REBOOTMESSAGE = b'reboot'

# regarding socket.IP_MULTICAST_TTL
# ---------------------------------
# for all packets sent, after two hops on the network the packet will not
# be re-sent/broadcast (see https://www.tldp.org/HOWTO/Multicast-HOWTO-6.html)
MULTICAST_TTL = 1

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)

try:

    # Send data to the multicast group
    print('sending {!r}'.format(MESSAGE))
    sock.sendto(MESSAGE, (MCAST_GRP, MCAST_PORT))
    print('waiting for ack...')
    while True:
        try:
            data, server = sock.recvfrom(200)
            data = data.decode('utf8')
            if data == 'TAKEN':
               print(f'Pic Taken by {server}')

            if data != 'TAKEN' and data != "FINISHED":
               print(f'{data}')
               
            if data == 'FINISHED':
                print('Finished Uploading!')
                break

        except socket.timeout:
            print('timed out, no more responses')
            break

except:
    print("Problem sending trigger!")

finally:
    print('closing socket')
    sock.close()
