# NAME

tcp\_distance - Find the hop distance at which a host connect succeeds or fails

# SYNOPSIS

    tcp_distance [-4] [-6] [-s|--source host] [-m|--max_hops max_ttl] [--w|--wait_time time] [-q|--quiet] [-d|--debug] [-T|--traceroute program] [host [port]]
    tcp_distance [--unsafe|-U] -h|--help

# DESCRIPTION

**tcp\_distance** tries a connect with various TTLs to determine at which hop
count the normal result gets established. The main use of this program is to
determine how far away a host is or how far away a blocking firewall sits.
Combining the failure case with a normal traceroute might then even get you the
exact identity of the firewall if anything is returned at that hop count.

Unlike several standard TCP traceroute tools this program does not require any
special privileges.

host defaults to www.google.com, port defaults to 80

# OPTIONS

- -6

    Force ipv6

- -4

    Force ipv4

- -m, --max-hops integer

    Maximum hop distance that will be probed. This is also determines the
    initial probe that gets done to determine the expected result of a
    connection. Defaults to 64.

- -s source\_addr, --source source\_addr

    Chooses an alternative source address. Note that you must select the address
    of one of the interfaces. By default, the address of the outgoing interface
    is used.

- -w float, --wait_time float

    How long to wait for the result of a connection attempt in seconds.
    Defaults to 5.

- -T program, --traceroute program

    If the connection fails a traceroute is run for the distance on which the
    connection fails. This option decides which  program gets run in that case.
    Defaults to `traceroute`.

- -q, --quiet

    Be less chatty, just print the final result

- -d, --debug

    Give debugging output. Mainly tells you what probes get done and their result.

- -h, --help

    Show this help.

- -U, --unsafe

    Allow even root to run the perldoc.
    Remember, the reason this is off by default is because it **IS** unsafe.

- --version

    Print version info.

# EXAMPLE

A typical use would be:

    tcp_distance www.google.com 80

with an output like:

    Using ip 2a00:1450:4013:c00::6a port 80
    Failed to connect to www.google.com 80 at TTL 10: Connection timed out. Forging on in search of connection
    Connected to www.google.com 80 at TTL 11

This indicates that www.google.com is 11 hops aways. The device at 10 hops is
probably some form of packet filter (e.g. a firewall). Notice that not all
distances before the final TTL get probed so the list of filtering devices does
not have to be exhaustive. However the device just before the final TTL is
guaranteed to have been probed.

Another use:

    tcp_distance www.google.com 81

with an output like:

    Using ip 2a00:1450:4013:c00::6a port 81
    Failed to connect to www.google.com 81 at TTL 5: Connection timed out
    traceroute to 2a00:1450:4013:c00::6a (2a00:1450:4013:c00::6a), 5 hops max, 80 byte packets
     5  amsix-router.google.com (2001:7f8:1::a501:5169:1)  22.648 ms  22.962 ms  24.739 ms

This indicates that port 81 is probably blocked by core2.ams.net.google.com at
a distance of 5 hops.

# BUGS

Will not work if a normal connect to the target host returns `host unreachable`
since the TTL probes also return that same failure. Therefore the program will
be unable to see where the behaviour changes. Using raw sockets would enable
interpreting the exact ICMP packets but that would mean the program has to be
privileged.

# SEE ALSO

[traceroute(1)](http://man.he.net/man1/traceroute),
[tcptraceroute(1)](http://man.he.net/man1/tcptraceroute)

# AUTHOR

Ton Hospel, &lt;tcp\_distance@ton.iguana.be>

# COPYRIGHT AND LICENSE

Copyright (C) 2024 by Ton Hospel

This library is free software; you can redistribute it and/or modify
it under the same terms as Perl itself, either Perl version 5.8.2 or,
at your option, any later version of Perl 5 you may have available.
