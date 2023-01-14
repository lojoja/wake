"""
wake

The command-line interface for wake
"""

import logging
import pathlib
import socket
import typing as t

import click
from clickext import ClickextCommand, ClickextGroup, config_option, init_logging, verbose_option

from .wake import Host, Hosts


CONFIG_FILE = pathlib.Path("~/.config/wake.toml").expanduser()
CONFIG_HOST_PROPERTIES = ["name", "mac", "ip", "port"]

logger = logging.getLogger(__package__)
init_logging(logger)


def build_hosts(data: t.Optional[dict[str, list[dict[str, t.Union[str, int]]]]]) -> Hosts:
    """Create hosts from configuration file data.

    Arguments:
        data: The parsed configuration file data.

    Raises:
        ValueError: When the configuration file could not be parsed.
    """

    hosts = Hosts()

    if data is None or "hosts" not in data:
        logger.warning("No hosts defined")
        return hosts

    count = len(data["hosts"])

    for idx, host_data in enumerate(data["hosts"]):
        num = idx + 1
        name = host_data.get("name", f"#{num}")

        logger.debug("Configuring host %s of %s", num, count)

        unknown_props = set(host_data.keys()).difference(CONFIG_HOST_PROPERTIES)

        for prop in unknown_props:
            del host_data[prop]
            logger.warning("Unknown property (%s): %s", name, prop)

        host_obj = Host(**host_data)

        try:
            host_obj.validate()
        except ValueError as exc:
            logger.warning("Invalid host (%s): %s", name, exc)
            continue

        hosts.add(host_obj)

    return hosts


@click.group(cls=ClickextGroup, global_opts=["config", "verbose"])
@click.version_option()
@config_option(CONFIG_FILE, processor=build_hosts)
@verbose_option(logger)
def cli() -> None:
    """A simple wakeonlan implementation."""
    logger.debug("%s started", __package__)


@cli.command(cls=ClickextCommand)
@click.option("--all", "-a", "all_", is_flag=True, default=False, help="Wake all hosts.")
@click.argument("names", nargs=-1, type=click.STRING)
@click.pass_obj
def host(hosts: Hosts, all_: bool, names: tuple[str]) -> None:
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
            defined_host: t.Optional[Host] = hosts.get(name)

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


@cli.command(cls=ClickextCommand)
@click.pass_obj
def show(hosts: Hosts) -> None:
    """Show all hosts."""
    click.echo(f"\n{hosts.table}")
