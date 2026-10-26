"""Tests for invoice-mx-receipt's scripts.

They cover what doesn't need a browser: the configuration, the regime for each Uso CFDI, the order
of the portal steps, and the requests by email and WhatsApp. The portals themselves are live
sites, so they are checked with dry runs.
"""

import argparse
import importlib
import socket
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
PORTALS = {
    "alsea": "Alsea",
    "carlscol": "Carlscol",
    "farmacias_guadalajara": "FarmaciasGuadalajara",
    "farmacias_similares": "FarmaciasSimilares",
    "kiosko": "Kiosko",
    "liverpool": "Liverpool",
    "miniso": "Miniso",
    "oxxo": "Oxxo",
    "soft_restaurant": "SoftRestaurant",
    "template": "Template",
    "walmart": "Walmart",
}
CONFIG = """
email = "facturas@example.com"
evidence_dir = "{evidence}"

[receiver]
rfc = "PEMJ800101AB1"
first_names = "JUAN"
paternal_last_name = "PEREZ"
maternal_last_name = "MARTINEZ"
postal_code = "01000"
regimes = ["626", "614"]

[request]
confirm_before_sending = true
sender = "Juan <juan@example.com>"
signature = ["Saludos", "Juan"]
"""


@pytest.fixture(name="import_script")
def import_script_fixture(monkeypatch):
    """Import a script's module the way the scripts import each other."""
    monkeypatch.syspath_prepend(str(SCRIPTS))
    for name in ["config", "portal", "request_invoice"] + list(PORTALS):
        sys.modules.pop(name, None)
    return importlib.import_module


@pytest.fixture(name="config_path")
def config_path_fixture(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(CONFIG.format(evidence=tmp_path / "evidence"))
    return path


@pytest.fixture(name="config")
def config_fixture(import_script, config_path):
    return import_script("config").Config.load(config_path)


def test_load_config(config):
    assert config.receiver.name == "JUAN PEREZ MARTINEZ"
    assert config.receiver.regimes == ["626", "614"]
    assert config.email == "facturas@example.com"
    assert config.signature == ["Saludos", "Juan"]
    assert config.sendmail == []


def test_load_config_from_environment(import_script, config_path, monkeypatch):
    monkeypatch.setenv("INVOICE_MX_RECEIPT_CONFIG", str(config_path))
    assert import_script("config").Config.load().receiver.rfc == "PEMJ800101AB1"


def test_load_config_missing_fields(import_script, tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[receiver]\nrfc = "PEMJ800101AB1"\n')
    with pytest.raises(SystemExit, match="receiver.first_names.*receiver.regimes, email"):
        import_script("config").Config.load(path)


def test_load_config_one_last_name(import_script, config_path):
    config_path.write_text(config_path.read_text().replace('maternal_last_name = "MARTINEZ"\n', ""))
    receiver = import_script("config").Config.load(config_path).receiver
    assert receiver.last_names == "PEREZ"
    assert receiver.name == "JUAN PEREZ"


def test_load_config_unknown_regime(import_script, config_path):
    config_path.write_text(config_path.read_text().replace('"614"]', '"999"]'))
    with pytest.raises(SystemExit, match="unknown regimes: 999"):
        import_script("config").Config.load(config_path)


def test_load_config_missing_file(import_script, tmp_path):
    with pytest.raises(SystemExit, match="no configuration"):
        import_script("config").Config.load(tmp_path / "missing.toml")


@pytest.mark.parametrize(
    ("regimes", "usage", "expected"),
    [
        (["626", "614"], "G03", "626"),
        (["626", "614"], "I04", "626"),
        (["626", "614"], "S01", "626"),
        (["626", "614"], "D01", "614"),
        (["614", "626"], "S01", "614"),
        (["612"], "D01", "612"),
    ],
)
def test_regime_for(config, regimes, usage, expected):
    config.receiver.regimes = regimes
    assert config.receiver.regime_for(usage) == expected


@pytest.mark.parametrize(
    ("regimes", "usage", "message"),
    [
        (["626"], "D01", "admits none"),
        (["626"], "X99", "unknown Uso CFDI"),
    ],
)
def test_regime_for_none(config, regimes, usage, message):
    config.receiver.regimes = regimes
    with pytest.raises(SystemExit, match=message):
        config.receiver.regime_for(usage)


def test_receipt_folder(config):
    path = config.receipt_folder("softrestaurant", "restaurante/123 456")
    assert path.is_dir()
    assert path.parent == config.evidence_dir
    assert path.name.endswith("-softrestaurant-restaurante_123_456")


def test_proxy_listening(config):
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        config.proxy = "socks5://127.0.0.1:%s" % server.getsockname()[1]
        assert config.proxy_listening()
        config.open_proxy()


def test_open_proxy_without_command(config):
    with socket.socket() as free:
        free.bind(("127.0.0.1", 0))
        config.proxy = "socks5://127.0.0.1:%s" % free.getsockname()[1]
    with pytest.raises(SystemExit, match="no proxy_command"):
        config.open_proxy()


@pytest.mark.parametrize(("module", "class_name"), PORTALS.items())
def test_portal_steps(import_script, module, class_name):
    portal = getattr(import_script(module), class_name)
    fill = portal.step_names("fill_")
    submit = portal.step_names("submit_")
    assert fill[0].startswith("fill_01_")
    numbers = [name.split("_")[1] for name in fill + submit]
    assert all(len(number) == 2 for number in numbers)
    assert len(set(fill)) == len({name.split("_")[1] for name in fill})
    assert portal.submits()


def test_kiosko_receipts_limit(import_script):
    parser = argparse.ArgumentParser()
    import_script("kiosko").Kiosko.add_arguments(parser)
    assert len(parser.parse_args(["--referencia", "1"] * 10).referencia) == 10
    with pytest.raises(SystemExit):
        parser.parse_args(["--referencia", "1"] * 11)


@pytest.mark.parametrize(
    "value, expected",
    [("ABCDE FGH1J KLMNO PQRST", "ABCDEFGH1JKLMNOPQRST"), ("abcdefgh1jklmnopqrst", "ABCDEFGH1JKLMNOPQRST")],
)
def test_liverpool_billing_code(import_script, value, expected):
    assert import_script("liverpool").billing_code(value) == expected


@pytest.mark.parametrize("value", ["ABCDE FGH1J KLMNO", "ABCDE FGH1J KLMNO PQRS-"])
def test_liverpool_billing_code_invalid(import_script, value):
    with pytest.raises(argparse.ArgumentTypeError):
        import_script("liverpool").billing_code(value)


def request_args(**values):
    defaults = {
        "ref": None,
        "fecha": "2026-10-23",
        "importe": "82.00",
        "uso": "S01",
        "field": [],
        "intro": None,
        "image": [],
        "csf": False,
        "to": "tienda@example.com",
    }
    defaults.update(values)
    return argparse.Namespace(**defaults)


def test_chat_message(import_script, config):
    request = import_script("request_invoice")
    args = request_args(field=["Folio=123456"])
    message = request.chat_message(request.receipt_data(args), request.billing_data(config, "D01"))
    assert message.startswith("Hola, ¿me pueden apoyar con la facturación de este ticket?\n\nDatos del ticket:\n")
    assert "- Folio: 123456" in message
    assert "- Régimen fiscal: 614 - Ingresos por intereses" in message
    assert "- Correo: facturas@example.com" in message
    assert "Saludos" not in message


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        ("33 1234 5678", "523312345678"),
        ("+52 33 1234 5678", "523312345678"),
        ("044 33 1234 5678", "523312345678"),
    ],
)
def test_whatsapp_link(import_script, number, expected):
    request = import_script("request_invoice")
    link = request.whatsapp_link(number, "Hola, ¿me pueden apoyar?\n- Fecha: 2026-10-23")
    prefix = "https://wa.me/%s?text=" % expected
    assert link.startswith(prefix)
    assert unquote(link[len(prefix) :]) == "Hola, ¿me pueden apoyar?\n- Fecha: 2026-10-23"


