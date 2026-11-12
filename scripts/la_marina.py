# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a La Marina receipt on servicios.lamarina.com.mx/Facturacion.

The receipt's "Folio" is the terminal and the transaction, separated by a dash (101-2345
is terminal 101, transaction 2345). The portal doesn't look the receipt up before
issuing, and it asks for the receiver's mobile phone and full address, which go in the
configuration.

Usage:
    la_marina.py --tienda "La Marina Zapotlán" --folio 101-2345 --fecha 2026-11-01 \
        --forma-pago 04 --uso S01 [--send]
"""

import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from portal import InvoicePortal, PortalDone, PortalError, pattern_argument


class LaMarina(InvoicePortal):
    name = "la_marina"
    url = "https://servicios.lamarina.com.mx/Facturacion"
    required_receiver_fields = (
        "mobile_phone",
        "state",
        "municipality",
        "locality",
        "neighborhood",
        "street",
        "exterior_number",
    )

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--tienda", required=True, help='the store, as on the receipt\'s "Tienda"'
        )
        parser.add_argument(
            "--folio",
            required=True,
            type=pattern_argument(
                pattern=r"\s*(\d+)\s*-\s*(\d+)\s*",
                error="the folio should be <terminal>-<transaction>, such as 101-2345",
            ),
            help="<terminal>-<transaction>, such as 101-2345",
        )
        parser.add_argument(
            "--fecha", required=True, help="the purchase date, yyyy-mm-dd"
        )
        parser.add_argument(
            "--forma-pago",
            required=True,
            help="SAT code: 01 cash, 04 credit card, 28 debit card",
        )

    def ticket(self):
        return "-".join(self.args.folio)

    def next_section(self, number):
        """Press "Continuar" in a section, which checks it and opens the next one."""
        self.page.click("#fi-acc-%d button:has-text('Continuar')" % number)
        try:
            self.page.locator("#fi-acc-%d" % (number + 1)).wait_for(timeout=15000)
        except PlaywrightTimeoutError:
            raise PortalError(
                "the portal did not accept the section %d: %s"
                % (number, self.text("#fi-acc-%d" % number))
            )

    def options(self, select_id):
        """Return the value, the text and the names of each option of a select.

        Some options show a name other than the catalog's, which they keep in
        data-original ("La Marina San Fernando" and "San Fernando"), so both count.
        """
        options = []
        for option in self.page.locator("#%s option" % select_id).all():
            value = option.get_attribute("value") or ""
            # The first option only asks to choose, and its value can be "null".
            if value.strip().lower() in ("", "null", "undefined"):
                continue
            names = (
                option.text_content(),
                option.get_attribute("data-original"),
                value,
            )
            names = {self.comparable_text(name) for name in names if name}
            options.append((value, option.text_content().strip(), names))
        return options

    def option_by_code(self, select_id, code):
        """Return the value of the option of a SAT code, such as "S01" or "04"."""
        for value, _text, _names in self.options(select_id):
            if value.startswith(code + "-"):
                return value
        raise PortalError("%s not offered in %s" % (code, select_id))

    def choose(self, select_id, wanted, what):
        """Pick an option once the cascade loads it; stop when the portal lacks it."""
        for _attempt in range(20):
            options = self.options(select_id)
            if options:
                break
            self.page.wait_for_timeout(500)
        wanted_name = self.comparable_text(wanted)
        values = [value for value, _text, names in options if wanted_name in names]
        if len(values) != 1:
            offered = [text for _value, text, _names in options]
            raise PortalError(
                "%s %r not offered; options: %s" % (what, wanted, offered)
            )
        # The select is hidden behind a search field, which follows its changes.
        # Choosing an option loads the next select of the address.
        self.page.select_option("#" + select_id, values[0], force=True)
        self.page.wait_for_timeout(1000)

    def fill_01_purchase(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        # A notice about online purchases covers the page.
        if self.page.is_visible("button:has-text('Aceptar')"):
            self.page.click("button:has-text('Aceptar')")
        self.page.click("text=Tienda departamental")
        self.page.click("text=Persona física")

    def fill_02_receiver(self):
        self.page.fill("#inputName", self.receiver.first_names)
        self.page.fill("#inputLastName", self.receiver.last_names)
        self.page.fill("#inputRFC", self.receiver.rfc)
        self.page.fill("#inputEmail", self.args.email)
        self.choose("inputRegimenF", self.regime(), "Régimen fiscal")
        usage = self.option_by_code("inputCFDI", self.args.uso)
        self.choose("inputCFDI", usage, "Uso CFDI")
        self.page.fill("#inputCel", self.receiver.mobile_phone)
        self.show(
            [
                "#inputName",
                "#inputLastName",
                "#inputRFC",
                "#inputEmail",
                "#inputRegimenF",
                "#inputCFDI",
                "#inputCel",
            ]
        )
        self.next_section(1)

    def fill_03_address(self):
        self.page.select_option("#inputPaisCatalogo", "MEX")
        self.choose("inputEstado", self.receiver.state, "Estado")
        self.choose("inputMunicipio", self.receiver.municipality, "Municipio")
        self.choose("inputLocalidad", self.receiver.locality, "Localidad")
        self.choose("inputCodigoPostal1", self.receiver.postal_code, "Código postal")
        self.choose("inputColonia", self.receiver.neighborhood, "Colonia")
        self.page.fill("#inputCalle", self.receiver.street)
        self.page.fill("#inputNumOut", self.receiver.exterior_number)
        self.show(
            [
                "#inputEstadoBuscar",
                "#inputMunicipioBuscar",
                "#inputLocalidadBuscar",
                "#inputCodigoPostal1Buscar",
                "#inputColoniaBuscar",
                "#inputCalle",
                "#inputNumOut",
            ]
        )
        self.next_section(2)

    def fill_04_receipt(self):
        terminal, transaction = self.args.folio
        self.choose("inputStore", self.args.tienda, "Tienda")
        self.page.fill("#inputTerminal", terminal)
        self.page.fill("#inputTransaction", transaction)
        self.page.fill("#inputDate", self.args.fecha)
        self.page.dispatch_event("#inputDate", "change")
        self.page.wait_for_timeout(1000)
        # A date out of the invoicing period opens a notice, and the form stops there.
        if self.page.is_visible(".swal2-popup"):
            raise PortalError(
                "the portal rejected the date: %s" % self.text(".swal2-popup")
            )
        payment = self.option_by_code("inputPayment", self.args.forma_pago)
        self.choose("inputPayment", payment, "Forma de pago")
        self.show(
            [
                "#inputStoreBuscar",
                "#inputTerminal",
                "#inputTransaction",
                "#inputDate",
                "#inputPayment",
            ]
        )

    def fill_05_review(self):
        """Open the portal's summary, the last step before it issues the invoice."""
        self.page.click("#btn-sendit")
        # Any other notice is the portal's reason not to go on.
        self.wait_for_answer(
            ".swal2-popup:has-text('Confirmar datos')", errors=[".swal2-popup"]
        )
        print("SUMMARY: %s" % self.text(".swal2-popup"))

    def submit_01_invoice(self):
        self.page.click(".swal2-confirm:has-text('Generar')")
        self.page.wait_for_selector(
            ".swal2-popup:not(:has-text('Generando'))", timeout=120000
        )
        self.page.wait_for_timeout(1000)
        result = self.text(".swal2-popup")
        if "ya ha sido facturada" in result:
            raise PortalDone("already invoiced: %s" % result)
        if "Factura Enviada" not in result:
            raise PortalError("the portal did not issue the invoice: %s" % result)
        print("RESULT: %s" % result)


if __name__ == "__main__":
    sys.exit(LaMarina.main())
