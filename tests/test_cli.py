# pylint: disable=missing-function-docstring,missing-module-docstring

import pathlib
import typing as t

from click.testing import CliRunner
import pytest
import pytest_mock

from wake import Host, Hosts
import wake.cli  # import the module to allow monkeypatching


@pytest.mark.parametrize(
    ["parsed", "count", "output"],
    [
        (None, 0, "No hosts defined"),
        ({"x": []}, 0, "No hosts defined"),
        ({"hosts": [{"name": "foo", "mac": "00:11:22:33:44:55"}]}, 1, ""),
        ({"hosts": [{"name": "foo", "mac": "ZZ:11:22:33:44:55"}]}, 0, "Invalid host (foo):"),
        ({"hosts": [{"name": "foo", "mac": "00:11:22:33:44:55", "x": 0}]}, 1, "Unknown property (foo): x"),
    ],
    ids=["no data", "missing host key", "valid configuration", "invalid configuration", "unknown property"],
)
def test_build_hosts(
    capsys: pytest.CaptureFixture,
    parsed: t.Optional[dict[str, t.Any]],
    count: int,
    output: str,
):
    result = wake.cli.build_hosts(parsed)
    captured = capsys.readouterr()

    if output:
        assert output in captured.err
    assert result.count == count


@pytest.fixture(name="hosts")
def fixture_hosts():
    data = [
        Host(name="foo", mac="00:11:22:33:44:55"),
        Host(name="bar", mac="AA:BB:CC:DD:EE:FF"),
    ]
    return Hosts(data)


@pytest.fixture(name="config_file")
def fixture_config_file(tmp_path: pathlib.Path):
    data = '[[ hosts ]]\nname = "foo"\nmac = "00:11:22:33:44:55"\n\n'
    data += '[[ hosts ]]\nname = "bar"\nmac = "AA:BB:CC:DD:EE:FF"\n'

    file = tmp_path / "config.toml"
    file.write_text(data)

    return file


@pytest.mark.parametrize(
    ["args", "output", "exit_code", "socket_exit_code"],
    [
        (["--all"], 'Waking host "foo"\nWaking host "bar"\n', 0, 0),
        (["--all", "foo"], "--all cannot be used with named hosts\n", 2, 0),
        (["xyz"], 'Unknown host "xyz"\n', 0, 0),
        (["xyz"], "No hosts to wake\n", 0, 0),
        (["foo"], 'Waking host "foo"\n', 0, 0),
        (["foo"], "Failed to send magic packet\n", 1, 1),
    ],
    ids=[
        "wake all hosts",
        "mutually exclusive parameters",
        "unknown host name",
        "no hosts to wake",
        "waking host",
        "socket fail",
    ],
)
def test_cli_host(
    mocker: pytest_mock.MockerFixture,
    config_file: pathlib.Path,
    args: list[str],
    output: str,
    exit_code: int,
    socket_exit_code: int,
):  # pylint: disable=too-many-arguments
    mocker.patch("wake.cli.socket.socket.sendto", return_value=socket_exit_code)

    runner = CliRunner()
    result = runner.invoke(wake.cli.cli, ["--config", str(config_file), "host", *args])

    assert result.exit_code == exit_code
    assert output in result.output


def test_cli_show(config_file: pathlib.Path, hosts: Hosts):
    runner = CliRunner()
    result = runner.invoke(wake.cli.cli, ["--config", str(config_file), "show"])

    assert result.output == f"\n{hosts.table}\n"
