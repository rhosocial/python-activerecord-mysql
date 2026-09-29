# tests/rhosocial/activerecord_mysql_test/feature/backend/test_ssl_connection_params.py
"""Regression tests: MySQL SSL/TLS config must reach mysql-connector.

``MySQLConnectionConfig`` inherits the generic ``SSLMixin``, but the driver
spells its options differently: cipher lists are ``tls_ciphersuites`` (a list)
and protocol selection is ``tls_versions``. Two of the inherited fields have no
driver counterpart at all, so they must be rejected loudly rather than
collected and dropped.
"""

from unittest.mock import patch

import pytest

from rhosocial.activerecord.backend.impl.mysql.backend.backend import MySQLBackend
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig


def make_config(**kwargs):
    defaults = dict(
        host="db.example.com",
        port=3306,
        database="test_db",
        username="tester",
        password="secret",
    )
    defaults.update(kwargs)
    return MySQLConnectionConfig(**defaults)


def test_mutual_tls_certificates_are_forwarded():
    backend = MySQLBackend(connection_config=make_config(
        ssl_ca="/certs/ca.pem",
        ssl_cert="/certs/client.pem",
        ssl_key="/certs/client-key.pem",
        ssl_verify_cert=True,
        ssl_verify_identity=True,
    ))

    with patch("rhosocial.activerecord.backend.impl.mysql.backend.backend.mysql.connector.connect") as connect:
        backend.connect()

    params = connect.call_args.kwargs
    assert params["ssl_ca"] == "/certs/ca.pem"
    assert params["ssl_cert"] == "/certs/client.pem"
    assert params["ssl_key"] == "/certs/client-key.pem"
    assert params["ssl_verify_cert"] is True
    assert params["ssl_verify_identity"] is True


def test_unset_certificate_fields_are_omitted():
    """Passing ``ssl_ca=None`` is noise; the driver must be able to apply its
    own default, and an explicit False would override a driver default of True."""
    backend = MySQLBackend(connection_config=make_config())
    with patch("rhosocial.activerecord.backend.impl.mysql.backend.backend.mysql.connector.connect") as connect:
        backend.connect()

    params = connect.call_args.kwargs
    for key in ("ssl_ca", "ssl_cert", "ssl_key", "ssl_verify_cert", "ssl_verify_identity"):
        assert key not in params, f"{key} must not be emitted when unset"


def test_tls_versions_and_ciphersuites_are_forwarded():
    backend = MySQLBackend(connection_config=make_config(
        tls_versions=["TLSv1.2", "TLSv1.3"],
        tls_ciphersuites=["TLSv1.3"],
    ))
    with patch("rhosocial.activerecord.backend.impl.mysql.backend.backend.mysql.connector.connect") as connect:
        backend.connect()

    params = connect.call_args.kwargs
    assert params["tls_versions"] == ["TLSv1.2", "TLSv1.3"]
    assert params["tls_ciphersuites"] == ["TLSv1.3"]


def test_to_dict_exposes_tls_selection():
    config = make_config(tls_versions=["TLSv1.3"], tls_ciphersuites=["TLSv1.3"])
    assert config.to_dict()["tls_versions"] == ["TLSv1.3"]
    assert config.to_dict()["tls_ciphersuites"] == ["TLSv1.3"]


def test_ssl_mode_is_rejected_instead_of_silently_ignored():
    with pytest.raises(ValueError, match="ssl_mode is not supported"):
        make_config(ssl_mode="REQUIRED").validate()


def test_ssl_ciphers_is_rejected_instead_of_silently_ignored():
    with pytest.raises(ValueError, match="ssl_ciphers is not supported"):
        make_config(ssl_ciphers="ECDHE-RSA-AES256-GCM-SHA384").validate()


def test_validate_passes_for_supported_configuration():
    assert make_config(ssl_ca="/certs/ca.pem", tls_versions=["TLSv1.3"]).validate() is True
