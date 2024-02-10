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


HostData = t.TypedDict("HostData", {"name": str, "mac": str, "ip": str, "port": int})

CONFIG_FILE = pathlib.Path("~/.config/wake.toml").expanduser()
CONFIG_HOST_PROPERTIES = ["name", "mac", "ip", "port"]

logger = logging.getLogger(__package__)
init_logging(logger)


def build_hosts(data: t.Optional[dict[str, list[HostData]]]) -> Hosts:
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
@click.version_option(package_name="py_wake_cli")
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
    hosts_to_wake: list[Host] = []

    if all_ and names:
        raise click.BadOptionUsage("all", "--all cannot be used with named hosts")

    if all_:
        hosts_to_wake = hosts.get_all()
    else:
        for name in names:
            defined_host = hosts.get(name)

            if defined_host is None:
                logger.warning('Unknown host "%s"', name)
                continue

            hosts_to_wake.append(defined_host)

    if not hosts_to_wake:
        logger.warning("No hosts to wake")
        return

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        for target in hosts_to_wake:
            logger.info('Waking host "%s"', target.name)

            try:
                sock.sendto(target.magic_packet, (target.ip, target.port))
            except OSError as exc:
                raise click.ClickException("Failed to send magic packet") from exc


@cli.command(cls=ClickextCommand)
@click.pass_obj
def show(hosts: Hosts) -> None:
    """Show all hosts."""
    click.echo(f"\n{hosts.table}")
