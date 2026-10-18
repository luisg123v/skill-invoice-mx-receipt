# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""Invoice a Walmart receipt on facturacion-clientes.walmart.com.

Usage:
    walmart.py --tc 1234567890123456789012 --tr 01234 --forma "Tarjeta de crédito" --uso S01 [--send]
"""

import sys

from portal import InvoicePortal, PortalError


class Walmart(InvoicePortal):
    name = "walmart"
    url = "https://facturacion-clientes.walmart.com/"
    payment_methods = [
        "Efectivo",
        "Cheque nominativo",
        "Transferencia",
        "Tarjeta de crédito",
        "Monedero electrónico",
        "Vales de despensa",
        "Tarjeta de débito",
    ]
    receiver_fields = [
        "#rfc",
        "[id='Razón Social']",
        "[id='Código Postal']",
        "#billing_email_input",
        "[id='Régimen Fiscal']",
        "[id='Uso Factura']",
    ]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--tc", required=True, help="TC#, the receipt number (22 digits)")
        parser.add_argument("--tr", required=True, help="TR#, the transaction (5 digits)")
        parser.add_argument(
            "--forma", required=True, choices=cls.payment_methods, help="payment method, as the portal names it"
        )

    def ticket(self):
        return self.args.tc

    def close_notice(self):
        if self.page.is_visible("#popup_btn_accept"):
            self.page.click("#popup_btn_accept")
            self.page.wait_for_timeout(1000)

    def click_continue(self):
        self.page.locator("button:has-text('Continuar'):visible").first.click()

    def fill_01_ticket(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=60000)
        self.page.wait_for_timeout(2000)
        self.close_notice()
        # Single-page app: /ticket opened directly lands on the home page.
        self.page.locator("a:has-text('Obtener factura')").first.click()
        self.page.wait_for_timeout(4000)
        self.close_notice()
        self.page.fill("#membershipOrRFC", self.receiver.rfc)
        self.page.fill("#postalCode", self.receiver.postal_code)
        self.page.fill("#ticketNumber", self.args.tc)
        self.page.fill("#transactionNumber", self.args.tr)
        self.page.click("#form_btn_accept")
        self.page.wait_for_timeout(10000)
        if "/address" not in self.page.url:
            raise PortalError("the portal did not accept the receipt: %s" % self.text()[:600])
        # "será necesario capturar nuevamente su información fiscal en cada solicitud"
        self.close_notice()

    def fill_02_receiver(self):
        # RFC, postal code, state and municipality come prefilled; the address is optional.
        self.page.fill("[id='Razón Social']", self.receiver.name)
        self.page.fill("#billing_email_input", self.args.email)
        self.page.select_option("[id='Régimen Fiscal']", self.regime())
        # The Uso Factura options load after the regime.
        self.page.wait_for_timeout(3000)
        self.select_offered("[id='Uso Factura']", self.args.uso, "Uso CFDI")
        self.page.wait_for_timeout(800)
        self.show(self.receiver_fields, width=24)
        if (
            self.page.input_value("#rfc") != self.receiver.rfc
            or self.page.input_value("[id='Código Postal']") != self.receiver.postal_code
        ):
            raise PortalError("the prefilled RFC or postal code is not the receiver's")

    def submit_01_confirm(self):
        self.page.click("#form_btn_accept")
        self.page.wait_for_timeout(3000)
        # An "Alerta" modal asks "¿Están correctos todos sus datos?" with Cerrar / Continuar.
        self.click_continue()
        self.page.wait_for_timeout(8000)
        if "/payment" not in self.page.url:
            raise PortalError("the payment step did not open: %s" % self.text()[:600])

    def submit_02_payment(self):
        select = self.page.locator("select:visible").first
        labels = [option.inner_text().strip() for option in select.locator("option").all()]
        if self.args.forma not in labels:
            raise PortalError("payment method %r not offered; options: %s" % (self.args.forma, labels))
        select.select_option(label=self.args.forma)
        self.page.wait_for_timeout(800)
        self.click_continue()
        self.page.wait_for_timeout(15000)
        confirm = self.page.locator("button:has-text('Continuar'):visible, button:has-text('Aceptar'):visible")
        if "/payment" in self.page.url and confirm.count():
            print("confirmation: %s" % self.text()[:300])
            confirm.last.click()
            self.page.wait_for_timeout(15000)

    def submit_03_invoice(self):
        # "Enviar a correo electrónico" comes selected, with the email of the receiver step;
        # "Facturar" stamps the invoice.
        if "/invoiceSelection" not in self.page.url:
            raise PortalError("the last step did not open: %s" % self.text()[:600])
        inputs = self.page.locator("input[type=text]:visible, input[type=email]:visible").all()
        emails = [field.input_value() for field in inputs]
        if self.args.email not in emails:
            raise PortalError("the email to send to is %s, not %s" % (emails, self.args.email))
        self.page.locator("button:has-text('Facturar'):visible").first.click()
        self.page.wait_for_timeout(15000)
        print("url: %s" % self.page.url)
        print("RESULT: %s" % self.text()[:1200])


if __name__ == "__main__":
    sys.exit(Walmart.main())
