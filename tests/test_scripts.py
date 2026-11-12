"""Tests for invoice-mx-receipt's scripts.

They cover what doesn't need a browser: the configuration, the regime for each Uso CFDI,
the order of the portal steps, and the requests by email and WhatsApp. The portals
themselves are live sites, so they are checked with dry runs.
"""

import argparse
import importlib
import socket
import sys
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import unquote

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
PORTALS = {
    "alsea": "Alsea",
    "carlscol": "Carlscol",
    "cerveceria_de_la_costa": "CerveceriaDeLaCosta",
    "farmacias_guadalajara": "FarmaciasGuadalajara",
    "farmacias_similares": "FarmaciasSimilares",
    "kiosko": "Kiosko",
    "la_marina": "LaMarina",
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
    with pytest.raises(
        SystemExit, match="receiver.first_names.*receiver.regimes, email"
    ):
        import_script("config").Config.load(path)


def test_load_config_one_last_name(import_script, config_path):
    config_path.write_text(
        config_path.read_text().replace('maternal_last_name = "MARTINEZ"\n', "")
    )
    receiver = import_script("config").Config.load(config_path).receiver
    assert receiver.last_names == "PEREZ"
    assert receiver.name == "JUAN PEREZ"


def test_load_config_address(import_script, config_path):
    config_path.write_text(
        config_path.read_text().replace(
            'regimes = ["626", "614"]\n',
            'regimes = ["626", "614"]\n'
            'mobile_phone = "5500000000"\nstate = "Jalisco"\n',
        )
    )
    receiver = import_script("config").Config.load(config_path).receiver
    assert (receiver.mobile_phone, receiver.state) == ("5500000000", "Jalisco")
    assert receiver.street == ""


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


@pytest.mark.parametrize(("module", "class_name"), PORTALS.items())
def test_required_receiver_fields_exist(import_script, module, class_name):
    """Each name in a portal's `required_receiver_fields` is a field of `Receiver`."""
    portal = getattr(import_script(module), class_name)
    receiver_field_names = {
        item.name for item in fields(import_script("config").Receiver)
    }
    not_in_receiver = set(portal.required_receiver_fields) - receiver_field_names
    assert not not_in_receiver


def test_kiosko_receipts_limit(import_script):
    parser = argparse.ArgumentParser()
    import_script("kiosko").Kiosko.add_arguments(parser)
    assert len(parser.parse_args(["--referencia", "1"] * 10).referencia) == 10
    with pytest.raises(SystemExit):
        parser.parse_args(["--referencia", "1"] * 11)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("ABCDE FGH1J KLMNO PQRST", "ABCDEFGH1JKLMNOPQRST"),
        ("abcdefgh1jklmnopqrst", "ABCDEFGH1JKLMNOPQRST"),
    ],
)
def test_liverpool_billing_code(import_script, value, expected):
    liverpool = import_script("liverpool").Liverpool
    parser = argparse.ArgumentParser()
    liverpool.add_arguments(parser)
    args = parser.parse_args(["--codigo", value, "--total", "100.00"])
    assert liverpool.billing_code(SimpleNamespace(args=args)) == expected


@pytest.mark.parametrize("value", ["ABCDE FGH1J KLMNO", "ABCDE FGH1J KLMNO PQRS-"])
def test_liverpool_billing_code_invalid(import_script, value):
    parser = argparse.ArgumentParser()
    import_script("liverpool").Liverpool.add_arguments(parser)
    with pytest.raises(SystemExit):
        parser.parse_args(["--codigo", value, "--total", "100.00"])


@pytest.mark.parametrize(
    "pattern, value, expected",
    [(r"(\d+)-(\d+)", "101-2345", ("101", "2345")), (r"\d{3}", "101", "101")],
)
def test_pattern_argument(import_script, pattern, value, expected):
    check = import_script("portal").pattern_argument(pattern=pattern, error="wrong")
    assert check(value) == expected


def test_pattern_argument_invalid(import_script):
    check = import_script("portal").pattern_argument(pattern=r"\d{3}", error="wrong")
    with pytest.raises(argparse.ArgumentTypeError, match="wrong, not '1012'"):
        check("1012")


def la_marina_folio(import_script, value):
    parser = argparse.ArgumentParser()
    import_script("la_marina").LaMarina.add_arguments(parser)
    args = [
        "--tienda",
        "La Marina Zapotlán",
        "--fecha",
        "2026-11-01",
        "--forma-pago",
        "04",
    ]
    return parser.parse_args(args + ["--folio", value]).folio


@pytest.mark.parametrize("value", ["101-2345", " 101 - 2345 "])
def test_la_marina_folio(import_script, value):
    assert la_marina_folio(import_script, value) == ("101", "2345")


@pytest.mark.parametrize("value", ["1012345", "101-", "A01-2345"])
def test_la_marina_folio_invalid(import_script, value):
    with pytest.raises(SystemExit):
        la_marina_folio(import_script, value)


