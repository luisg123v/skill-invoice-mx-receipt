# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a restaurant receipt on Soft Restaurant's portal
(facturacion.softrestaurant.com/<slug>).

Many restaurants use Soft Restaurant; the receipt prints "Soft Restaurant" at the bottom
and a link such as mefacturo.com/<slug>, which redirects to the portal. Restaurants that
link mefacturo.mx use another portal, which this script doesn't cover (see
reference/soft-restaurant.md). Without --send it stops at the preview of the invoice.

Usage:
    soft_restaurant.py --slug mirestaurante --folio 123456 --codigo 123456ABCDEFGH \
        --total 285.00 --uso G03 [--send]
"""

import re
import sys

from portal import InvoicePortal, PortalDone, PortalError


class SoftRestaurant(InvoicePortal):
    name = "softrestaurant"
    url = "https://facturacion.softrestaurant.com/%s"
    customer_form = "#OpenModalAddCustomer "
    next_button = (
        "button:has-text('Siguiente'):visible, a:has-text('Siguiente'):visible"
    )
    customer_fields = [
        "#RFC",
        "#ListTaxRegimes",
        "#Name",
        "#Email",
        "#CustomerAddress_Code",
        "#usecode",
    ]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--slug", required=True, help="restaurant id in the portal URL"
        )
        parser.add_argument("--folio", required=True)
        parser.add_argument(
            "--codigo", required=True, help="CODIGO FACT printed above the QR"
        )
        parser.add_argument(
            "--total",
            required=True,
            help="the receipt's total, to compare with the CFDI",
        )

    def ticket(self):
        return "%s-%s" % (self.args.slug, self.args.folio)

    def visible_messages(self):
        messages = []
        for dialog in self.page.query_selector_all(
            ".modal, .swal2-popup, .alert-danger, .alert-warning, .alert-success"
        ):
            if dialog.is_visible():
                messages.append(" ".join(dialog.inner_text().split())[:400])
        return messages

    def fill_01_ticket(self):
        self.page.goto(
            self.url % self.args.slug, wait_until="networkidle", timeout=90000
        )
        self.page.fill("#folio", self.args.folio)
        self.page.fill("#unicCode", self.args.codigo)
        self.page.fill("#RFC", self.receiver.rfc)
        self.page.click("button[type=submit]:has-text('FACTURAR')")
        # The ticket's page shows a notice, the customer form or, for a saved customer,
        # the button to go on. A receipt already invoiced shows its CFDI instead, and
        # one the portal doesn't find gets a message under the form ("No se encontró el
        # ticket").
        invoiced_notice = ":text('Ya puedes descargar tu factura')"
        self.wait_for_answer(
            "#acceptFeedback, %s#Name, %s, %s"
            % (self.customer_form, self.next_button, invoiced_notice),
            errors=["#captchamessage:not(:empty)", ".alert-danger", ".swal2-popup"],
        )
        if self.page.is_visible(invoiced_notice):
            raise PortalDone("already invoiced: %s" % self.text()[:300])

    def fill_02_customer(self):
        # A notice about CFDI 4.0 opens first; then, for an RFC the restaurant doesn't
        # know yet, a customer form. Its visible "Guardar" is a link; the two Guardar
        # buttons are hidden.
        if self.page.is_visible("#acceptFeedback"):
            self.page.click("#acceptFeedback")
            self.wait_for_answer("%s#Name, %s" % (self.customer_form, self.next_button))
        if not self.page.is_visible(self.customer_form + "#Name"):
            print(
                "WARNING: no customer form; the portal reused a saved customer. Check "
                "the preview."
            )
            return
        self.page.select_option(self.customer_form + "#ListTaxRegimes", self.regime())
        self.page.fill(self.customer_form + "#Name", self.receiver.name)
        self.page.fill(self.customer_form + "#Email", self.args.email)
        self.page.fill(
            self.customer_form + "#CustomerAddress_Code", self.receiver.postal_code
        )
        # The Uso CFDI options load after the regime is chosen.
        self.select_offered(self.customer_form + "#usecode", self.args.uso, "Uso CFDI")
        self.show(
            [self.customer_form + selector for selector in self.customer_fields],
            width=44,
        )
        self.page.click(self.customer_form + "a[onclick='enviarUserForm()']")
        self.wait_for_answer(self.next_button)

    def fill_03_preview(self):
        self.page.locator(self.next_button).first.click()
        self.wait_for_answer("text=Previsualizar factura")
        # A saved customer skips the form, so the portal may use an old Uso CFDI. Check
        # the receiver in the preview's XML tab and stop on any difference.
        self.page.locator(
            "a:has-text('XML'):visible, li:has-text('XML'):visible"
        ).first.click()
        xml = ""
        for _attempt in range(60):
            frames = [
                frame.inner_text("body")
                for frame in self.page.frames
                if frame.url != "about:blank"
            ]
            xml = " ".join(" ".join(frames).split())
            if "Receptor" in xml:
                break
            self.page.wait_for_timeout(500)
        expected = {
            "Rfc": self.receiver.rfc,
            "UsoCFDI": self.args.uso,
            "DomicilioFiscalReceptor": self.receiver.postal_code,
            "RegimenFiscalReceptor": self.regime(),
        }
        receptor = xml[xml.find("Receptor") :][:600]
        wrong = [
            key
            for key, value in expected.items()
            if '%s="%s"' % (key, value) not in receptor
        ]
        if "Receptor" not in xml or wrong:
            raise PortalError(
                "the preview XML does not match on %s: %s"
                % (wrong or "Receptor", receptor[:400])
            )
        print("XML receiver OK: %s" % receptor[:300])
        # The restaurant's system can round the unit price and add a cent, so compare
        # the total with the receipt before stamping.
        total = re.search(r'\bTotal="([\d.]+)"', xml)
        print(
            "XML total: %s, receipt: %s"
            % (total.group(1) if total else "?", self.args.total)
        )
        if not total or abs(float(total.group(1)) - float(self.args.total)) > 0.005:
            raise PortalError(
                "the CFDI total differs from the receipt; ask before stamping"
            )

    def submit_01_invoice(self):
        self.page.locator(
            "button:has-text('Facturar'):visible, a:has-text('Facturar'):visible"
        ).first.click()
        # It asks "¿Estás seguro que deseas generar la factura?" in an HTML modal.
        confirm_button = self.page.locator(
            "button:has-text('Aceptar'):visible, a:has-text('Aceptar'):visible"
        )
        stamping_notice = self.page.locator("text=Facturando...")
        confirm_button.or_(stamping_notice).first.wait_for(timeout=30000)
        if confirm_button.count():
            confirm_button.last.click()
        # Stamping shows "Facturando..." for well over 15 seconds; wait for it to end.
        stamping_notice.wait_for(timeout=30000)
        stamping_notice.wait_for(state="hidden", timeout=180000)
        print("RESULT: %s | url %s" % (self.visible_messages(), self.page.url))


if __name__ == "__main__":
    sys.exit(SoftRestaurant.main())
