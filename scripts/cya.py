# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a C&A receipt on facturacion.cyamoda.com.

The receipt has a "Datos para Facturar" section at the end, with the store, the ticket,
the date and the total. The portal finds the ticket before asking for the receiver's
data.

Usage:
    cya.py --tienda 012 --ticket 12345678901234 --fecha 10/11/2026 --total 100.00 \
        --uso S01 [--send]
"""

import datetime
import sys

from portal import InvoicePortal, PortalDone, PortalError, pattern_argument


class Cya(InvoicePortal):
    name = "cya"
    url = "https://facturacion.cyamoda.com/"

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--tienda", required=True, help='"TIENDA", e.g. 012')
        parser.add_argument(
            "--ticket",
            required=True,
            type=pattern_argument(
                pattern=r"\d+", error="the ticket should be only digits"
            ),
            help='"TICKET"',
        )
        parser.add_argument("--fecha", required=True, help='"FECHA", dd/mm/yyyy')
        parser.add_argument("--total", required=True, help='"TOTAL", with cents')

    def choose(self, select, code, what):
        """Pick the option that starts with a SAT code, once the portal loads them."""
        for _attempt in range(20):
            values = self.page.eval_on_selector(
                select, "s => Array.from(s.options).map(o => o.value)"
            )
            matches = [value for value in values if value.startswith(code + " - ")]
            if matches:
                self.page.select_option(select, matches[0])
                return
            self.page.wait_for_timeout(500)
        raise PortalError("%s %s not offered; options: %s" % (what, code, values))

    def fill_01_ticket(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        self.page.fill("#tienda", self.args.tienda)
        self.page.fill("#ticket", self.args.ticket)
        # The portal takes the date as yyyy-mm-dd.
        date = datetime.datetime.strptime(self.args.fecha, "%d/%m/%Y").date()
        self.page.fill("#fecha", date.isoformat())
        self.page.fill("#total", self.args.total)
        self.page.check("#check", force=True)
        self.show(["#tienda", "#ticket", "#fecha", "#total"])
        self.page.click("#Button1")
        # A ticket already invoiced gets a note, and one the portal doesn't find, a box
        # that starts with "Error:".
        invoiced_note = ".alert-info:has-text('YA FACTURADO')"
        self.wait_for_answer("#rfc, %s" % invoiced_note, errors=[".alert-danger"])
        if self.page.is_visible(invoiced_note):
            raise PortalDone("already invoiced: %s" % self.text(invoiced_note))

    def fill_02_receiver(self):
        # The regime options load after the RFC is typed.
        self.page.click("#rfc")
        self.page.keyboard.type(self.receiver.rfc, delay=50)
        self.page.keyboard.press("Tab")
        self.page.fill("#nombre", self.receiver.name)
        self.page.fill("#codigopostal", self.receiver.postal_code)
        self.page.fill("#correo", self.args.email)
        self.choose("#regimen", self.regime(), "Régimen fiscal")
        self.choose("#cfdi", self.args.uso, "Uso CFDI")
        self.show(["#rfc", "#nombre", "#codigopostal", "#correo", "#regimen", "#cfdi"])
        self.page.click("button[type=submit]:has-text('Siguiente')")
        self.wait_for_answer(":text('DATOS DEL TICKET')", errors=[".alert-danger"])

    def fill_03_review(self):
        """Print the portal's summary, the last step before it issues the invoice."""
        print("SUMMARY: %s" % self.text()[:900])

    def submit_01_invoice(self):
        self.page.click("button[type=submit]:has-text('Siguiente')")
        # The answer is a note: "Ticket timbrado correctamente. Descargar: PDF XML".
        self.wait_for_answer(
            ".alert-info:has-text('timbrado')", errors=[".alert-danger"], timeout=120
        )
        print("RESULT: %s" % self.text()[:1200])


if __name__ == "__main__":
    sys.exit(Cya.main())
