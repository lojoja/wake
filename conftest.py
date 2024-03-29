# pylint: disable=missing-module-docstring,missing-function-docstring

from pathlib import Path

import pytest

from wake.wake import Host, Hosts


@pytest.fixture(name="config", scope="session")
def config_fixture(tmp_path_factory: pytest.TempPathFactory, hosts: Hosts) -> Path:
    """A config file with the `hosts` fixture data."""
    data = ""

    for host in hosts.get_all():
        data += f'[[ hosts ]]\nname = "{host.name}"\nmac = "{host.mac}"\n'

    file = tmp_path_factory.getbasetemp() / "wake.toml"
    file.write_text(data, encoding="utf8")

    return file


@pytest.fixture(name="hosts", scope="session")
def hosts_fixture() -> Hosts:
    """Defined hosts for CLI tests."""
    hosts = [Host(name="foo", mac="00:11:22:33:44:55"), Host(name="bar", mac="AA:BB:CC:DD:EE:FF")]
    return Hosts(hosts)
