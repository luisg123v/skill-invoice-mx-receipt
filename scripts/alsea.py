# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""Invoice an Alsea receipt (Starbucks and the other Alsea brands) on alsea.interfactura.com.

Usage:
    alsea.py --brand Starbucks --ticket 123456789 --tienda 12345 --fecha 23/10/2026 --uso G03 [--send]
"""

import sys

from portal import InvoicePortal, PortalError


class Alsea(InvoicePortal):
    name = "alsea"
    url = "https://alsea.interfactura.com/wwwroot?opc=%s"

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--brand", default="Starbucks", help="value of ?opc= on the portal, e.g. Dominos")
        parser.add_argument("--ticket", required=True)
        parser.add_argument("--tienda", required=True)
        parser.add_argument("--fecha", required=True, help="dd/mm/yyyy")

    def default_email(self):
        # Alsea emails links to the XML and the PDF instead of attaching them.
        return self.config.email_links or self.config.email

    def fill_01_ticket(self):
        self.page.goto(self.url % self.args.brand, wait_until="networkidle", timeout=90000)
        self.page.fill("#rfc", self.receiver.rfc)
        self.page.fill("#ticket", self.args.ticket)
        self.page.fill("#tienda", self.args.tienda)
        self.page.fill("#dtFecha", self.args.fecha)
        self.page.click("button[type=submit]")
        self.page.wait_for_timeout(6000)
        self.page.wait_for_load_state("networkidle", timeout=60000)
        if not self.page.query_selector("#persona"):
            raise PortalError("the portal did not accept the receipt (see DIALOG above, if any)")

    def fill_02_receiver(self):
        self.page.select_option("#persona", "FISICA")
        self.page.wait_for_timeout(1500)
        self.page.fill("#rfc", self.receiver.rfc)
        self.page.fill("#nombres", self.receiver.first_names)
        self.page.fill("#apellidos", self.receiver.last_names)
        self.page.fill("#codigoPostal", self.receiver.postal_code)
        self.page.select_option("#regimenFiscal", self.regime())
        # The Uso CFDI options load after the regime is chosen.
        self.page.wait_for_timeout(3000)
        self.select_offered("#usoCfdi", self.args.uso, "Uso CFDI")
        self.page.fill("#correoElectronico", self.args.email)
        self.page.wait_for_timeout(1000)
        self.show(
            [
                "#persona",
                "#rfc",
                "#nombres",
                "#apellidos",
                "#codigoPostal",
                "#regimenFiscal",
                "#usoCfdi",
                "#correoElectronico",
            ]
        )

    def submit_01_invoice(self):
        self.page.click("button:has-text('Enviar')")
        self.page.wait_for_timeout(9000)
        print("RESULT: %s" % self.text()[:600])


if __name__ == "__main__":
    sys.exit(Alsea.main())
