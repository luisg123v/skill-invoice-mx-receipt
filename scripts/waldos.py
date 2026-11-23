# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a Waldo's receipt on facturacion.waldos.com.

The top of the receipt has the data to invoice: "Tienda", "Caja", "Fecha", "Cajero" and
"Transacción", which the portal calls "Ticket". With the total, the portal finds the
receipt and opens a form for the receiver's data.

Usage:
    waldos.py --tienda 1234 --caja 3 --cajero 123456 --ticket 1234 \
        --fecha 17/11/2026 --total 100.00 --uso S01 [--send]
"""

import datetime
import sys

from portal import InvoicePortal, PortalDone, PortalError, pattern_argument


class Waldos(InvoicePortal):
    name = "waldos"
    # The page of facturacion.waldos.com only shows this one in a frame.
    url = "https://facturacion.waldos.com/CFDI_PortalClientes_CTE40/default"
    # It warns in a yellow box, e.g. "El importe proporcionado [$100.00] no corresponde
    # al ticket de compra".
    errors = [".alert-warning", ".alert-danger"]
    receiver_fields = [
        "#MainContent_txtDRFC",
        "#MainContent_txtDRazonSocial",
        "#MainContent_txtDCP",
        "#MainContent_cboRegimenFiscal",
        "#MainContent_cboDUsoCFDI",
        "#MainContent_txtDEmail",
    ]

    @classmethod
    def add_arguments(cls, parser):
        digits_argument = pattern_argument(
            pattern=r"\d+", error="it should be only digits"
        )
        parser.add_argument(
            "--tienda", required=True, type=digits_argument, help='"Tienda"'
        )
        parser.add_argument(
            "--caja", required=True, type=digits_argument, help='"Caja"'
        )
        parser.add_argument(
            "--cajero", required=True, type=digits_argument, help='"Cajero"'
        )
        parser.add_argument(
            "--ticket", required=True, type=digits_argument, help='"Transacción"'
        )
        parser.add_argument("--fecha", required=True, help='"Fecha", dd/mm/yyyy')
        parser.add_argument("--total", required=True, help='"Total", with cents')

    def ticket(self):
        return f"{self.args.tienda}-{self.args.ticket}"

    def fill_01_ticket(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        self.page.fill("#MainContent_txtRFC", self.receiver.rfc)
        self.page.fill("#MainContent_txtTienda", self.args.tienda)
        self.page.fill("#MainContent_txtCantidad", self.args.total)
        self.page.fill("#MainContent_txtCaja", self.args.caja)
        self.page.fill("#MainContent_txtCajero", self.args.cajero)
        self.page.fill("#MainContent_txtTicket", self.args.ticket)
        # The field has a date picker that keeps its own date, today's at first, and
        # writes it back into the field when the form is sent. It reads the date typed
        # key by key, as a person does, but not a value set at once with fill().
        date = datetime.datetime.strptime(self.args.fecha, "%d/%m/%Y").date()
        date_field = self.page.locator("#MainContent_txtFecha")
        date_field.clear()
        date_field.press_sequentially(date.isoformat())
        self.show(
            [
                "#MainContent_txtRFC",
                "#MainContent_txtFecha",
                "#MainContent_txtTienda",
                "#MainContent_txtCantidad",
                "#MainContent_txtCaja",
                "#MainContent_txtCajero",
                "#MainContent_txtTicket",
            ],
            width=30,
        )
        with self.page.expect_response(
            lambda response: response.request.method == "POST", timeout=120000
        ):
            self.page.click("#MainContent_cmdBuscar")
        # The page sends the form in the background. Once it has processed the
        # response, the answer is on the page, although a dialog takes a moment more to
        # show.
        self.page.wait_for_function(
            "!Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostBack()"
        )
        # The answer is the receiver's form, an error or, for an invoiced receipt, the
        # dialog of the invoice's files with that message. For a receipt invoiced to an
        # RFC other than the one on the first page, the response has none of them.
        invoiced_message = ":text('ya ha sido facturado')"
        receiver_form_or_invoiced_message = (
            f"#MainContent_txtDEmail, {invoiced_message}"
        )
        any_answer = ", ".join([receiver_form_or_invoiced_message, *self.errors])
        if not self.page.locator(any_answer).count():
            raise PortalError(
                "no answer, as for a receipt invoiced to another RFC: %s"
                % self.text()[:300]
            )
        self.wait_for_answer(receiver_form_or_invoiced_message, errors=self.errors)
        if self.page.locator(invoiced_message).filter(visible=True).count():
            print(f"already invoiced: {self.text(invoiced_message)}")
            self.download_files()
            raise PortalDone("already invoiced")

    def fill_02_receiver(self):
        # Choosing the regime reloads the form with the uses it admits, so the other
        # fields are filled once that is done. Choosing the regime the form already
        # shows reloads it too, and that would reset the fields being filled.
        regime = "#MainContent_cboRegimenFiscal"
        if self.page.input_value(regime) != self.regime():
            with self.page.expect_response(lambda r: r.request.method == "POST"):
                self.select_offered(regime, self.regime(), "regime", timeout=30)
            self.page.locator("#MainContent_UpdateProgress1").wait_for(state="hidden")
        self.select_offered(
            "#MainContent_cboDUsoCFDI", self.args.uso, "Uso CFDI", timeout=60
        )
        # The form comes with the RFC typed on the first page. When the portal has
        # invoiced that RFC before, it also fills the other fields with the data it
        # keeps for it. They are set anyway, since that data may be out of date.
        self.page.fill("#MainContent_txtDRazonSocial", self.receiver.name)
        self.page.fill("#MainContent_txtDCP", self.receiver.postal_code)
        self.page.fill("#MainContent_txtDEmail", self.args.email)
        self.show(self.receiver_fields, width=30)

    def submit_01_invoice(self):
        self.page.click("#MainContent_cmdGenerarFactura")
        # A dialog, "Descarga de archivos", says "La factura se generó correctamente y se
        # ha enviado a su correo electrónico", with links to the XML and the PDF.
        issued_message = ":text('se generó correctamente')"
        self.wait_for_answer(issued_message, errors=self.errors, timeout=120)
        print(f"RESULT: {self.text(issued_message)}")
        self.download_files()

    def download_files(self):
        """Save the XML and the PDF from the dialog of the invoice's files."""
        link_per_format = {"XML": "#MainContent_hprXML", "PDF": "#MainContent_hprPDF"}
        for file_format, link in link_per_format.items():
            with self.page.expect_download(timeout=60000) as download:
                self.page.click(link)
            path = self.out / download.value.suggested_filename
            download.value.save_as(path)
            print(f"{file_format}: {path}")


if __name__ == "__main__":
    sys.exit(Waldos.main())
