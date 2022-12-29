"""
wake

The command-line interface for wake
"""

import logging
import pathlib
import socket

import click
from clickext import DebugCommonOptionGroup
import tomli

from wake import Host, Hosts


CONFIG_FILE = pathlib.Path("~/.config/wake.toml").expanduser()
CONFIG_HOST_PROPERTIES = ["name", "mac", "ip", "port"]

logger = logging.getLogger(__package__)


class LazyConfigGroup(DebugCommonOptionGroup):
    """A lazy-loading configuration command group.

    Checks for presence of the --help or --version option before invoking command and stores the result in
    `click.Context.obj`. This value is used in the entry point to prevent loading the configuration when the program
    will not be run.
    """

    def invoke(self, ctx):
        ctx.obj = any(value in ctx.args for value in ["--help", "--version"])
        return super().invoke(ctx)


@click.group(cls=LazyConfigGroup)
@click.version_option()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """A simple wakeonlan implementation."""
    logger.debug("%s started", __package__)

    if not ctx.invoked_subcommand or ctx.obj:
        return

    ctx.obj = get_config()


@cli.command()
@click.option("--all", "-a", "all_", is_flag=True, default=False, help="Wake all hosts.")
@click.argument("names", nargs=-1, type=click.STRING)
@click.pass_obj
def host(hosts: Hosts, all_: bool, names: tuple[str], debug: bool) -> None:  # pylint: disable=w0613
    """Wake the specified host(s).

    NAMES: The host name(s) to wake.
    """
    wake_hosts: list[Host] = []

    if all_ and names:
        raise click.BadOptionUsage("all", "--all cannot be used with named hosts")

    if all_:
        wake_hosts = hosts.get_all()
    else:
        for name in names:
            defined_host: Host | None = hosts.get(name)

            if defined_host is None:
                logger.warning('Unknown host "%s"', name)
                continue

            wake_hosts.append(defined_host)

    if not wake_hosts:
        logger.warning("No hosts to wake")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    for wake_host in wake_hosts:
        logger.info('Waking host "%s"', wake_host.name)
        result_code = sock.sendto(wake_host.magic_packet, (wake_host.ip, wake_host.port))

        if result_code > 0:
            raise click.ClickException("Failed to send magic packet")


@cli.command()
@click.pass_obj
def show(hosts: Hosts, debug: bool) -> None:  # pylint: disable=w0613
    """Show all hosts."""
    click.echo(f"\n{hosts.table}")


def get_config() -> Hosts:
    """Get the program configuration.

    Raises:
        ValueError: When the configuration file could not be parsed.
    """
    config: dict[str, list[dict[str, str | int]]] = {"hosts": []}

    try:
        config = tomli.loads(CONFIG_FILE.read_text(encoding="utf8"))
    except IOError:
        logger.warning("Failed to read configuration file")
    except (tomli.TOMLDecodeError) as exc:
        raise ValueError("Invalid configuration file") from exc

    hosts = Hosts()

    config_host_count = len(config["hosts"])

    for idx, config_host in enumerate(config["hosts"]):
        config_host_num = idx + 1
        config_host_name = config_host.get("name", "") or config_host_num

        logger.debug("Configuring host %s of %s", config_host_num, config_host_count)

        unknown_props = set(config_host.keys()).difference(CONFIG_HOST_PROPERTIES)

        for prop in unknown_props:
            del config_host[prop]
            logger.warning("Unknown property (%s): %s", config_host_name, prop)

        host_obj = Host(**config_host)

        try:
            host_obj.validate()
        except ValueError as exc:
            logger.warning("Invalid host (%s): %s", config_host_name, exc)
            continue

        hosts.add(host_obj)

    return hosts