def test_build_email(import_script, config, tmp_path):
    request = import_script("request_invoice")
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"jpeg")
    args = request_args(image=[photo], intro="El portal no encuentra el ticket.")
    msg = request.build_email(config, args, request.receipt_data(args), request.billing_data(config, "S01"))
    assert msg["Subject"] == "Facturación de consumo del día 2026-10-23"
    assert msg["From"] == "Juan <juan@example.com>"
    text = msg.get_body(("plain",)).get_content()
    assert "El portal no encuentra el ticket." in text
    assert text.endswith("--\nSaludos\nJuan\n")
    html = msg.get_body(("html",)).get_content()
    assert "<li>Uso CFDI: S01 - Sin efectos fiscales</li>" in html
    assert [part.get_filename() for part in msg.iter_attachments()] == ["ticket_2026-10-23.jpg"]


def test_build_email_with_reference(import_script, config):
    request = import_script("request_invoice")
    args = request_args(ref="12345")
    msg = request.build_email(config, args, request.receipt_data(args), request.billing_data(config, "S01"))
    assert msg["Subject"] == "Facturación de consumo #12345"
    assert "- Referencia: 12345" in msg.get_body(("plain",)).get_content()


def test_build_email_csf_needs_configuration(import_script, config):
    request = import_script("request_invoice")
    args = request_args(csf=True)
    with pytest.raises(SystemExit, match="csf"):
        request.build_email(config, args, request.receipt_data(args), request.billing_data(config, "S01"))


def test_farmacias_similares_receiver_rfc(import_script):
    receiver_rfc = import_script("farmacias_similares").FarmaciasSimilares.receiver_rfc
    cfdi = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0">'
        b'<cfdi:Emisor Rfc="AAA010101AAA"/><cfdi:Receptor Rfc="PEMJ800101AB1"/>'
        b"</cfdi:Comprobante>"
    )
    assert receiver_rfc(cfdi) == "PEMJ800101AB1"
    assert receiver_rfc(cfdi.replace(b"<cfdi:Receptor", b"<cfdi:Otro")) is None
