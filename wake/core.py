import json
import logging
import pathlib
import socket

import click

from wake import __version__  # noqa
from wake.log import change_logger_level, setup_logger

__all__ = ['cli']


PROGRAM_NAME = 'wake'
CONFIG_FILE = f'{PROGRAM_NAME}.json'
FLAGS_QUIET = ['--quiet', '-q']
FLAGS_VERBOSE = ['--verbose', '-v']


logger = logging.getLogger(PROGRAM_NAME)
setup_logger(logger)


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
