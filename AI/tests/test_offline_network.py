"""The default pytest command must be safe with live local credentials present."""
import socket

from fastapi.testclient import TestClient
import pytest

from app.main import app
from tests.support.offline_network import ExternalNetworkForbidden


@pytest.mark.parametrize("operation", ["connect", "connect_ex"])
def test_tcp_is_blocked_before_opening_connection(operation):
    with socket.socket() as connection:
        with pytest.raises(ExternalNetworkForbidden):
            getattr(connection, operation)(("127.0.0.1", 9))


def test_udp_is_blocked_before_sending_data():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
        with pytest.raises(ExternalNetworkForbidden):
            connection.sendto(b"offline-test", ("127.0.0.1", 9))


def test_connection_helper_and_dns_are_blocked():
    with pytest.raises(ExternalNetworkForbidden):
        socket.create_connection(("127.0.0.1", 9))
    with pytest.raises(ExternalNetworkForbidden):
        socket.getaddrinfo("localhost", 9)


def test_application_exception_fallback_cannot_hide_network_attempt():
    with pytest.raises(ExternalNetworkForbidden):
        try:
            socket.create_connection(("127.0.0.1", 9))
        except Exception:
            pytest.fail("A forbidden network call was hidden by a normal fallback")


def test_in_process_api_transport_still_works():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"
