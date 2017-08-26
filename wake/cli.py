from codecs import open
import json
import logging
from logging.handlers import RotatingFileHandler
import os

import click
from click_log import ClickHandler, ColorFormatter as ClickFormatter
from texttable import Texttable

from wake import PROGRAM_NAME, __version__
from wake.core import HostSchema, wake

CONFIG_FILE = 'wake.json'
LOG_FILE = '{0}/{1}/{1}.log'.format(os.path.expanduser('~/Library/Logs'), PROGRAM_NAME)
LOG_VERBOSITY_LEVELS = {True: logging.DEBUG, False: logging.WARNING, None: logging.INFO}

logger = logging.getLogger(PROGRAM_NAME)
logger.setLevel(logging.DEBUG)

if not os.path.isdir(os.path.dirname(LOG_FILE)):
    os.mkdir(os.path.dirname(LOG_FILE))

if not os.path.isfile(LOG_FILE):
    open(LOG_FILE, 'w').close()

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10485760, backupCount=5, encoding='utf8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(name)s [%(levelname)s]: %(message)s', '%b %d %Y %H:%M:%S'))
logger.addHandler(file_handler)

click_handler = ClickHandler()
click_handler.setFormatter(ClickFormatter())
logger.addHandler(click_handler)


def get_hosts():
    """Load, validate, and normalize configured hosts"""
    hosts = []
    raw_hosts = []

    if os.path.isfile(CONFIG_FILE):
        logger.debug('Configuration file found; using "{0}"'.format(CONFIG_FILE))
        try:
            with open(CONFIG_FILE, mode='rb', encoding='utf-8') as f:
                raw_hosts = json.loads(f.read(), encoding='utf-8')
        except ValueError:
            raise click.ClickException('Failed to parse configuration file')
    else:
        logger.debug('Configuration file not found')

    schema = HostSchema()

    for idx, raw_host in enumerate(raw_hosts):
        host, host_errors = schema.load(raw_host)
        if host_errors:
            error_name = raw_host.get('name', idx)
            error_msg = '::'.join('{0}'.format(v[0]) for k, v in host_errors.items())
            logger.warning('Invalid host "{0}": {1}'.format(error_name, error_msg))
        else:
            hosts.append(host)

    if not hosts:
        raise click.ClickException('No valid hosts defined')
    return hosts


@click.group()
@click.option('--verbose/--quiet', '-v/-q', is_flag=True, default=None, help='Specify verbosity level.')
@click.version_option()
@click.pass_context
def cli(ctx, verbose):
    if ctx.invoked_subcommand is not None:
        click_handler.setLevel(LOG_VERBOSITY_LEVELS.get(verbose, logging.INFO))
        logger.debug('{0} {1} started'.format(PROGRAM_NAME, __version__))
        logger.debug('Loading hosts')
        ctx.obj = get_hosts()


@cli.command()
@click.argument('hostnames', nargs=-1, type=click.STRING)
@click.pass_context
def host(ctx, hostnames):
    """Wake specified hosts."""
    logger.debug('Command: hosts')

    if not hostnames:
        raise click.UsageError('No host(s) specified')

    hosts_to_wake = []

    if len(hostnames) == 1 and hostnames[0].lower() == 'all':
        hosts_to_wake = ctx.obj
    else:
        for hostname in hostnames:
            host = next((h for h in ctx.obj if h['name'].lower() == hostname.lower()), None)
            if host is None:
                logger.warning('Unknown host: "{0}"'.format(hostname))
            else:
                logger.debug('Found host: "{0}"'.format(host['name']))
                hosts_to_wake.append(host)

    if not hosts_to_wake:
        raise click.ClickException('No hosts to wake')

    for host in hosts_to_wake:
        logger.info('Waking host: "{0}"'.format(host['name']))
        wake(host)


@cli.command()
@click.pass_context
def show(ctx):
    """Show all defined hosts."""
    logger.debug('Command: show')
    table = Texttable()
    table.set_cols_align(['l', 'c', 'c', 'c'])
    table.set_cols_valign(['m', 'm', 'm', 'm'])

    table.header(['Hostname', 'MAC Addr', 'IP Addr', 'Port'])
    for host in ctx.obj:
        table.add_row([host['name'], host['mac'], host['ip'], host['port']])

    click.echo(table.draw())


def show_exception(self, file=None):
    logger.error(self.message)


click.ClickException.show = show_exception
click.UsageError.show = show_exception
