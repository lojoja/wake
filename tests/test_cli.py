# pylint: disable=missing-module-docstring,missing-function-docstring

from pathlib import Path
import typing as t
from unittest.mock import call

from click.testing import CliRunner
import pytest
from pytest_mock import MockerFixture

from wake.wake import Hosts
from wake.cli import build_hosts, cli


@pytest.mark.parametrize("name", ["foo", ""])
def test_build_hosts_invalid(capsys: pytest.CaptureFixture, name: str):
    err_name = name if name else "#1"  # Unnamed hosts should be referenced by their position in the config file
    err_prop = "name" if not name else "MAC Address"

    hosts = build_hosts({"hosts": [{"name": name, "mac": f"AA:BB:CC:DD:EE:FF{'x' if name else ''}"}]})  # type: ignore
    assert hosts.count == 0
    assert capsys.readouterr().err == f"Warning: Invalid host ({err_name}): ['Invalid {err_prop}']\n"


@pytest.mark.parametrize("data", [None, {}])
def test_build_hosts_no_hosts_defined(capsys: pytest.CaptureFixture, data: t.Optional[dict]):
    hosts = build_hosts(data)
    assert hosts.count == 0
    assert capsys.readouterr().err == "Warning: No hosts defined\n"


def test_build_hosts_unknown_property(capsys: pytest.CaptureFixture):
    hosts = build_hosts({"hosts": [{"name": "foo", "mac": "AA:BB:CC:DD:EE:FF", "x": "y"}]})  # type: ignore
    assert hosts.count == 1
    assert capsys.readouterr().err == "Warning: Unknown property (foo): x\n"


def test_build_hosts_valid(capsys: pytest.CaptureFixture):
    hosts = build_hosts({"hosts": [{"name": "foo", "mac": "AA:BB:CC:DD:EE:FF"}]})  # type: ignore
    assert hosts.count == 1
    assert capsys.readouterr().err == ""


def test_cli_version(config: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "--version"])
    assert result.output.startswith("cli, version")


@pytest.mark.parametrize("short_opts", [True, False])
@pytest.mark.parametrize("verbose", [True, False])
def test_cli_verbosity(caplog: pytest.LogCaptureFixture, config: Path, verbose: bool, short_opts: bool):
    CliRunner().invoke(
        cli, ["-c", str(config), "show", "--help", ("-v" if short_opts else "--verbose") if verbose else ""]
    )
    assert ("DEBUG" in caplog.text) is verbose


@pytest.mark.parametrize("short_opts", [True, False])
@pytest.mark.parametrize("all_hosts", [True, False])
def test_host(mocker: MockerFixture, config: Path, hosts: Hosts, all_hosts: bool, short_opts: bool):
    mock_sendto = mocker.patch("wake.cli.socket.socket.sendto")
    target_hosts = hosts.get_all()

    if all_hosts:
        arg = "-a" if short_opts else "--all"
    else:
        arg = target_hosts[0].name
        del target_hosts[-1]

    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "host", arg])

    assert result.exit_code == 0
    assert result.output == "\n".join([f'Waking host "{host.name}"' for host in target_hosts]) + "\n"
    mock_sendto.assert_has_calls([call(host.magic_packet, (host.ip, host.port)) for host in target_hosts])


@pytest.mark.parametrize("all_hosts", [True, False])
def test_host_no_hosts_to_wake(mocker: MockerFixture, config: Path, all_hosts: bool):
    missing_config_file = f"{config}x"  # Change file name so config is not found
    mock_sendto = mocker.patch("wake.cli.socket.socket.sendto")

    runner = CliRunner()
    result = runner.invoke(cli, ["-c", missing_config_file, "host", "--all" if all_hosts else "x"])

    assert result.exit_code == 0
    assert result.output.endswith(
        "\n" + ("" if all_hosts else 'Warning: Unknown host "x"\n') + "Warning: No hosts to wake\n"
    )
    mock_sendto.assert_not_called()


def test_hosts_known_and_unknown_host(mocker: MockerFixture, config: Path, hosts: Hosts):
    mock_sendto = mocker.patch("wake.cli.socket.socket.sendto")
    known_host = hosts.get_all()[0]

    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "host", known_host.name, "x"])

    assert result.exit_code == 0
    assert result.output == f'Warning: Unknown host "x"\nWaking host "{known_host.name}"\n'
    mock_sendto.assert_called_once_with(known_host.magic_packet, (known_host.ip, known_host.port))


def test_host_mutually_exclusive_params(mocker: MockerFixture, config: Path):
    mock_sendto = mocker.patch("wake.cli.socket.socket.sendto")

    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "host", "--all", "x"])

    assert result.output.endswith("\nError: --all cannot be used with named hosts\n")
    mock_sendto.assert_not_called()


def test_host_send_fails(mocker: MockerFixture, config: Path, hosts: Hosts):
    mock_sendto = mocker.patch("wake.cli.socket.socket.sendto", side_effect=OSError)
    target_host = hosts.get_all()[0]

    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "host", target_host.name])

    assert result.exit_code == 1
    assert result.output == f'Waking host "{target_host.name}"\nError: Failed to send magic packet\n'
    mock_sendto.assert_called_once_with(target_host.magic_packet, (target_host.ip, target_host.port))


def test_show(config: Path, hosts: Hosts):
    runner = CliRunner()
    result = runner.invoke(cli, ["-c", str(config), "show"])
    assert result.output == f"\n{hosts.table}\n"
