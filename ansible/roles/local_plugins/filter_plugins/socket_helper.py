#!/usr/bin/env python3

from math import sqrt, ceil
from select import select
from errno import ETIMEDOUT, EHOSTUNREACH, ECONNREFUSED
from os import strerror
from time import monotonic
from socket import (
    getaddrinfo, gaierror, inet_pton, socket, AddressFamily, SocketKind,
    AF_INET, AF_INET6, IPPROTO_TCP, IPPROTO_IP, IPPROTO_IPV6, SOCK_DGRAM,
    IP_TTL, IPV6_UNICAST_HOPS, SOL_SOCKET, SO_ERROR,
    AI_ADDRCONFIG, AI_NUMERICSERV, AI_NUMERICHOST
)
from typing import Optional, Union

from ansible.errors import AnsibleError			# type: ignore

SockAddr = Union[tuple[str, int], tuple[str, int, int, int]]
AddrInfo = tuple[AddressFamily, SocketKind, int, str, SockAddr]


def addrinfo(host: str, service: str, family: int) -> list[AddrInfo]:
    flags = AI_ADDRCONFIG
    try:
        int(service)
        flags |= AI_NUMERICSERV
    except ValueError:
        pass
    if family == 0:
        for f in AF_INET, AF_INET6:
            try:
                inet_pton(f, host)
                flags |= AI_NUMERICHOST
                break
            except OSError:
                pass
    else:
        try:
            inet_pton(family, host)
            flags |= AI_NUMERICHOST
        except OSError:
            pass

    try:
        addrs = getaddrinfo(host, service, family = family,
                            proto = IPPROTO_TCP, flags = flags)
    except gaierror as exc:
        try:
            addrs = getaddrinfo("0.0.0.0", service, proto = IPPROTO_TCP)
        except gaierror:
            raise AnsibleError("Unknown TCP service %s" % repr(service)) from None
        raise AnsibleError("Cannot resolve %s: %s" % (repr(host), str(exc)))
    return addrs

def get_ip(address_family: Optional[str], host: str, service: str,
           source: Optional[str]) -> dict[str, list]:
    if not address_family or address_family == "0":
        family = 0
    elif address_family == "4" or address_family == 4:
        family = AF_INET
    elif address_family == "6" or address_family == 6:
        family = AF_INET6
    else:
        raise AnsibleError(f"Unknown {address_family=}")
    addrs = addrinfo(host, service, family)

    if not source:
        for addr in addrs:
            try:
                with socket(addr[0], SOCK_DGRAM) as s:
                    s.connect(addr[4])
                    s_addr = s.getsockname()
                    source_addr = [s_addr[0], 0, *s_addr[2:]]
            except OSError:
                continue
            break
        else:
            raise AnsibleError("Cannot connect to any address of %s" % repr(host))
    else:
        saddrs = getaddrinfo(source, "0", family)
        # Look for a compatibe source and destination
        tried = 0
        binds = 0
        for addr in addrs:
            for saddr in saddrs:
                if addr[0] != saddr[0]:
                    continue
                tried += 1
                try:
                    with socket(addr[0], SOCK_DGRAM) as s:
                        s.bind(saddr[4])
                        binds += 1
                        s.connect(addr[4])
                        s_addr = s.getsockname()
                        source_addr = [s_addr[0], 0, *s_addr[2:]]
                except OSError:
                    continue
                break
            else:
                continue
            break
        else:
            if not tried:
                raise AnsibleError("Address family of %s is incompatible with %s"
                                 % (repr(host), repr(source)))
            if not binds:
                raise AnsibleError("Cannot bind to any address of %s" %
                                 repr(source))

            raise AnsibleError("Cannot connect to any address of %s from any address of %s" %
                               (repr(host), repr(source)))
    return dict(
        source = source_addr,
        dest = list(addr[4]),
        socket = [int(addr[0]), int(addr[1]), addr[2]]
    )


def ttl_probe(ttl: int, ips: dict[str, list], wait_time: float) -> dict[str, Union[str, int]]:
    errno: int
    with socket(*ips["socket"]) as s:
        s.bind(tuple(ips["source"]))
        s.setblocking(False)
        if ips["socket"][0] == AF_INET:
            s.setsockopt(IPPROTO_IP, IP_TTL, ttl)
        elif ips["socket"][0] == AF_INET6:
            s.setsockopt(IPPROTO_IPV6, IPV6_UNICAST_HOPS, ttl)
        else:
            raise AssertionError(f"Impossible family {ips['socket'][0]!r}")

        start = monotonic()
        try:
            s.connect(tuple(ips["dest"]))
            elapsed = monotonic() - start
            errno = 0
        except BlockingIOError:
            now = start
            end = now + wait_time
            while True:
                remaining = end - now
                if remaining <= 0:
                    elapsed = now - start
                    errno = ETIMEDOUT
                    break
                try:
                    _, write_sockets, _ = select([], [s], [], remaining)
                except InterruptedError:
                    pass
                else:
                    if write_sockets:
                        elapsed = monotonic() - start
                        errno = s.getsockopt(SOL_SOCKET, SO_ERROR)
                        break
                    # Othwerwise it must be a timeout
                now = monotonic()
        except OSError as exc:
            elapsed = monotonic() - start
            errno = exc.errno
    return dict(
        msg = "TTL %2d: %s after %.3f s" % (ttl, strerror(errno), elapsed),
        errno = errno,
        error = strerror(errno)
    )


def next_probe(low: int, high: int) -> int:
    return ceil(sqrt(low * (high-1)))


def is_unreachable(err: int) -> bool:
    return err == EHOSTUNREACH

class FilterModule:
    def filters(self):
        return dict(
            get_ip     = get_ip,
            ttl_probe  = ttl_probe,
            next_probe = next_probe,
            is_unreachable = is_unreachable,
        )
