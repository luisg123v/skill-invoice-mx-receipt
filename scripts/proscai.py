# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a receipt of a store that uses Proscai, on cw.pos.mx.

Stores such as Promoda, Mumuso and Aldo Conti print "Obtenga su factura con su
celular", a QR and a "Clave para facturar" of 12 consonants in groups of three. Each
store has its own address on the portal, e.g. cw.pos.mx/factura/mumuso. The portal
requests the invoice as soon as the receiver's form is sent, with no preview.

Usage:
    proscai.py --tienda mumuso --clave "BCD FGH JKL MNP" --uso S01 [--send]
"""

import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from portal import InvoicePortal, PortalDone, PortalError, pattern_argument


class Proscai(InvoicePortal):
    name = "proscai"
    url = "https://cw.pos.mx/factura/%s"
    receiver_fields = [
        "input[name=rfc]",
        "input[name=primerApellido]",
        "input[name=segundoApellido]",
        "input[name=nombre]",
        "input[name=cp]",
        "input[name=email]",
    ]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--tienda",
            required=True,
            help="the store's address on the portal, e.g. multibrand for Promoda",
        )
        parser.add_argument(
            "--clave",
            required=True,
            type=pattern_argument(
                # Consonants, in four groups of three with or without a space.
                pattern=r"(?i)[b-df-hj-np-tv-z]{3}(?: ?[b-df-hj-np-tv-z]{3}){3}",
                error="the key should be 12 consonants",
            ),
            help='"Clave para facturar"',
        )

    def ticket(self):
        """Return the store and the key without spaces, e.g. "mumuso_BCDFGHJKLMNP"."""
        return "%s_%s" % (self.args.tienda, self.clave())

    def clave(self):
        """Return the key as the portal takes it, without spaces."""
        return self.args.clave.replace(" ", "").upper()

    def pick(self, index, text):
        """Pick the option of a menu of the form that starts with a text.

        The menus are searchable lists, not selects, and typing filters their options.
        """
        menu = self.page.locator("input[id^=react-select][id$=-input]").nth(index)
        menu.fill(text)
        option = self.page.locator("[id*=-option-]", has_text=text).first
        try:
            option.wait_for(timeout=15000)
        except PlaywrightTimeoutError:
            raise PortalError("option %r not offered" % text)
        option.click()

    def chosen(self):
        """Return the options chosen in the menus of the form."""
        return self.page.locator("[class*=singleValue]").all_inner_texts()

    def fill_01_clave(self):
        self.page.goto(
            self.url % self.args.tienda, wait_until="networkidle", timeout=90000
        )
        self.page.fill("input[name=clave]", self.clave())
        self.page.click("button[type=submit]")
        # A key already used shows "¡Tu factura está en proceso!", or "Descarga tus
        # comprobantes" once the CFDI is issued, instead of the form. A wrong key opens
        # a dialog ("Clave inválida") on the same page.
        self.wait_for_answer(
            expected=(
                "input[name=rfc], :text('Tu factura está en proceso'), "
                ":text('Descarga tus comprobantes')"
            ),
            errors=["[role=dialog] [id^=headlessui-dialog-panel]"],
        )
        if not self.page.is_visible("input[name=rfc]"):
            raise PortalDone("already requested: %s" % self.text()[:300])

    def fill_02_receiver(self):
        values = [
            self.receiver.rfc,
            self.receiver.paternal_last_name,
            self.receiver.maternal_last_name,
            self.receiver.first_names,
            self.receiver.postal_code,
            self.args.email,
        ]
        for selector, value in zip(self.receiver_fields, values):
            self.page.fill(selector, value)
        self.pick(0, self.regime() + " - ")
        # The uses load after the regime.
        self.pick(1, self.args.uso + " - ")
        self.show(self.receiver_fields, width=28)
        chosen = self.chosen()
        print("%-28s %r" % ("menus", chosen))
        chosen_codes = [value.split(" - ")[0] for value in chosen]
        if chosen_codes != [self.regime(), self.args.uso]:
            raise PortalError("the menus show %r" % chosen)

    def submit_01_invoice(self):
        self.page.click("button[type=submit]")
        # It answers "¡Solicitud realizada!" and emails the CFDI within 24 hours.
        self.wait_for_answer(
            "text=Solicitud realizada",
            errors=["[role=dialog] [id^=headlessui-dialog-panel]"],
            timeout=120,
        )
        print("RESULT: %s" % self.text()[:600])


if __name__ == "__main__":
    sys.exit(Proscai.main())
