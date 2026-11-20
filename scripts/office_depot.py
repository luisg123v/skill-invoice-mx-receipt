# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice an Office Depot receipt on facturacion.officedepot.com.mx.

The portal asks for the receipt's ITU, the 30 characters printed at its foot, and its
total. Once validated, it keeps the receipt "in use" for half an hour, and answers
another browser that tries it "FES002-ITU NO DISPONIBLE". So the dry run leaves the
form with "Salir" and confirms it, which frees the receipt for the next run.

Usage:
    office_depot.py --itu 2026111700123011000123456ABCD1 --total 100.00 --uso S01 \
        [--send]
"""

import sys

from portal import InvoicePortal, PortalDone, PortalError, pattern_argument


class OfficeDepot(InvoicePortal):
    name = "office_depot"
    url = "https://facturacion.officedepot.com.mx/#/invoices"
    # Answers 403 to IPs outside Mexico.
    blocks_foreign_ips = True
    # The portal's messages start with a code, e.g. "FES002-ITU NO DISPONIBLE...".
    errors = [
        ":text('FES0')",
        "*:has(> mat-icon:text-is('error_outline'))",
        "mat-error",
        "mat-dialog-container",
    ]
    receiver_fields = [
        "input[formcontrolname=rfc]",
        "input[formcontrolname=zipCode]",
        "input[formcontrolname=businessName]",
        "input[formcontrolname=email]",
    ]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--itu",
            required=True,
            type=pattern_argument(
                pattern=r"[0-9A-Z]{30}", error="the ITU should be its 30 characters"
            ),
            help="ITU, at the foot of the receipt",
        )
        parser.add_argument("--total", required=True, help='"Total", with cents')

    def ticket(self):
        return self.args.itu

    def pick(self, name, code):
        """Pick the option of a menu by its code, e.g. "605" for "605 - Sueldos y..."."""
        self.page.click("mat-select[formcontrolname=%s]" % name)
        options = self.page.locator("mat-option").filter(visible=True)
        options.first.wait_for(timeout=15000)
        texts = [" ".join(text.split()) for text in options.all_inner_texts()]
        matching = [
            index for index, text in enumerate(texts) if text.split(" - ")[0] == code
        ]
        if not matching:
            raise PortalError("%s %s not offered; options: %s" % (name, code, texts))
        options.nth(matching[0]).click()
        # The menu's options stay on the page while it closes.
        options.first.wait_for(state="hidden")
        return self.chosen(name)

    def chosen(self, name):
        """Return the option a menu shows."""
        return " ".join(
            self.page.inner_text(
                "mat-select[formcontrolname=%s] .mat-mdc-select-value" % name
            ).split()
        )

    def fill_01_ticket(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        welcome = self.page.get_by_role("button", name="Omitir")
        if welcome.count():
            welcome.click()
        self.page.fill("input[formcontrolname=orderNumber]", self.args.itu)
        self.page.fill("input[formcontrolname=amount]", self.args.total)
        # A receipt the portal doesn't find shows no message on the page; only the
        # answer of the validation says so ("Error al validar el ITU").
        with self.page.expect_response(lambda r: "validateItu" in r.url) as response:
            self.page.click("button:has-text('Validar y Continuar')")
        answer = response.value.json()
        if not answer.get("status"):
            raise PortalError("the portal answered: %s" % answer.get("msg"))
        self.wait_for_answer(
            "input[formcontrolname=rfc], :text('previamente facturado')",
            errors=self.errors,
        )
        receiver_form = self.page.locator("input[formcontrolname=rfc]").filter(
            visible=True
        )
        if not receiver_form.count():
            raise PortalDone("already invoiced: %s" % self.text()[:300])

    def fill_02_receiver(self):
        self.page.fill("input[formcontrolname=rfc]", self.receiver.rfc)
        # The button next to the RFC looks it up; the fields below are written either
        # way.
        self.page.click(
            "mat-form-field:has(input[formcontrolname=rfc]) button:has-text('search')"
        )
        self.page.wait_for_load_state("networkidle")
        # The RFC of a person has 13 characters, and a company's 12.
        person = self.pick("personType", "F" if len(self.receiver.rfc) == 13 else "M")
        regime = self.pick("fiscalRegime", self.regime())
        usage = self.pick("cfdiUse", self.args.uso)
        self.page.fill("input[formcontrolname=zipCode]", self.receiver.postal_code)
        self.page.fill("input[formcontrolname=businessName]", self.receiver.name)
        self.page.fill("input[formcontrolname=email]", self.args.email)
        self.show(self.receiver_fields, width=36)
        menus = [("persona", person), ("regime", regime), ("uso", usage)]
        for label, value in menus:
            print("%-36s %r" % (label, value))
        if not self.args.send:
            self.release()

    def release(self):
        """Leave the form, so that the portal stops keeping the receipt in use."""
        self.page.click("button:has-text('Salir')")
        # It asks "¿Deseas cancelar el proceso de facturación?" before leaving, and
        # frees the receipt only once that is confirmed.
        dialog = self.page.locator("mat-dialog-container")
        dialog.wait_for(timeout=15000)
        with self.page.expect_response(lambda r: "deleteItus" in r.url) as response:
            dialog.get_by_role("button", name="Confirmar").click()
        if not response.value.ok:
            raise PortalError(
                "the portal didn't free the receipt (%s); the next run has to wait "
                "half an hour" % response.value.status
            )
        print("receipt freed for the next run")

    def submit_01_invoice(self):
        self.page.click("button:has-text('Facturar')")
        # The third step, "Tu factura", replaces the form.
        form = self.page.locator("input[formcontrolname=rfc]").filter(visible=True)
        for _attempt in range(240):
            if not form.count():
                break
            for error in self.errors:
                message = self.page.locator(error).filter(visible=True)
                if message.count():
                    raise PortalError(" ".join(message.first.inner_text().split()))
            self.page.wait_for_timeout(500)
        else:
            raise PortalError("the portal didn't answer: %s" % self.text()[:600])
        print("RESULT: %s" % self.text()[:1200])


if __name__ == "__main__":
    sys.exit(OfficeDepot.main())
