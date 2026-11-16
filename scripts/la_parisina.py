# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a La Parisina receipt on facturacion.laparisina.com.mx.

The end of the receipt has the data to invoice: the branch ("Sucursal 1401 GUADALAJARA
CENTRO"), the register ("Caja"), the ticket ("No Ticket"), the total and the date.

The first time, the portal asks to register the RFC with the receiver's address. The
script does it even without `--send`, because the portal needs it to show the ticket's
form, and registering doesn't issue anything. The portal issues the invoice as soon as
the ticket's form is sent, with no preview.

Usage:
    la_parisina.py --estado Jalisco --sucursal 1401 --caja 3 --ticket 12345 \
        --fecha 14/11/2026 --total 100.00 --uso S01 [--send]
"""

import datetime
import sys
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from portal import InvoicePortal, PortalDone, PortalError, pattern_argument


class LaParisina(InvoicePortal):
    name = "la_parisina"
    url = "https://facturacion.laparisina.com.mx/"
    # The first time, the portal asks to register the RFC with its address.
    required_receiver_fields = (
        "street",
        "exterior_number",
        "municipality",
        "neighborhood",
        "state",
    )
    # The receiver's data the portal keeps, shown before the ticket's form.
    receiver_fields = ["#TxtRFC2", "#TxtResultado", "#TxtCodigoPostal", "#TxtMail"]
    # The text fields of the registration reject "Á", "ü" and "Ü", though they take the
    # other accents and "ñ".
    rejected_letters = str.maketrans("ÁüÜ", "AuU")
    ticket_fields = [
        "#DropDownList2",
        "#ddlComputedColumns",
        "#ddlUsoCFDI",
        "#TxtCaja",
        "#TxtTicket",
        "#TxtImporte",
        "#TxtFecha",
    ]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--estado", required=True, help="the state of the branch, e.g. Jalisco"
        )
        parser.add_argument(
            "--sucursal",
            required=True,
            type=pattern_argument(
                pattern=r"\d{4}", error="the branch should be its 4 digits"
            ),
            help='the 4 digits of "Sucursal"',
        )
        parser.add_argument("--caja", required=True, help='"Caja"')
        parser.add_argument(
            "--ticket",
            required=True,
            type=pattern_argument(
                pattern=r"\d+", error="the ticket should be only digits"
            ),
            help='"No Ticket"',
        )
        parser.add_argument("--fecha", required=True, help='"Fecha", dd/mm/yyyy')
        parser.add_argument("--total", required=True, help='"Total a pagar"')

    def option_by_text(self, selector, text, what):
        """Return the value of the option whose text matches, ignoring accents."""
        wanted = self.comparable_text(text)
        for value in self.option_values(selector):
            if self.comparable_text(value) == wanted:
                return value
        raise PortalError("%s %r not offered" % (what, text))

    def select(self, selector, value):
        """Select an option, and wait for the page to reload when the field posts it.

        The state of the ticket's form does, and changes the branches it offers.
        """
        onchange = self.page.get_attribute(selector, "onchange") or ""
        if "__doPostBack" not in onchange:
            self.page.select_option(selector, value)
            return
        with self.page.expect_navigation(timeout=60000):
            self.page.select_option(selector, value)

    def search_rfc(self):
        """Look up the RFC, which shows its saved data or the form to register it."""
        self.page.check("#RdoBtn2")  # Física; #RdoBtn1 is Moral
        self.page.fill("#TxtRFC", self.receiver.rfc)
        self.page.click("#BtnRFC")
        # An RFC it doesn't know opens a dialog ("No se encontró tu RFC, Regístrate!!")
        # and the form to register it.
        try:
            self.page.locator("#BtnSi, #BtnRegistro").first.wait_for(timeout=60000)
        except PlaywrightTimeoutError:
            raise PortalError(
                "the portal didn't accept the RFC: %s" % self.text()[:600]
            )

    def wait_for_dialog(self, timeout=120):
        """Return the message of the next dialog, which is how the portal answers."""
        dialog_count = len(self.dialogs)
        deadline = time.monotonic() + timeout
        while len(self.dialogs) == dialog_count and time.monotonic() < deadline:
            self.page.wait_for_timeout(500)
        if len(self.dialogs) == dialog_count:
            raise PortalError(
                "the portal didn't answer in %d seconds: %s"
                % (timeout, self.text()[:600])
            )
        return self.dialogs[-1]

    def fill_01_rfc(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        self.search_rfc()

    def fill_02_register(self):
        """Register the RFC, which the portal asks for the first time only.

        It isn't the invoice yet, so a run without `--send` does it too.
        """
        if not self.page.is_visible("#BtnRegistro"):
            return
        # The name has to be the one of the Constancia, so it can't lose its accents.
        if self.receiver.name != self.receiver.name.translate(self.rejected_letters):
            raise PortalError(
                'the portal rejects "Á", "ü" and "Ü" in the name %r'
                % self.receiver.name
            )
        self.select(
            "#DropDownList1",
            self.option_by_text("#DropDownList1", self.receiver.state, "Estado"),
        )
        regimes = [
            value
            for value in self.option_values("#DropDownList3")
            if value.startswith(self.regime() + " ")
        ]
        if not regimes:
            raise PortalError("regime %s not offered" % self.regime())
        self.select("#DropDownList3", regimes[0])
        self.page.fill("#TxtResultado", self.receiver.name)
        self.page.fill(
            "#TxtDireccion", self.receiver.street.translate(self.rejected_letters)
        )
        self.page.fill("#TxtNumero", self.receiver.exterior_number)
        self.page.fill(
            "#TxtDelegacion",
            self.receiver.municipality.translate(self.rejected_letters),
        )
        self.page.fill(
            "#TxtColonia", self.receiver.neighborhood.translate(self.rejected_letters)
        )
        self.page.fill("#TxtCodigoPostal", self.receiver.postal_code)
        self.page.fill("#TxtMail", self.args.email)
        self.show(
            [
                "#TxtRFC2",
                "#TxtResultado",
                "#TxtDireccion",
                "#TxtNumero",
                "#TxtDelegacion",
                "#TxtColonia",
                "#TxtCodigoPostal",
                "#DropDownList1",
                "#DropDownList3",
                "#TxtMail",
            ]
        )
        self.page.click("#BtnRegistro")
        # It shows the data in a dialog, sometimes says the system isn't available,
        # then says "Se realizo registro exitoso" and goes back to the first step. A
        # value it rejects turns its field red ("Los campos en rojo estan incorrectos o
        # vacios").
        for _attempt in range(3):
            answer = self.wait_for_dialog()
            if "registro exitoso" in answer.lower() or "en rojo" in answer.lower():
                break
        if "registro exitoso" not in answer.lower():
            raise PortalError("the portal did not register the RFC: %s" % answer)
        self.search_rfc()

    def fill_03_receiver(self):
        """Check the receiver's data the portal keeps, since it can be out of date."""
        self.show(self.receiver_fields, width=18)
        expected = [
            self.receiver.rfc,
            self.receiver.name,
            self.receiver.postal_code,
            self.args.email,
        ]
        kept = [self.page.input_value(selector) for selector in self.receiver_fields]
        if [value.upper() for value in kept] != [value.upper() for value in expected]:
            raise PortalError(
                "the portal keeps other data for the RFC; update it by hand: %s" % kept
            )
        # The portal shows the regime in the box of "Entre calles", not in the box of
        # the regime. It can't change per invoice, so stop when the use needs another.
        regime = self.page.input_value("#TxtEntreCalles") or self.page.input_value(
            "#TxtRegimen"
        )
        if not regime.startswith(self.regime() + " "):
            raise PortalError(
                "the RFC is registered with regime %r, not %s" % (regime, self.regime())
            )
        print("%-18s %r" % ("regime", regime))
        self.page.click("#BtnSi")
        self.wait_for_answer("#BtnSi2")
        self.page.click("#BtnSi2")
        self.wait_for_answer("#DropDownList2")

    def fill_04_ticket(self):
        # The branches load after the state.
        self.select(
            "#DropDownList2",
            self.option_by_text("#DropDownList2", self.args.estado, "Estado"),
        )
        self.select_offered("#ddlComputedColumns", self.args.sucursal, "Sucursal")
        self.select_offered("#ddlUsoCFDI", self.args.uso, "Uso CFDI")
        self.page.fill("#TxtCaja", self.args.caja)
        self.page.fill("#TxtTicket", self.args.ticket)
        self.page.fill("#TxtImporte", self.args.total)
        date = datetime.datetime.strptime(self.args.fecha, "%d/%m/%Y").date()
        self.page.fill("#TxtFecha", date.isoformat())
        self.show(self.ticket_fields, width=22)

    def submit_01_invoice(self):
        self.page.click("#BtnFacturar")
        # The answer is a dialog ("Se Genero la Factura No. 1401-12345").
        answer = self.wait_for_dialog()
        if "ya fue facturado" in answer.lower():
            raise PortalDone("already invoiced: %s" % answer)
        if "se genero la factura" not in answer.lower():
            raise PortalError("the portal did not issue the invoice: %s" % answer)
        print("RESULT: %s; the CFDI arrives by email within 24 hours" % answer)


if __name__ == "__main__":
    sys.exit(LaParisina.main())
