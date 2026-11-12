# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice an Alsea receipt (Starbucks and the other Alsea brands) on
alsea.interfactura.com.

Usage:
    alsea.py --brand Starbucks --ticket 123456789 --tienda 12345 --fecha 23/10/2026 \
        --uso G03 [--send]
"""

import sys

from portal import InvoicePortal


class Alsea(InvoicePortal):
    name = "alsea"
    url = "https://alsea.interfactura.com/wwwroot?opc=%s"

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--brand",
            default="Starbucks",
            help="value of ?opc= on the portal, e.g. Dominos",
        )
        parser.add_argument("--ticket", required=True)
        parser.add_argument("--tienda", required=True)
        parser.add_argument("--fecha", required=True, help="dd/mm/yyyy")

    def default_email(self):
        # Alsea emails links to the XML and the PDF instead of attaching them.
        return self.config.email_links or self.config.email

    def fill_01_ticket(self):
        self.page.goto(
            self.url % self.args.brand, wait_until="networkidle", timeout=90000
        )
        self.page.fill("#rfc", self.receiver.rfc)
        self.page.fill("#ticket", self.args.ticket)
        self.page.fill("#tienda", self.args.tienda)
        self.page.fill("#dtFecha", self.args.fecha)
        self.page.click("button[type=submit]")
        # The portal reports a receipt it doesn't take in a dialog.
        self.wait_for_answer("#persona")

    def fill_02_receiver(self):
        self.page.select_option("#persona", "FISICA")
        self.page.wait_for_timeout(1500)
        self.page.fill("#rfc", self.receiver.rfc)
        self.page.fill("#nombres", self.receiver.first_names)
        self.page.fill("#apellidos", self.receiver.last_names)
        self.page.fill("#codigoPostal", self.receiver.postal_code)
        self.page.select_option("#regimenFiscal", self.regime())
        # The Uso CFDI options load after the regime is chosen.
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
        self.wait_for_answer(
            "text=Muchas gracias por usar nuestro servicio", timeout=120
        )
        print("RESULT: %s" % self.text()[:600])


if __name__ == "__main__":
    sys.exit(Alsea.main())
