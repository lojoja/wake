from codecs import open
from ipaddress import AddressValueError, IPv4Address
import json
import logging
import os
import platform
import re
import socket
import struct

import click
from marshmallow import Schema, post_load, validates, ValidationError
from marshmallow.fields import Integer, String
from texttable import Texttable

from wake import __version__  # noqa

__all__ = ['cli']


PROGRAM_NAME = 'wake'
MIN_MACOS_VERSION = 10.10
LOG_VERBOSITY_MAP = {True: logging.DEBUG, False: logging.WARNING}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ClickFormatter(logging.Formatter):
    colors = {
        'critical': 'red',
        'debug': 'blue',
        'error': 'red',
        'exception': 'red',
        'warning': 'yellow',
    }

    def format(self, record):
        if not record.exc_info:
            level = record.levelname.lower()
            msg = record.msg
            if level in self.colors:
                prefix = click.style(
                    '{0}: '.format(level.title()), fg=self.colors[level]
                )
                if not isinstance(msg, (str, bytes)):
                    msg = str(msg)
                msg = '\n'.join(prefix + l for l in msg.splitlines())
            return msg
        return logging.Formatter.format(self, record)


class ClickHandler(logging.Handler):
    error_levels = ['critical', 'error', 'exception', 'warning']

    def emit(self, record):
        try:
            msg = self.format(record)
            err = record.levelname.lower() in self.error_levels
            click.echo(msg, err=err)
        except Exception:
            self.handleError(record)


click_handler = ClickHandler()
click_formatter = ClickFormatter()
click_handler.setFormatter(click_formatter)
logger.addHandler(click_handler)


class Host(object):
    """ Host configuration. """

    def __init__(self, schema):
        self.name = schema['name']
        self.ip = schema['ip']
        self.mac = schema['mac']
        self.port = schema['port']

    def create_magic_packet(self):
        mac = self.mac.replace(':', '')
        raw = ''.join(['FF' * 6, mac * 20])
        packet = b''

        for i in range(0, len(raw), 2):
            packet = b''.join([packet, struct.pack('B', int(raw[i : i + 2], 16))])

        return packet

    def wake(self):
        logger.info('Waking host "{0}"'.format(self.name))
        magic_packet = self.create_magic_packet()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (self.ip, self.port))


class HostSchema(Schema):
    """ Schema for hosts. """

    name = String(default='', missing='')
    ip = String(default='255.255.255.255', missing='255.255.255.255')
    mac = String(default='', missing='')
    port = Integer(default=9, missing=9)

    @post_load
    def format_mac(self, data, **kwargs):
        """ Format a MAC address as 00:11:22:33:44:55. """
        if '.' in data['mac']:
            data['mac'] = data['mac'].replace('.', '')
        elif '-' in data['mac']:
            data['mac'] = data['mac'].replace('-', ':')

        if len(data['mac']) == 12:
            data['mac'] = ':'.join(data['mac'][i : i + 2] for i in range(0, 12, 2))

        data['mac'] = data['mac'].upper()
        return data

    @validates('ip')
    def validate_ip(self, data, **kwargs):
        """ Validates an IPv4 address. """
        try:
            IPv4Address(data)
        except AddressValueError:
            raise ValidationError('"{0}" is not a valid IPv4 address.'.format(data))

    @validates('mac')
    def validate_mac(self, data, **kwargs):
        """ Validates a MAC address. """
        regex = re.compile(
            r'^(?:(?:[0-9A-F]{2}([-:]))(?:[0-9A-F]{2}\1){4}[0-9A-F]{2}'  # 00:11:22:33:44:55 / 00-11-22-33-44-55
            r'|(?:[0-9A-F]{4}\.){2}[0-9A-F]{4}'  # 0011.2233.4455
            r'|[0-9A-F]{12})$',
            re.IGNORECASE,
        )  # 001122334455

        if regex.match(data) is None:
            raise ValidationError('"{0}" is not a valid MAC address.'.format(data))

    @validates('port')
    def validate_port(self, data, **kwargs):
        """ Validates a port number. """
        if not 0 <= data <= 65535:
            raise ValidationError('"{0}" is not a valid port number.'.format(data))


class Context(object):
    def __init__(self, verbose):
        logger.debug('Gathering system and environment details')

        self.verbose = verbose
        self.macos_version = self._get_mac_version()
        self.config = None

    def _get_mac_version(self):
        version = platform.mac_ver()[0]
        version = float('.'.join(version.split('.')[:2]))  # format as e.g., '10.10'
        return version


