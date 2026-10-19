# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a restaurant receipt on Soft Restaurant's portal (facturacion.softrestaurant.com/<slug>).

Many restaurants use Soft Restaurant; the receipt prints "Soft Restaurant" at the bottom and a link
such as mefacturo.com/<slug>, which redirects to the portal. Restaurants that link mefacturo.mx
use another portal, which this script doesn't cover (see reference/soft-restaurant.md). Without
--send it stops at the preview of the invoice.

Usage:
    soft_restaurant.py --slug mirestaurante --folio 123456 --codigo 123456ABCDEFGH --total 285.00 \
        --uso G03 [--send]
"""

import re
import sys

from portal import InvoicePortal, PortalError


class SoftRestaurant(InvoicePortal):
    name = "softrestaurant"
    url = "https://facturacion.softrestaurant.com/%s"
    customer_form = "#OpenModalAddCustomer "
    customer_fields = ["#RFC", "#ListTaxRegimes", "#Name", "#Email", "#CustomerAddress_Code", "#usecode"]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--slug", required=True, help="restaurant id in the portal URL")
        parser.add_argument("--folio", required=True)
        parser.add_argument("--codigo", required=True, help="CODIGO FACT printed above the QR")
        parser.add_argument("--total", required=True, help="the receipt's total, to compare with the CFDI")

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
        self.page.goto(self.url % self.args.slug, wait_until="networkidle", timeout=90000)
        self.page.fill("#folio", self.args.folio)
        self.page.fill("#unicCode", self.args.codigo)
        self.page.fill("#RFC", self.receiver.rfc)
        self.page.click("button[type=submit]:has-text('FACTURAR')")
        try:
            self.page.wait_for_url("**/Invoice/Ticket**", timeout=60000)
        except Exception:
            raise PortalError(
                "the portal did not accept the receipt: %s" % (self.visible_messages() or self.text()[:400])
            )
        self.page.wait_for_timeout(4000)

    def fill_02_customer(self):
        # A notice about CFDI 4.0 opens first; then, for an RFC the restaurant doesn't know yet, a
        # customer form. Its visible "Guardar" is a link; the two Guardar buttons are hidden.
        if self.page.is_visible("#acceptFeedback"):
            self.page.click("#acceptFeedback")
            self.page.wait_for_timeout(1500)
        if not self.page.is_visible(self.customer_form + "#Name"):
            print("WARNING: no customer form; the portal reused a saved customer. Check the preview.")
            return
        self.page.select_option(self.customer_form + "#ListTaxRegimes", self.regime())
        self.page.wait_for_timeout(1500)
        self.page.fill(self.customer_form + "#Name", self.receiver.name)
        self.page.fill(self.customer_form + "#Email", self.args.email)
        self.page.fill(self.customer_form + "#CustomerAddress_Code", self.receiver.postal_code)
        self.page.select_option(self.customer_form + "#usecode", self.args.uso)
        self.show([self.customer_form + selector for selector in self.customer_fields], width=44)
        self.page.click(self.customer_form + "a[onclick='enviarUserForm()']")
        self.page.wait_for_timeout(6000)

    def fill_03_preview(self):
        self.page.locator("button:has-text('Siguiente'):visible, a:has-text('Siguiente'):visible").first.click()
        self.page.wait_for_timeout(6000)
        if not self.page.locator("text=Previsualizar factura").is_visible():
            raise PortalError("the preview did not open: %s" % self.visible_messages())
        # A saved customer skips the form, so the portal may use an old Uso CFDI. Check the receiver
        # in the preview's XML tab and stop on any difference.
        self.page.locator("a:has-text('XML'):visible, li:has-text('XML'):visible").first.click()
        self.page.wait_for_timeout(3000)
        frames = [frame.inner_text("body") for frame in self.page.frames if frame.url != "about:blank"]
        xml = " ".join(" ".join(frames).split())
        expected = {
            "Rfc": self.receiver.rfc,
            "UsoCFDI": self.args.uso,
            "DomicilioFiscalReceptor": self.receiver.postal_code,
            "RegimenFiscalReceptor": self.regime(),
        }
        receptor = xml[xml.find("Receptor") :][:600]
        wrong = [key for key, value in expected.items() if '%s="%s"' % (key, value) not in receptor]
        if "Receptor" not in xml or wrong:
            raise PortalError("the preview XML does not match on %s: %s" % (wrong or "Receptor", receptor[:400]))
        print("XML receiver OK: %s" % receptor[:300])
        # The restaurant's system can round the unit price and add a cent, so compare the total
        # with the receipt before stamping.
        total = re.search(r'\bTotal="([\d.]+)"', xml)
        print("XML total: %s, receipt: %s" % (total.group(1) if total else "?", self.args.total))
        if not total or abs(float(total.group(1)) - float(self.args.total)) > 0.005:
            raise PortalError("the CFDI total differs from the receipt; ask before stamping")

    def submit_01_invoice(self):
        self.page.locator("button:has-text('Facturar'):visible, a:has-text('Facturar'):visible").first.click()
        self.page.wait_for_timeout(3000)
        # It asks "¿Estás seguro que deseas generar la factura?" in an HTML modal.
        confirm = self.page.locator("button:has-text('Aceptar'):visible, a:has-text('Aceptar'):visible")
        if confirm.count():
            confirm.last.click()
        # Stamping shows "Facturando..." for well over 15 seconds; wait for it to end.
        self.page.wait_for_timeout(3000)
        for _ in range(60):
            if not self.page.locator("text=Facturando...").is_visible():
                break
            self.page.wait_for_timeout(2000)
        print("RESULT: %s | url %s" % (self.visible_messages(), self.page.url))


if __name__ == "__main__":
    sys.exit(SoftRestaurant.main())
