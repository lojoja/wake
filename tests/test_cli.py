# pylint: disable=c0114,c0116

from click.testing import CliRunner
import pytest

from wake import Host, Hosts
import wake.cli  # import the module to allow monkeypatching


def test_config_read_error(capsys, mocker):
    mocker.patch("wake.cli.pathlib.Path.read_text", side_effect=IOError)

    result = wake.cli.get_config()
    captured = capsys.readouterr()

    assert "Failed" in captured.err
    assert isinstance(result, Hosts)
    assert result.count == 0


def test_config_parse_error(mocker):
    mocker.patch("wake.cli.pathlib.Path.read_text", return_value="[[hosts]]\nfoo=bar\n")

    with pytest.raises(ValueError):
        wake.cli.get_config()


@pytest.mark.parametrize(
    ["hosts", "message", "count"],
    [
        ('[[hosts]]\nname="foo"\nmac="00:11:22:33:44:55"\n', "", 1),
        ('[[hosts]]\nname="foo"\nport=1\nmac="ZZ:11:22:33:44:55"', "Invalid", 0),
        ('[[hosts]]\nname="foo"\nmac="00:11:22:33:44:55"\nx=0\n', "Unknown", 1),
    ],
    ids=["valid configuration", "valid configuration", "unknown property"],
)
def test_config_parse(capsys, mocker, hosts: dict[str, str | int], message: str, count: int):  # pylint: disable=w0621
    mocker.patch("wake.cli.pathlib.Path.read_text", return_value=hosts)

    result = wake.cli.get_config()
    captured = capsys.readouterr()

    if message:
        assert message in captured.err

    assert isinstance(result, Hosts)
    assert result.count == count


@pytest.fixture
def hosts():
    data = [
        Host(name="foo", mac="00:11:22:33:44:55"),
        Host(name="bar", mac="AA:BB:CC:DD:EE:FF"),
    ]
    return Hosts(data)


@pytest.mark.parametrize(
    ["args", "message", "exit_code", "socket_return"],
    [
        (["host", "--all"], "Waking", 0, 0),
        (["host", "--all", "foo"], "named hosts", 2, 0),
        (["host", "xyz"], "Unknown", 0, 0),
        (["host", "xyz"], "No hosts", 0, 0),
        (["host", "foo"], "Waking", 0, 0),
        (["host", "foo"], "Failed", 1, 1),
    ],
    ids=[
        "wake all hosts",
        "mutually exclusive options",
        "unknown host name",
        "no hosts to wake",
        "waking host",
        "socket fail",
    ],
)
def test_cli_host(mocker, hosts, args, message, exit_code, socket_return):  # pylint: disable=r0913,w0621
    mocker.patch("wake.cli.get_config", return_value=hosts)
    mocker.patch("wake.cli.socket.socket.sendto", return_value=socket_return)

    runner = CliRunner()
    result = runner.invoke(wake.cli.cli, args)

    assert result.exit_code == exit_code
    assert message in result.output


def test_cli_show(mocker, hosts):  # pylint: disable=w0621
    mocker.patch("wake.cli.get_config", return_value=hosts)

    runner = CliRunner()
    result = runner.invoke(wake.cli.cli, ["show"])

    assert result.output == f"\n{hosts.table}\n"