def test_cerveceria_de_la_costa_tickets(import_script, config):
    portal = import_script("cerveceria_de_la_costa").CerveceriaDeLaCosta
    parser = argparse.ArgumentParser()
    portal.add_arguments(parser)
    args = parser.parse_args(
        ["--ticket", "123", "--total", "1.00", "--ticket", "456", "--total", "2.00"]
    )
    assert (args.ticket, args.total) == (["123", "456"], ["1.00", "2.00"])
    assert portal(args, config).ticket() == "123-456"


def test_cerveceria_de_la_costa_one_total_per_ticket(import_script, config):
    portal = import_script("cerveceria_de_la_costa").CerveceriaDeLaCosta
    args = SimpleNamespace(ticket=["123", "456"], total=["1.00"])
    with pytest.raises(SystemExit, match="one --total for each --ticket"):
        portal(args, config)


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
    message = request.chat_message(
        request.receipt_data(args), request.billing_data(config, "D01")
    )
    assert message.startswith(
        "Hola, ¿me pueden apoyar con la facturación de este ticket?\n\n"
        "Datos del ticket:\n"
    )
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
    link = request.whatsapp_link(
        number, "Hola, ¿me pueden apoyar?\n- Fecha: 2026-10-23"
    )
    prefix = "https://wa.me/%s?text=" % expected
    assert link.startswith(prefix)
    assert (
        unquote(link[len(prefix) :]) == "Hola, ¿me pueden apoyar?\n- Fecha: 2026-10-23"
    )


def test_build_email(import_script, config, tmp_path):
    request = import_script("request_invoice")
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"jpeg")
    args = request_args(image=[photo], intro="El portal no encuentra el ticket.")
    msg = request.build_email(
        config, args, request.receipt_data(args), request.billing_data(config, "S01")
    )
    assert msg["Subject"] == "Facturación de consumo del día 2026-10-23"
    assert msg["From"] == "Juan <juan@example.com>"
    text = msg.get_body(("plain",)).get_content()
    assert "El portal no encuentra el ticket." in text
    assert text.endswith("--\nSaludos\nJuan\n")
    html = msg.get_body(("html",)).get_content()
    assert "<li>Uso CFDI: S01 - Sin efectos fiscales</li>" in html
    assert [part.get_filename() for part in msg.iter_attachments()] == [
        "ticket_2026-10-23.jpg"
    ]


def test_build_email_with_reference(import_script, config):
    request = import_script("request_invoice")
    args = request_args(ref="12345")
    msg = request.build_email(
        config, args, request.receipt_data(args), request.billing_data(config, "S01")
    )
    assert msg["Subject"] == "Facturación de consumo #12345"
    assert "- Referencia: 12345" in msg.get_body(("plain",)).get_content()


def test_build_email_csf_needs_configuration(import_script, config):
    request = import_script("request_invoice")
    args = request_args(csf=True)
    with pytest.raises(SystemExit, match="csf"):
        request.build_email(
            config,
            args,
            request.receipt_data(args),
            request.billing_data(config, "S01"),
        )


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


class FakePage:
    """A page whose elements show up after some checks, as a slow portal's do."""

    def __init__(self, elements, after=0):
        self.elements = elements
        self.checks_left = after

    def locator(self, selector):
        found = [] if self.checks_left else [self.elements.get(selector)]
        return SimpleNamespace(
            filter=lambda visible: SimpleNamespace(
                count=lambda: len([text for text in found if text]),
                first=SimpleNamespace(inner_text=lambda: found[0]),
            )
        )

    def wait_for_timeout(self, _milliseconds):
        self.checks_left -= 1

    def inner_text(self, _selector):
        return "Buscando ticket..."


def portal_on(import_script, page):
    portal = import_script("template").Template.__new__(
        import_script("template").Template
    )
    portal.page = page
    portal.dialogs = []
    return portal


def test_wait_for_answer_slow_portal(import_script):
    page = FakePage({"#rfc": "RFC"}, after=3)
    portal_on(import_script, page).wait_for_answer("#rfc")
    assert page.checks_left == 0


def test_wait_for_answer_error(import_script):
    portal = portal_on(import_script, FakePage({".alert": " Ticket  no encontrado "}))
    with pytest.raises(Exception, match="^Ticket no encontrado$"):
        portal.wait_for_answer("#rfc", errors=(".alert",))


def test_wait_for_answer_dialog(import_script):
    portal = portal_on(import_script, FakePage({}, after=5))
    portal.page.wait_for_timeout = lambda _ms: portal.dialogs.append("Ya facturado")
    with pytest.raises(Exception, match="the portal answered: Ya facturado"):
        portal.wait_for_answer("#rfc")


def test_wait_for_answer_timeout(import_script):
    portal = portal_on(import_script, FakePage({}))
    with pytest.raises(Exception, match="didn't answer in 0 seconds: Buscando"):
        portal.wait_for_answer("#rfc", timeout=0)
