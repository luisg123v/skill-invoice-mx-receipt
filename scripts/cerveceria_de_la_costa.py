# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a Cervecería de la Costa receipt on its portal.

The portal is facturacion.cerveceriadelacosta.com. The receipt's "Referencia", under
"Facturación en Línea", is the ticket number. The portal finds the ticket before
issuing, and fills the payment method with the sale's. A ticket number with a digit of
the folio changed is usually another person's ticket of the same day, so the script also
checks each ticket's total. Several tickets can go on one invoice, by repeating --ticket
and --total in the same order.

Usage:
    cerveceria_de_la_costa.py --ticket 1234567890123 --total 100.00 \
        [--ticket ... --total ...] --uso S01 [--send]
"""

import sys

from portal import InvoicePortal, PortalDone, PortalError, pattern_argument


class CerveceriaDeLaCosta(InvoicePortal):
    name = "cerveceria_de_la_costa"
    url = "https://facturacion.cerveceriadelacosta.com/facturar"

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--ticket",
            required=True,
            action="append",
            type=pattern_argument(
                pattern=r"\d+", error='the ticket should be the digits of "Referencia"'
            ),
            help='the digits after "Referencia", under "Facturación en Línea"; '
            "repeat it for each ticket",
        )
        parser.add_argument(
            "--total",
            required=True,
            action="append",
            help="the receipt's total, with cents; one for each --ticket, in order",
        )

    def __init__(self, args, config):
        if len(args.ticket) != len(args.total):
            raise SystemExit(
                "ABORT: pass one --total for each --ticket (got %d --ticket and "
                "%d --total)" % (len(args.ticket), len(args.total))
            )
        super().__init__(args, config)

    def ticket(self):
        return "-".join(self.args.ticket)

    def pick(self, button, code, what):
        """Pick an option of a dropdown by its code, stopping when it isn't offered."""
        self.page.click(button)
        options = self.page.locator("[role=option]")
        options.first.wait_for(timeout=10000)
        texts = [text.strip() for text in options.all_inner_texts()]
        matches = [i for i, text in enumerate(texts) if text.startswith(code + " - ")]
        if not matches:
            self.page.keyboard.press("Escape")
            raise PortalError("%s %s not offered; options: %s" % (what, code, texts))
        options.nth(matches[0]).click()
        self.page.wait_for_timeout(800)

    def fill_01_receiver(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        # The search only starts with typed keys, not with a filled value.
        self.page.click("#rfcLookup")
        self.page.keyboard.type(self.receiver.rfc, delay=60)
        self.page.click("button:has-text('Buscar RFC')")
        self.page.wait_for_selector("#codigoPostal", timeout=60000)
        self.page.fill("#codigoPostal", self.receiver.postal_code)
        self.page.fill("#razonSocial", self.receiver.name)
        self.page.fill("#email", self.args.email)
        self.pick("#regimenFiscal", self.regime(), "Régimen fiscal")
        self.pick("#usoCfdi", self.args.uso, "Uso CFDI")
        self.show(["#tipoPersona", "#codigoPostal", "#razonSocial", "#email"])
        print("regime: %s" % self.text("#regimenFiscal"))
        print("uso: %s" % self.text("#usoCfdi"))
        self.page.click("button:has-text('Continuar a tickets')")

    def add_ticket(self, number, total):
        """Add a ticket, stopping unless the portal finds it with that total.

        The portal's ticket service answers with the ticket's date and amount, or with
        an error such as "El numero de ticket ya fue facturado y no se puede usar".
        """
        field = self.page.locator("input[placeholder='Numero de ticket']")
        field.wait_for(timeout=30000)
        field.fill(number)
        with self.page.expect_response(
            lambda response: "ValidaTicket" in response.url, timeout=60000
        ) as answer:
            self.page.click("button:has-text('Buscar ticket')")
        data = answer.value.json()
        if not answer.value.ok:
            message = "; ".join(error["Message"] for error in data.get("Errors", []))
            if "ya fue facturado" in message and len(self.args.ticket) == 1:
                raise PortalDone("ticket %s: %s" % (number, message))
            raise PortalError("ticket %s: %s" % (number, message or data))
        print(
            "TICKET: %s %s %.2f"
            % (number, data["DateTicket"][:10], data["ImporteTicket"])
        )
        if abs(data["ImporteTicket"] - float(total)) >= 0.005:
            raise PortalError(
                "ticket %s: its total is %.2f, not %s; check the ticket number"
                % (number, data["ImporteTicket"], total)
            )
        self.page.wait_for_timeout(1000)

    def fill_02_tickets(self):
        for number, total in zip(self.args.ticket, self.args.total):
            self.add_ticket(number, total)

    def fill_03_review(self):
        """Open the summary, the last step before the portal issues the invoice."""
        self.page.click("button:has-text('Continuar a confirmación')")
        self.page.locator("button:has-text('Solicitar factura')").wait_for(
            timeout=30000
        )
        # The payment method loads after the summary, from the tickets.
        self.page.locator("text=Cargando").wait_for(state="detached", timeout=30000)
        print("SUMMARY: %s" % self.text()[:1200])

    def submit_01_invoice(self):
        self.page.click("button:has-text('Solicitar factura')")
        # The portal says sending can take some minutes, and asks not to close the page.
        self.page.locator("text=Enviando solicitud").wait_for(timeout=30000)
        self.page.locator("text=Enviando solicitud").wait_for(
            state="detached", timeout=600000
        )
        print("RESULT: %s" % self.text()[:1200])


if __name__ == "__main__":
    sys.exit(CerveceriaDeLaCosta.main())
