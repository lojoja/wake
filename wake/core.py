from ipaddress import AddressValueError, IPv4Address
import re
import socket
import struct

from marshmallow import Schema, post_load, validates, ValidationError
from marshmallow.fields import Integer, String


class HostSchema(Schema):
    """Schema for hosts."""
    name = String(default='', missing='')
    ip = String(default='255.255.255.255', missing='255.255.255.255')
    mac = String(default='', missing='')
    port = Integer(default=9, missing=9)

    @post_load
    def format_mac(self, data):
        """Format a MAC address as 00:11:22:33:44:55."""
        if '.' in data['mac']:
            data['mac'] = data['mac'].replace('.', '')
        elif '-' in data['mac']:
            data['mac'] = data['mac'].replace('-', ':')

        if len(data['mac']) == 12:
            data['mac'] = ':'.join(data['mac'][i:i + 2] for i in range(0, 12, 2))

        data['mac'] = data['mac'].upper()
        return data

    @validates('ip')
    def validate_ip(self, data):
        """Validates an IPv4 address."""
        try:
            IPv4Address(data)
        except AddressValueError:
            raise ValidationError('"{}" is not a valid IPv4 address.'.format(data))

    @validates('mac')
    def validate_mac(self, data):
        """Validates a MAC address."""
        regex = re.compile(
            r'^(?:(?:[0-9A-F]{2}([-:]))(?:[0-9A-F]{2}\1){4}[0-9A-F]{2}'  # 00:11:22:33:44:55 / 00-11-22-33-44-55
            r'|(?:[0-9A-F]{4}\.){2}[0-9A-F]{4}'  # 0011.2233.4455
            r'|[0-9A-F]{12})$', re.IGNORECASE)  # 001122334455

        if regex.match(data) is None:
            raise ValidationError('"{}" is not a valid MAC address.'.format(data))

    @validates('port')
    def validate_port(self, data):
        """Validates a port number."""
        if not 0 <= data <= 65535:
            raise ValidationError('"{}" is not a valid port number.'.format(data))


def wake(host):
    magic_packet = create_magic_packet(host['mac'])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(magic_packet, (host['ip'], host['port']))


def create_magic_packet(mac):
    mac = mac.replace(':', '')
    raw = ''.join(['FF' * 6, mac * 20])
    packet = b''

    for i in range(0, len(raw), 2):
        packet = b''.join([packet, struct.pack('B', int(raw[i: i + 2], 16))])

    return packet
