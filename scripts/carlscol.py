# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a receipt of Carlscol (Carl's Jr in Colima and Manzanillo) on carlscol.libellum.com.mx.

Usage:
    carlscol.py --ticket 12345 --fecha 25/10/2026 --monto 250.00 --sucursal Zentralia --uso G03 [--send]
"""

import sys

from portal import InvoicePortal, PortalError


class Carlscol(InvoicePortal):
    name = "carlscol"
    url = "https://carlscol.libellum.com.mx"
    # The ASP.NET page prefixes the id of every field.
    field_prefix = "#ctl00_cph_page_"
    ticket_fields = ["txt_rfcbusqueda", "txt_fechaticket", "txt_montototal", "txt_numeroticket", "ddl_sucursales"]
    receiver_fields = ["txt_razonsocial", "txt_email", "txt_cp", "ddl_regimenfiscal", "ddl_usocfdiconrfc"]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--ticket", required=True, help="Ticket# on the receipt")
        parser.add_argument("--fecha", required=True, help="dd/mm/yyyy; the receipt prints mm/dd/yyyy")
        parser.add_argument("--monto", required=True, help="TOTAL, e.g. 250.00")
        parser.add_argument("--sucursal", required=True, help="branch name as the portal lists it, e.g. Zentralia")

    def field(self, name):
        """Return the selector of a field, by its id without the page's prefix."""
        return self.field_prefix + name

    def branch_value(self):
        """Return the option value of the branch, stopping unless exactly one matches."""
        branches = {
            option.inner_text().strip(): option.get_attribute("value")
            for option in self.page.query_selector_all(self.field("ddl_sucursales") + " option")
        }
        match = [value for name, value in branches.items() if self.args.sucursal.lower() in name.lower()]
        if len(match) != 1:
            raise PortalError("branch %r not found once; options: %s" % (self.args.sucursal, list(branches)))
        return match[0]

    def fill_01_ticket(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        self.page.wait_for_timeout(2000)
        # A slideshow of instructions covers the form.
        if self.page.is_visible("#btn-slider-modal"):
            self.page.click("#btn-slider-modal")
            self.page.wait_for_timeout(1000)
        self.page.fill(self.field("txt_rfcbusqueda"), self.receiver.rfc)
        # The date field is a read-only datepicker; set its value directly.
        self.page.evaluate(
            "value => document.querySelector('%s').value = value" % self.field("txt_fechaticket"), self.args.fecha
        )
        self.page.fill(self.field("txt_montototal"), self.args.monto)
        self.page.fill(self.field("txt_numeroticket"), self.args.ticket)
        self.page.select_option(self.field("ddl_sucursales"), self.branch_value())
        self.show([self.field(name) for name in self.ticket_fields], width=40)
        self.page.click(self.field("btn_siguiente"))
        self.page.wait_for_timeout(5000)
        self.page.wait_for_load_state("networkidle", timeout=60000)
        if "transaccion.aspx" not in self.page.url:
            raise PortalError("the portal did not accept the receipt: %s" % self.text()[:600])

    def fill_02_receiver(self):
        # Choosing the regime posts the page back and reloads the Uso CFDI options.
        self.page.select_option(self.field("ddl_regimenfiscal"), self.regime())
        self.page.wait_for_timeout(3000)
        self.page.wait_for_load_state("networkidle", timeout=60000)
        self.select_offered(self.field("ddl_usocfdiconrfc"), self.args.uso, "Uso CFDI")
        self.page.fill(self.field("txt_razonsocial"), self.receiver.name)
        self.page.fill(self.field("txt_email"), self.args.email)
        self.page.fill(self.field("txt_cp"), self.receiver.postal_code)
        # The address and the card's last digits are optional; the CFDI 4.0 only needs the CP.
        self.show([self.field(name) for name in self.receiver_fields], width=40)

    def submit_01_invoice(self):
        # The button is meant to open a confirmation dialog, but clicked while the page is still
        # loading after the regime postback, its onclick fails and the browser submits the form,
        # which issues the invoice. So wait for the page's scripts first.
        self.page.wait_for_function(
            "typeof BotonConfirmacion === 'function' && typeof jQuery === 'function'", timeout=60000
        )
        self.page.click(self.field("btn_facturar"))
        self.page.wait_for_timeout(2000)
        if not self.page.is_visible("#btn_confirmacionsi"):
            raise PortalError("no confirmation dialog: %s" % self.text()[:600])
        print("CONFIRMATION: %s" % self.text("#modal_confirmacion"))
        self.page.click("#btn_confirmacionsi")
        self.page.wait_for_timeout(10000)
        self.page.wait_for_load_state("networkidle", timeout=90000)
        print("url: %s" % self.page.url)
        print("RESULT: %s" % self.text()[:1200])
        for link in self.page.query_selector_all("a[href]"):
            label = " ".join(link.inner_text().split())
            if label:
                print("LINK: %s -> %s" % (label, link.get_attribute("href")))
        (self.out / "result.html").write_text(self.page.content())


if __name__ == "__main__":
    sys.exit(Carlscol.main())