class Configuration(object):
    """ Container for configuration. """

    filename = '{0}.json'.format(PROGRAM_NAME)
    paths = ['/usr/local/etc', '/etc']
    table = {
        'cols_align': ['l', 'c', 'c', 'c'],
        'cols_valign': ['m', 'm', 'm', 'm'],
        'header': ['Hostname', 'MAC Addr', 'IP Addr', 'Port'],
    }

    def __init__(self):
        logger.debug('Loading configuration')
        self._data = self.load(self.get_config())

    @property
    def data(self):
        return self._data

    def find_host(self, name):
        return next(
            (host for host in self.data if host.name.lower() == name.lower()), None
        )

    def get_config_file(self):
        """ Locate the configuration file to use. """
        for p in self.paths:
            file = os.path.join(p, self.filename)

            logger.debug('Trying configuration file "{0}"'.format(file))
            if os.path.isfile(file):
                logger.debug('Configuration file found, using "{0}"'.format(file))
                return file
            else:
                raise click.ClickException('Configuration file not found')

    def get_config(self):
        """ Load the configuration file data. """
        file = self.get_config_file()
        data = None

        if file:
            try:
                with open(file, mode='rb', encoding='utf-8') as f:
                    data = json.loads(f.read(), encoding='utf-8')
            except ValueError:
                raise click.ClickException('Failed to parse configuration file')
        return data

    def load(self, data):
        """ Load and validate configuration data against schema. """
        if data is None:
            return None
        elif not isinstance(data, list):
            raise click.ClickException(
                'Invalid configuration data, config root must be a list'
            )

        loaded = []
        schema = HostSchema()

        for idx, raw_host in enumerate(data):
            try:
                schema_host = schema.load(raw_host)
            except ValidationError as err:
                error_name = raw_host.get('name', idx)
                error_msg = '::'.join(
                    '{0}'.format(v[0]) for k, v in err.messages.items()
                )
                logger.warning(
                    'Invalid host definition "{0}": {1}'.format(error_name, error_msg)
                )
            else:
                loaded.append(Host(schema_host))

        if not loaded:
            raise click.ClickException('There are no valid hosts defined')

        return loaded

    def show(self):
        """ Show all hosts in a nice table. """
        logger.debug('Creating hosts table')
        table = Texttable()
        table.set_cols_align(self.table['cols_align'])
        table.set_cols_valign(self.table['cols_valign'])
        table.header(self.table['header'])

        for host in self.data:
            table.add_row([host.name, host.mac, host.ip, host.port])

        logger.debug('Displaying hosts table')
        click.echo(table.draw())


@click.group()
@click.option(
    '--verbose/--quiet',
    '-v/-q',
    is_flag=True,
    default=None,
    help='Specify verbosity level.',
)
@click.version_option()
@click.pass_context
def cli(ctx, verbose):
    logger.setLevel(LOG_VERBOSITY_MAP.get(verbose, logging.INFO))
    logger.debug('{0} started'.format(PROGRAM_NAME))

    ctx.obj = Context(verbose)

    logger.debug('Checking macOS version')
    if ctx.obj.macos_version < MIN_MACOS_VERSION:
        raise click.ClickException(
            '{0} requires macOS {1} or higher'.format(PROGRAM_NAME, MIN_MACOS_VERSION)
        )

    if ctx.invoked_subcommand is not None:
        ctx.obj.config = Configuration()


@cli.command()
@click.argument('hostnames', nargs=-1, type=click.STRING)
@click.pass_context
def host(ctx, hostnames):
    """ Wake specified hosts. """
    logger.debug('Checking "hostnames" command line argument')
    if not hostnames:
        raise click.UsageError('No host(s) specified')

    hosts_to_wake = []

    if len(hostnames) == 1 and hostnames[0].lower() == 'all':
        logger.debug('Waking all {0} defined hosts'.format(len(ctx.obj.config.data)))
        hosts_to_wake = ctx.obj.config.data
    else:
        for hostname in hostnames:
            host = ctx.obj.config.find_host(hostname)
            if host is None:
                logger.warning('Unknown host "{0}"'.format(hostname))
            else:
                logger.debug('Found host "{0}"'.format(host.name))
                hosts_to_wake.append(host)

    if not hosts_to_wake:
        raise click.ClickException('No known hosts to wake')

    for host in hosts_to_wake:
        host.wake()


@cli.command()
@click.pass_context
def show(ctx):
    """ Show all defined hosts. """
    ctx.obj.config.show()


def show_exception(self, file=None):
    logger.error(self.message)


click.ClickException.show = show_exception
click.UsageError.show = show_exception
