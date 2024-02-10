# pylint: disable=missing-module-docstring,missing-function-docstring,protected-access

from contextlib import nullcontext as does_not_raise
import typing as t

import pytest

from wake.wake import Host, Hosts


def test_host_name():
    assert Host(name="foo").name == "foo"


def test_host_mac():
    assert Host(mac="AA:BB:CC:00:11:22").mac == "AA:BB:CC:00:11:22"


def test_host_ip():
    assert Host(ip="127.0.0.1").ip == "127.0.0.1"


def test_host_port():
    assert Host(port=1).port == 1


def test_host_magic_packet():
    packet = Host(mac="AA:BB:CC:00:11:22").magic_packet
    assert packet == (
        b"\xff\xff\xff\xff\xff\xff"
        b"\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22"
        b"\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22"
        b"\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22"
        b"\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22\xaa\xbb\xcc\x00\x11\x22"
    )


@pytest.mark.parametrize(
    "value", ["aa:bb:cc:00:11:22", "aa-bb-cc-00-11-22", "aa.bb.cc.00.11.22", "aabb.cc00.1122", "aabbcc001122"]
)
def test_host_mac_format(value: str):
    host = Host(mac=value)
    assert host.mac == "AA:BB:CC:00:11:22"


@pytest.mark.parametrize("valid", [True, False])
def test_host_validate(valid: bool):
    error_msg = str(["Invalid IPv4 Address", "Invalid MAC Address", "Invalid name", "Invalid port"])

    if valid:
        data = {"ip": "127.0.0.1", "mac": "AA:BB:CC:00:11:22", "name": "foo", "port": 9}
    else:
        data = {"ip": "127.0.0.x", "mac": "ZZ:BB:CC:00:11:22", "name": "", "port": -1}

    host = Host(**data)
    context = does_not_raise() if valid else pytest.raises(ValueError, match=error_msg)

    with context:
        host.validate()


@pytest.mark.parametrize("valid", [True, False])
def test_host__validate_ip(valid: bool):
    host = Host(ip="127.0.0.1" if valid else "127.0.0.x")
    context = does_not_raise() if valid else pytest.raises(ValueError, match="Invalid IPv4 Address")

    with context:
        host._validate_ip()


@pytest.mark.parametrize(
    ["value", "valid"], [("AA:BB:CC:00:11:22", True), ("ZZ:BB:CC:00:11:22", False), ("AA:BB:CC:00:11:22A", False)]
)
def test_host__validate_mac(value: str, valid: bool):
    host = Host(mac=value)
    context = does_not_raise() if valid else pytest.raises(ValueError, match="Invalid MAC Address")

    with context:
        host._validate_mac()


@pytest.mark.parametrize("valid", [True, False])
def test_host__validate_name(valid: bool):
    host = Host(name="foo" if valid else "")
    context = does_not_raise() if valid else pytest.raises(ValueError, match="Invalid name")

    with context:
        host._validate_name()


@pytest.mark.parametrize(["value", "valid"], [(-1, False), (0, True), (7, True), (65536, False)])
def test_host__validate_port(value: int, valid: bool):
    host = Host(port=value)
    context = does_not_raise() if valid else pytest.raises(ValueError, match="Invalid port")

    with context:
        host._validate_port()


@pytest.mark.parametrize("value", [None, [], Host(), [Host()]])
def test_hosts(value: t.Optional[Host | list[Host]]):
    hosts = Hosts(value)

    if value is None:
        assert hosts.count == 0
    elif isinstance(value, Host):
        assert hosts.count == 1
    else:
        assert hosts.count == len(value)


def test_hosts_count():
    assert Hosts([Host(), Host()]).count == 2


def test_hosts_table():
    host_data = [Host(name="foo", mac="AA:BB:CC:00:11:22"), Host(name="bar", mac="DD:EE:FF:33:44:55")]
    hosts = Hosts(host_data)
    result = hosts.table

    assert result == (
        "Hostname    MAC Address        IP Address         Port\n"
        "----------  -----------------  ---------------  ------\n"
        "foo         AA:BB:CC:00:11:22  255.255.255.255       9\n"
        "bar         DD:EE:FF:33:44:55  255.255.255.255       9"
    )


def test_hosts_add():
    hosts = Hosts(Host())
    hosts.add(Host())
    assert hosts.count == 2


@pytest.mark.parametrize("name", ["foo", "FOO", "bar"])
def test_hosts_get(name: str):
    host = Host(name="foo")
    assert Hosts(host).get(name) == (None if name == "bar" else host)


def test_hosts_get_all():
    values = [Host(), Host()]
    assert Hosts(values).get_all() == values
