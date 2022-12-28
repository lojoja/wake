"""
wake

A simple wakeonlan implementation.
"""

from ipaddress import AddressValueError, IPv4Address
import re
import struct
import typing as t

from tabulate import tabulate

# 00:11:22:33:44:55 / 00-11-22-33-44-55
# 0011.2233.4455
# 001122334455

MAC_PATTERN = re.compile(r"^(?:[0-9A-F]{2}([:]))(?:[0-9A-F]{2}\1){4}[0-9A-F]{2}", re.IGNORECASE)
MAC_REPLACE = [".", "-", ":"]
MAC_SEPARATOR = ":"


class Host:
    """A network host."""

    def __init__(
        self, name: str = "", mac: str = "", ip: str = "255.255.255.255", port: int = 9  #  pylint: disable=c0103
    ):
        self._name = name
        self._ip = ip
        self._port = port
        self._validated: bool = False

        for char in MAC_REPLACE:
            if char in mac:
                mac = mac.replace(char, "")

        mac = MAC_SEPARATOR.join(mac[i : i + 2] for i in range(0, 12, 2))

        self._mac = mac

    @property
    def ip(self) -> str:  # pylint: disable=c0103
        """The host IPv4 address."""
        return self._ip

    @property
    def mac(self) -> str:
        """The host MAC address."""
        return self._mac.upper()

    @property
    def name(self) -> str:
        """The host name."""
        return self._name

    @property
    def port(self) -> int:
        """The host WoL port."""
        return self._port

    @property
    def magic_packet(self) -> bytes:
        """The host magic packet."""

        mac = self.mac.replace(MAC_SEPARATOR, "")
        data = f'{"FF" * 6}{mac * 20}'
        packet = b""

        for i in range(0, len(data), 2):
            packet = b"".join([packet, struct.pack("B", int(data[i : i + 2], 16))])

        return packet

    def validate(self) -> None:
        """Validate a host.

        Call all object methods that begin with '_validate_' to validate host. Validation methods should raise
        `ValueError` on an error. All errors will be raised together after every validation method has run.

        Raises:
            ValueError: One or more values failed validation.
        """
        errors = []

        for attr in dir(self):
            if attr.startswith("_validate_") and callable(getattr(self, attr)):
                try:
                    getattr(self, attr)()
                except ValueError as exc:
                    errors.append(str(exc))

        if errors:
            raise ValueError(errors)

    def _validate_ip(self) -> None:
        try:
            IPv4Address(self.ip)
        except AddressValueError as exc:
            raise ValueError("Invalid IPv4 Address") from exc

    def _validate_mac(self) -> None:
        match = MAC_PATTERN.match(self._mac)
        if not match:
            raise ValueError("Invalid MAC Address")

    def _validate_name(self) -> None:
        if self.name == "":
            raise ValueError("Invalid name")

    def _validate_port(self) -> None:
        if not 0 <= self.port <= 65535:
            raise ValueError("Invalid port")


class Hosts:
    """A collection of network hosts.

    Attributes:
        _hosts: The hosts in the collection.
        _columns: The names of the columns for the hosts table.
        _fields: The `Host` attributes for each column in the hosts table.

    Args:
        hosts: Zero or more `Host`s to add to the collection.
    """

    _hosts: list[Host] = []
    _columns: list[str] = ["Hostname", "MAC Address", "IP Address", "Port"]
    _fields: list[str] = ["name", "mac", "ip", "port"]

    def __init__(self, hosts: t.Optional[Host | list[Host]] = None):
        if hosts is None:
            hosts = []
        self._hosts = [hosts] if isinstance(hosts, Host) else hosts

    @property
    def count(self) -> int:
        """The number of hosts in the collection."""
        return len(self._hosts)

    @property
    def table(self) -> str:
        """Table display of all hosts in the collection."""
        data = [self._columns]

        for host in self._hosts:
            row = []

            for field in self._fields:
                row.append(getattr(host, field))

            data.append(row)

        return tabulate(data, headers="firstrow", tablefmt="simple")

    def add(self, host: Host) -> None:
        """Add a host to the collection."""
        self._hosts.append(host)

    def get(self, name: str) -> t.Optional[Host]:
        """Get a host by name.

        Args:
            name: The name of the host to get.
        """
        return next((host for host in self._hosts if host.name.lower() == name.lower()), None)

    def get_all(self) -> list[Host]:
        """Get all hosts in the collection."""
        return self._hosts
