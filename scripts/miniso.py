# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a Miniso receipt on its Diverza portal (tickets.diverza.com/miniso-mexico).

Usage:
    miniso.py --ticket 0123401123456231026 --fecha 23/10/2026 --monto 99.90 --uso S01 [--send]
"""

import datetime
import sys

from portal import InvoicePortal, PortalError


class Miniso(InvoicePortal):
    name = "miniso"
    url = "https://tickets.diverza.com/miniso-mexico/facturar-ticket"
    # The id of every field in the receiver's form has this prefix.
    field_prefix = "#ticket-bill-form_"
    receiver_fields = ["rfc", "name", "zip_code", "tax_regime", "document_use", "email", "confirm_email"]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--ticket", required=True, help="the 19 digits under the barcode")
        parser.add_argument("--fecha", required=True, help="dd/mm/yyyy")
        parser.add_argument("--monto", required=True)

    def field(self, name):
        """Return the selector of a field of the receiver's form, by its id without the prefix."""
        return self.field_prefix + name

    def fill_01_ticket(self):
        date = datetime.datetime.strptime(self.args.fecha, "%d/%m/%Y").date()
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        # The date only takes a click in the calendar, which shows the current month only (Miniso
        # invoices within the month of the purchase).
        self.page.fill("#search-ticket-form_folio", self.args.ticket)
        self.page.click("#search-ticket-form_fecha")
        self.page.wait_for_timeout(1000)
        self.page.click(".datepicker-days td.day:not(.old):not(.new) >> text='%d'" % date.day)
        self.page.wait_for_timeout(800)
        self.page.fill("#search-ticket-form_monto", self.args.monto)
        picked = self.page.input_value("#search-ticket-form_fecha")
        if picked != self.args.fecha:
            raise PortalError(
                "the calendar has %r instead of %s (is the purchase from another month?)" % (picked, self.args.fecha)
            )
        self.page.click("text=Buscar")
        self.page.wait_for_timeout(8000)
        if not self.page.is_visible("#continue_button"):
            raise PortalError("the portal did not find the receipt: %s" % self.text()[:600])

    def fill_02_receiver(self):
        self.page.click("#continue_button")
        self.page.wait_for_timeout(4000)
        if not self.page.is_visible(self.field("rfc")):
            raise PortalError("unexpected page after Continuar: %s" % self.text()[:600])
        self.page.fill(self.field("rfc"), self.receiver.rfc)
        self.page.fill(self.field("name"), self.receiver.name)
        self.page.fill(self.field("zip_code"), self.receiver.postal_code)
        self.select_offered(self.field("tax_regime"), self.regime(), "Regime")
        self.page.wait_for_timeout(1500)
        self.select_offered(self.field("document_use"), self.args.uso, "Uso CFDI")
        self.page.fill(self.field("email"), self.args.email)
        self.page.fill(self.field("confirm_email"), self.args.email)
        if not self.page.is_checked(self.field("privacy")):
            self.page.check(self.field("privacy"), force=True)
        self.page.wait_for_timeout(800)
        self.show([self.field(name) for name in self.receiver_fields], width=32)
        print("%-32s %r" % ("privacy", self.page.is_checked(self.field("privacy"))))

    def submit_01_invoice(self):
        self.page.click("#billing_button")
        self.page.wait_for_timeout(12000)
        # The answer comes in a modal ("Éxito: Se ha generado la factura <uuid> ..."). The page text
        # also has the hidden options of the form, so read only the visible dialog.
        dialogs = [
            dialog
            for dialog in self.page.query_selector_all(".modal, [role=dialog], .swal2-popup")
            if dialog.is_visible()
        ]
        answer = " ".join(dialogs[0].inner_text().split()) if dialogs else self.text()
        print("RESULT: %s" % answer[:800])


if __name__ == "__main__":
    sys.exit(Miniso.main())
