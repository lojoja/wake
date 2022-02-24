wake
====

A simple wakeonlan implementation for waking defined hosts.


Requirements
------------

* Python 3.9.x


Installation
------------

```
pip install git+https://github.com/lojoja/wake.git
```


Use
---

Wake a specific host:

```
wake host myhost
```

Wake all hosts:

```
wake host --all
```

Show hosts:

```
wake show
```

Increase verbosity:

```
wake host myhost --verbose
```

Decrease verbosity:

```
wake host myhost --quiet
```


Configure
---------

Copy `/usr/local/etc/wake.example.json` to `/usr/local/etc/wake.json` and add entries for each remote host.

Every host must have a `name` and `mac` value; `ip` and `port` are optional. `ip` is an IPv4 address. `mac` can be formatted as follows:

- 00:11:22:33:44:55
- 00-11-22-33-44-55
- 0011.2233.4455
- 001122334455

Example:

```
[
    {
        "name": "myhost",
        "mac": "AABBCCDDEEFF"
    },
    {
        "name": "myotherhost",
        "mac": "00:11:22:33:44:55",
        "ip": "255.255.255.255",
        "port": 7
    }
]
```


License
-------

Wake is released under the [MIT License](./LICENSE)
