"""Fail loudly instead of letting a unit test fall back to a paid live service."""
import socket


class ExternalNetworkForbidden(BaseException):
    """Do not let application-level ``except Exception`` hide a network attempt."""


def forbid_network(*args, **kwargs):
    raise ExternalNetworkForbidden(
        "Unit tests must not access the network or paid AI; inject an in-process fake."
    )


def install_network_guard(monkeypatch):
    monkeypatch.setattr(socket, "create_connection", forbid_network)
    monkeypatch.setattr(socket, "getaddrinfo", forbid_network)
    monkeypatch.setattr(socket.socket, "connect", forbid_network)
    monkeypatch.setattr(socket.socket, "connect_ex", forbid_network)
    monkeypatch.setattr(socket.socket, "sendto", forbid_network)
