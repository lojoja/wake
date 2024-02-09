# wake

A simple wakeonlan implementation for waking defined hosts.

## Requirements

- Python 3.10.x, 3.11.x
- Linux / macOS

**Note:** wake is not tested on Windows.

## Installation

```
pip install py-wake-cli
```

## Usage

```
Usage: wake [OPTIONS] COMMAND [ARGS]...

  A simple wakeonlan implementation.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  host  Wake the specified host(s).
  show  Show all hosts.
```

### Examples

Wake a specific host:

```
> wake host myhost
```

Wake all hosts:

```
> wake host --all
```

Show hosts:

```
> wake show
```

## Configure

Hosts should be defined in the file `~/.config/wake.toml`. Every host must have a `name` and `mac` value; `ip` and `port` are optional. `ip` is an IPv4 address. Optional valid MAC address separators are `:`, `-`, and `.`. The number of characters between separators does not matter. Example formats:

- AA:00:BB:11:CC:22
- AA-00-BB-11-CC-22
- AA00.BB11.CC22
- AA00BB11CC22

Example configuration:

```
[[ hosts ]]
name = "myhost"
mac = "AABBCCDDEEFF"

[[ hosts ]]
name = "myotherhost"
mac = "00:11:22:33:44:55"
ip = "255.255.255.255"
port = 7
```

## License

Wake is released under the [MIT License](./LICENSE)
