from ipaddress import AddressValueError, IPv4Address
import json
import logging
import pathlib
import re
import socket
import struct

import click
from tabulate import tabulate

from wake import __version__  # noqa
from wake.log import change_logger_level, setup_logger

__all__ = ['cli']


PROGRAM_NAME = 'wake'
CONFIG_FILE = f'{PROGRAM_NAME}.json'
FLAGS_QUIET = ['--quiet', '-q']
FLAGS_VERBOSE = ['--verbose', '-v']
MAC_PATTERN = re.compile(
    r'^(?:(?:[0-9A-F]{2}([-:]))(?:[0-9A-F]{2}\1){4}[0-9A-F]{2}'  # 00:11:22:33:44:55 / 00-11-22-33-44-55
    r'|(?:[0-9A-F]{4}\.){2}[0-9A-F]{4}'  # 0011.2233.4455
    r'|[0-9A-F]{12})$',  # 001122334455
    re.IGNORECASE,
)

logger = logging.getLogger(PROGRAM_NAME)
setup_logger(logger)


class Host(object):
    """A network host.

    Args:
        kwargs: Catchall for unknown parameters. This is included to prevent errors instantiating `wake.core.Host`
            objects from unverified data which may contain unknown "key:value" pairs. All values are silently ignored.

    """
    def __init__(self, name=None, ip=None, mac=None, port=None, **kwargs):
        self.name = name
        self.ip = ip
        self.mac = mac
        self.port = port

    @property
    def ip(self):
        """The host IPv4 address. Default is '255.255.255.255'"""
        return self._ip

    @ip.setter
    def ip(self, value):
        self._ip = value or '255.255.255.255'

    @property
    def mac(self):
        """The host MAC address, without separators."""
        return self._mac

    @mac.setter
    def mac(self, value):
        try:
            match = MAC_PATTERN.match(value)
        except TypeError:
            match = None
            value = None

        if match:
            for char in ('.', '-', ':'):
                value = value.replace(char, '')

            value = value.upper()

        self._mac = value

    @property
    def mac_formatted(self):
        """The host MAC address, with ':' separators."""
        return ':'.join(self.mac[i:i+2] for i in range(0, 12, 2)) if self.mac else None

    @property
    def magic_packet(self):
        """The magic packet that wakes the host."""
        packet = None

        if self.mac:
            data = f'{"FF" * 6}{self.mac * 20}'
            packet = b''

            for i in range(0, len(data), 2):
                packet = b''.join([packet, struct.pack('B', int(data[i:i+2], 16))])

        return packet

    @property
    def name(self):
        """The host name."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value or None

    @property
    def port(self):
        """The host WoL port. Default: is '9'"""
        return self._port

    @port.setter
    def port(self, value):
        self._port = value or 9

    @property
    def summary(self):
        """A `list` of host properties to use in table displays."""
        return [self.name, self.mac_formatted, self.ip, self.port]

    def validate(self):
        """Validate a host.

        Call all object methods that begin with '_validate_' to validate host. Validation methods should raise
        `ValueError` on an error. All errors will be raised together after every validation method has run.

        Raises:
            ValueError: One or more values failed validation.

        """
        errors = []

        for attr in dir(self):
            if attr.startswith('_validate_') and callable(getattr(self, attr)):
                try:
                    getattr(self, attr)()
                except ValueError as e:
                    errors.append(str(e))

        if errors:
            raise ValueError(errors)

    def _validate_ip(self):
        try:
            IPv4Address(self.ip)
        except AddressValueError:
            raise ValueError('Invalid IPv4 Address')

    def _validate_mac(self):
        if self.mac is None:
            raise ValueError('Invalid MAC Address')

    def _validate_name(self):
        if self.name is None:
            raise ValueError('Invalid name')

    def _validate_port(self):
        if not 0 <= self.port <= 65535:
            raise ValueError('Invalid port')


def load_config():
    """Load the configuration file.

    Returns:
        A `list` of `wake.core.Host` objects.

    Raises:
        IOError: A configuration file was not found.
        ValueError: No valid host definitions were found.

    """
    logger.debug('Started loading configuration')

    paths = ('', '/usr/local/etc', '/etc')

    config = None

    for path in paths:
        file = pathlib.Path(path, CONFIG_FILE)

        if file.exists():
            logger.debug(f'Using configuration file "{file.absolute()}"')
            config = file
            break

    if config is None:
        raise IOError('Stopped loading configuration, configuration file not found')

    data = json.load(file.open())

    hosts = []

    for idx, raw_host in enumerate(data):
        host = Host(**raw_host)

        try:
            host.validate()
        except ValueError as e:
            logger.warning(f'Invalid host "{raw_host.get("name", f"#{idx+1}")}": {e}')
            continue

        hosts.append(host)

    if not hosts:
        raise ValueError('Stopped loading configuration, no valid hosts found')

    logger.debug('Finished loading configuration')

    return hosts


class CLIGroup(click.Group):
    """CLI command group.

    Collects common options to parse at group level and handles exceptions from subcommands.

    """
    def invoke(self, ctx):
        ctx.obj = tuple(ctx.args)
        ctx.args = tuple(arg for arg in ctx.args if arg not in FLAGS_QUIET + FLAGS_VERBOSE)

        try:
            super(CLIGroup, self).invoke(ctx)
        except click.exceptions.Exit:
            pass
        except click.UsageError as e:
            raise click.ClickException(e) from e
        except (EOFError, KeyboardInterrupt, click.Abort, click.ClickException):
            raise
        except Exception as e:
            raise click.ClickException(e) from e


@click.group(cls=CLIGroup)
@click.option(f'{FLAGS_VERBOSE[0]}/{FLAGS_QUIET[0]}', f'{FLAGS_VERBOSE[1]}/{FLAGS_QUIET[1]}',
              is_flag=True, default=None, help='Specify verbosity level.')
@click.version_option()
@click.pass_context
def cli(ctx, verbose):
    if verbose is None and ctx.invoked_subcommand:
        if any(arg in FLAGS_VERBOSE for arg in ctx.obj):
            verbose = True
        elif any(arg in FLAGS_QUIET for arg in ctx.obj):
            verbose = False

    change_logger_level(logger, verbose)
    logger.debug(f'{PROGRAM_NAME} started')

    if ctx.invoked_subcommand:
        ctx.obj = load_config()


@cli.command()
@click.argument('names', nargs=-1, type=click.STRING)
@click.option('--all', '-a', 'all_', is_flag=True, default=False, help='Wake all hosts.')
@click.pass_context
def host(ctx, all_, names):
    """Wake the specified host(s).

    NAMES: The host name(s) to wake.

    """
    logger.debug('Started waking hosts')

    hosts = []

    if all_:
        if names:
            raise click.UsageError('"--all" cannot be used with named hosts')
        else:
            hosts = ctx.obj
    else:
        if not names:
            raise click.UsageError('No host(s) specified')

        for name in names:
            host = next((host for host in ctx.obj if host.name.lower() == name.lower()), None)

            if host is None:
                logger.warning(f'Unknown host "{name}"')
            else:
                hosts.append(host)

    if not hosts:
        raise ValueError('Stopped waking hosts, no matching hosts found')

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    for host in hosts:
        logger.info(f'Waking host "{host.name}"')
        sock.sendto(host.magic_packet, (host.ip, host.port))

    logger.debug('Finished waking hosts')


@cli.command()
@click.pass_context
def show(ctx):
    """Show all hosts."""
    logger.debug('Started showing hosts')

    data = [['Hostname', 'MAC Address', 'IP Address', 'Port']]

    for host in ctx.obj:
        data.append(host.summary)

    click.echo(f'\n{tabulate(data, headers="firstrow", tablefmt="simple")}')

    logger.debug('Finished showing hosts')


def show_exception(self, file=None):
    logger.error(self.message)


click.ClickException.show = show_exception
click.UsageError.show = show_exception
