# pylint: disable=c0114,c0116

import pytest

from wake import Host, Hosts


def test_host():
    host = Host(name="foo", mac="AA:BB:CC:00:11:22", ip="127.0.0.1", port=1)

    assert host.name == "foo"
    assert host.mac == "AA:BB:CC:00:11:22"
    assert host.ip == "127.0.0.1"
    assert host.port == 1
    assert host.magic_packet == (
        b"\xff\xff\xff\xff\xff\xff"
        b'\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"'
        b'\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"'
        b'\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"'
        b'\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"'
        b'\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"\xaa\xbb\xcc\x00\x11"'
    )


@pytest.mark.parametrize(
    ["mac"],
    [("aa:bb:cc:00:11:22",), ("aa-bb-cc-00-11-22",), ("aa.bb.cc.00.11.22",), ("aabb.cc00.1122",), ("aabbcc001122",)],
)
def test_host_mac_format(mac: str):
    host = Host(mac=mac)

    assert host.mac == "AA:BB:CC:00:11:22"


@pytest.mark.parametrize(
    ["name", "mac", "ip", "port", "valid"],
    [
        ("foo", "AA:BB:CC:00:11:22", "127.0.0.1", 9, True),
        ("", "AA:BB:CC:00:11:22", "127.0.0.1", 9, False),
        ("foo", "ZZ:BB:CC:00:11:22", "127.0.0.1", 9, False),
        ("foo", "AA:BB:CC:00:11:22", "127.0.0.x", 9, False),
        ("foo", "AA:BB:CC:00:11:22", "127.0.0.x", -1, False),
    ],
)
def test_host_validation(name: str, mac: str, ip: str, port: int, valid: bool):  # pylint: disable=c0103
    host = Host(name, mac, ip, port)

    if valid:
        assert host.validate() is None
    else:
        with pytest.raises(ValueError):
            host.validate()


@pytest.mark.parametrize(["host_data", "count"], [(None, 0), (Host(), 1), ([Host(), Host()], 2)])
def test_hosts(host_data: Host | list[Host] | None, count: int):
    hosts = Hosts(host_data)

    assert hosts.count == count


def test_hosts_add_host():
    hosts = Hosts()
    hosts.add(Host())

    assert hosts.count == 1


@pytest.mark.parametrize(["name", "search_name", "expect_type"], [("foo", "foo", Host()), ("foo", "bar", None)])
def test_hosts_get_host(name: str, search_name: str, expect_type: Host | None):
    host = Host(name=name)
    hosts = Hosts(host)

    result = hosts.get(search_name)

    assert type(result) == type(expect_type)


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
