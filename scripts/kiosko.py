# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a receipt of Kiosko on facturas.mikiosko.mx.

Usage:
    kiosko.py --referencia "0123 4567 8901 2345 6789 012" [--referencia ...] --uso G03 [--send]
"""

import argparse
import base64
import sys

from portal import InvoicePortal, PortalError


class AppendReference(argparse.Action):
    """Collect the references, stopping at more than `limit`, the receipts the portal takes."""

    def __init__(self, *args, limit, **kwargs):
        super().__init__(*args, **kwargs)
        self.limit = limit

    def __call__(self, parser, namespace, value, option_string=None):
        references = (getattr(namespace, self.dest) or []) + [value]
        if len(references) > self.limit:
            parser.error("the portal takes up to %d receipts per invoice" % self.limit)
        setattr(namespace, self.dest, references)


class Kiosko(InvoicePortal):
    name = "kiosko"
    url = "https://facturas.mikiosko.mx/"
    # The receipts the portal takes on one invoice.
    max_receipts = 10

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--referencia",
            required=True,
            action=AppendReference,
            limit=cls.max_receipts,
            help="the 23 digits after the portal's URL; repeat it to put up to %d receipts on one invoice"
            % cls.max_receipts,
        )

    def ticket(self):
        first, *others = self.references()
        return "%s_plus_%d" % (first, len(others)) if others else first

    def references(self):
        return ["".join(reference.split()) for reference in self.args.referencia]

    def type_field(self, name, value):
        # The regime and Uso CFDI options load while the RFC is typed, not when it is filled. Clear the
        # field first, because the portal fills some fields of an RFC it already knows.
        field = self.page.locator("input[formcontrolname=%s]" % name)
        field.fill("")
        field.press_sequentially(value, delay=40)
        self.page.wait_for_timeout(800)

    def choose(self, index, value, what):
        """Pick an option of a dropdown, stopping when the portal doesn't offer it."""
        dropdown = self.page.locator("p-dropdown").nth(index)
        dropdown.click()
        option = self.page.locator("li.p-dropdown-item", has_text="%s - " % value)
        if not option.count():
            raise PortalError("%s %s not offered" % (what, value))
        option.first.click()
        print("%-40s %r" % (what, dropdown.locator(".p-dropdown-label").inner_text().strip()))

    def fill_01_receiver(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        # A notice to check that the RFC is active at the SAT.
        self.page.get_by_role("button", name="Aceptar").click()
        # The portal looks up the RFC and fills the name, the postal code and the email it has for it,
        # so wait for it before typing them.
        with self.page.expect_response(lambda response: "Catalogos/Cliente/" in response.url):
            self.type_field("rfc", self.receiver.rfc)
        self.type_field("razonSocial", self.receiver.name)
        self.type_field("cp", self.receiver.postal_code)
        self.type_field("correoElectronico", self.args.email)
        # The first dropdown is the regime, the second the Uso CFDI.
        self.choose(0, self.regime(), "regime")
        self.choose(1, self.args.uso, "Uso CFDI")
        self.show(
            ["input[formcontrolname=%s]" % name for name in ("rfc", "razonSocial", "cp", "correoElectronico")],
            width=40,
        )

    def fill_02_tickets(self):
        references = self.references()
        total = 0
        for reference in references:
            # The field has a mask, so fill() doesn't work. Clear it with the keyboard, and type from its
            # start, because a click leaves the cursor where it lands.
            field = self.page.locator("input.p-inputmask")
            field.click()
            field.press("Control+A")
            field.press("Backspace")
            field.press("Home")
            field.press_sequentially(reference, delay=40)
            typed = "".join(field.input_value().split())
            if typed != reference:
                raise PortalError("the reference field has %s instead of %s" % (typed, reference))
            with self.page.expect_response(lambda response: "Facturacion/ReferenciaTicket" in response.url) as answer:
                self.page.get_by_role("button", name="Agregar").click()
            result = answer.value.json()
            ticket = result.get("modelo")
            if not result.get("estado") or not ticket:
                raise PortalError("the portal did not accept the receipt: %s" % result.get("mensaje"))
            print("ticket: folio %s, %s, importe %.2f" % (ticket["folio"], ticket["fecha"], ticket["importe"]))
            for line in ticket.get("detalle") or []:
                print("  %s x %s = %.2f" % (line["cantidad"], line["articulo"], line["precioVenta"]))
            total += ticket["importe"]
            self.page.wait_for_timeout(1000)
        if len(references) > 1:
            print("total of the %d receipts: %.2f" % (len(references), total))

    def submit_01_invoice(self):
        # The button issues the invoice right away; there is no preview.
        with self.page.expect_response(
            lambda response: "Facturacion/Facturar" in response.url, timeout=120000
        ) as answer:
            self.page.locator("button:has-text('Facturar')").last.click()
        result = answer.value.json()
        self.page.wait_for_timeout(3000)
        invoice = result.get("modelo")
        if not result.get("estado") or not invoice:
            print("RESULT: %s" % result.get("mensaje"))
            return
        # The answer has the invoice's files, so keep them.
        if invoice.get("xmlString"):
            path = self.out / ("%s.xml" % invoice["uuid"])
            path.write_text(invoice["xmlString"], encoding="utf-8")
            print("XML: %s" % path)
        if invoice.get("pdf"):
            path = self.out / ("%s.pdf" % invoice["uuid"])
            path.write_bytes(base64.b64decode(invoice["pdf"]))
            print("PDF: %s" % path)
        print(
            "RESULT: issued %s-%s, UUID %s, total %s, sent to %s"
            % (
                invoice.get("serie"),
                invoice.get("folio"),
                invoice.get("uuid"),
                (invoice.get("comprobante") or {}).get("total"),
                self.args.email,
            )
        )


if __name__ == "__main__":
    sys.exit(Kiosko.main())
