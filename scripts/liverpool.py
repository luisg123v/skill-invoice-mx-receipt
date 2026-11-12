# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a Liverpool receipt on facturacionclientes.liverpool.com.mx.

Usage:
    liverpool.py --codigo "ABCDE FGH1J KLMNO PQRST" --total 100.00 --uso S01 [--send]
"""

import sys

from portal import InvoicePortal, PortalError, pattern_argument


class Liverpool(InvoicePortal):
    name = "liverpool"
    url = "https://facturacionclientes.liverpool.com.mx/generarFactura/&uid=liverpool"

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--codigo",
            required=True,
            type=pattern_argument(
                pattern=r"(?:\s*[A-Za-z0-9]){20}\s*",
                error="the invoicing code should have 20 letters and digits",
            ),
            help='the 20 characters under "Código de facturación", in groups of 5',
        )
        parser.add_argument(
            "--total", required=True, help="the receipt's total, with cents"
        )

    # The portal's error messages; its notes are alerts too, in another color.
    error_message = ".MuiAlert-colorError"

    def billing_code(self):
        """Return the invoicing code without the spaces between its groups."""
        return "".join(self.args.codigo.split()).upper()

    def ticket(self):
        return self.billing_code()

    def choose(self, name, value, what):
        """Pick an option of a dropdown, stopping when the portal doesn't offer it."""
        # The list opens from the element next to the hidden input that keeps the value.
        self.page.locator("input[name=%s]" % name).locator("xpath=..").locator(
            "[role=combobox]"
        ).click()
        options = self.page.locator("li[role=option]")
        options.first.wait_for(timeout=10000)
        offered = options.evaluate_all("items => items.map(item => item.dataset.value)")
        if value not in offered:
            self.page.keyboard.press("Escape")
            raise PortalError("%s %s not offered; options: %s" % (what, value, offered))
        self.page.click("li[role=option][data-value='%s']" % value)
        self.page.wait_for_timeout(1000)

    def fill_01_ticket(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        self.page.fill("input[name=billingCode]", self.billing_code())
        self.page.fill("input[name=amount]", self.args.total)
        self.page.click("button:has-text('Buscar ticket')")
        self.wait_for_answer("text=Ticket encontrado", errors=[self.error_message])
        self.show(["input[name=billingCode]", "input[name=amount]"])

    def fill_02_receiver(self):
        self.page.fill("input[name=rfc]", self.receiver.rfc)
        self.page.click("button:has-text('Continuar') >> nth=0")
        # When the RFC has invoiced before, the portal lists the data it keeps for it,
        # and the fields stay disabled until one is selected. The script then writes
        # every field again, because that data can be out of date.
        name_field_enabled = "input[name=firstName]:enabled"
        self.wait_for_answer(
            ":text('Seleccionar'), %s" % name_field_enabled,
            errors=[self.error_message],
        )
        if self.page.is_visible(":text('Seleccionar')"):
            print("SAVED DATA: %s" % self.text(".MuiModal-root"))
            self.page.click("text=Seleccionar >> nth=0")
            self.page.locator(name_field_enabled).wait_for()
        self.page.check("input[name=persona][value=fisica]")
        self.choose("regime", self.regime(), "Régimen fiscal")
        # The Uso CFDI options depend on the regime.
        self.choose("useCFDI", self.args.uso, "Uso CFDI")
        self.page.fill("input[name=firstName]", self.receiver.first_names)
        self.page.fill("input[name=paternalName]", self.receiver.paternal_last_name)
        self.page.fill("input[name=maternalName]", self.receiver.maternal_last_name)
        self.page.fill("input[name=postalCode]", self.receiver.postal_code)
        self.page.fill("input[name=email]", self.args.email)
        fields = [
            "rfc",
            "regime",
            "useCFDI",
            "firstName",
            "paternalName",
            "maternalName",
            "postalCode",
            "email",
        ]
        self.show(["input[name=%s]" % name for name in fields], width=26)

    def fill_03_confirmation(self):
        # The last "Continuar" only opens a summary, with "Corregir datos" and "Generar
        # factura".
        self.page.click("button:has-text('Continuar') >> nth=-1")
        self.page.wait_for_selector(
            "[role=dialog] button:has-text('Generar factura')", timeout=20000
        )
        print("SUMMARY: %s" % self.text("[role=dialog]"))

    def submit_01_invoice(self):
        generate_button = self.page.locator(
            "[role=dialog] button:has-text('Generar factura')"
        )
        generate_button.click()
        generate_button.wait_for(state="hidden", timeout=120000)
        self.page.wait_for_load_state("networkidle", timeout=120000)
        # The portal finds a receipt already invoiced like any other, and only says so
        # here.
        if "ya fue facturado" in self.text():
            raise PortalError(
                "the receipt was already invoiced: Este código ya fue facturado"
            )
        print("RESULT: %s" % self.text()[:1500])


if __name__ == "__main__":
    sys.exit(Liverpool.main())
