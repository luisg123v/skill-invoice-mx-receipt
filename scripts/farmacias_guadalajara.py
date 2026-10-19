# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a Farmacias Guadalajara receipt on www.movil.farmaciasguadalajara.com/facturacion.

With --send it also saves the CFDI's XML and PDF that the portal's service returns; the portal
emails them too.

Usage:
    farmacias_guadalajara.py --qr 'https://www.movil.farmaciasguadalajara.com/facturacion/?folio=...' \
        --uso G03 [--send]
"""

import base64
import re
import sys
import urllib.parse
from pathlib import Path

from portal import InvoicePortal, PortalError


class FarmaciasGuadalajara(InvoicePortal):
    name = "farmaciasguadalajara"
    url = "https://www.movil.farmaciasguadalajara.com/facturacion/"
    # Behind Akamai, which answers 403 to IPs outside Mexico.
    blocks_foreign_ips = True
    receiver_fields = [
        "#rfc",
        "#codigoPostal",
        "#razonSocial",
        "#regimenFiscal",
        "#usoCfdi",
        "#correo",
        "#correoConfirm",
    ]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--qr", help="URL in the receipt's QR (it has folio, caja, ticket, fecha and tienda)")
        parser.add_argument("--folio", help="FOLIO FACTURA, e.g. 123456-123456-123456 (without --qr)")
        parser.add_argument("--caja")
        parser.add_argument("--ticket", help="No TICKET")
        parser.add_argument("--fecha", help="FECHA COMPRA, yyyy-mm-dd")

    def __init__(self, args, config):
        super().__init__(args, config)
        self.answers = []

    @staticmethod
    def tag(xml, name):
        """Return the text of the first <name> element in the service's answer."""
        match = re.search(r"<%s>(.*?)</%s>" % (name, name), xml, re.S)
        return match.group(1) if match else None

    def ticket(self):
        if self.args.qr:
            query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(self.args.qr).query))
            self.args.folio = query.get("folio")
        elif not self.args.folio or not self.args.caja or not self.args.ticket or not self.args.fecha:
            raise SystemExit("ABORT: pass --qr, or --folio, --caja, --ticket and --fecha")
        return self.args.folio

    def alert_text(self):
        """Return the text of the SweetAlert dialog on screen, or None."""
        if not self.page.is_visible(".swal2-popup"):
            return None
        return self.text(".swal2-popup")

    def keep_invoice_answer(self, response):
        """Keep the answer of the service that issues the invoice, which has the XML and the PDF."""
        if "generateInvoice" in (response.request.post_data_buffer or b"").decode("utf-8", "replace"):
            self.answers.append(response)

    def fill_01_folio(self):
        self.page.on("response", self.keep_invoice_answer)
        response = self.page.goto(self.args.qr or self.url, wait_until="domcontentloaded", timeout=90000)
        if response.status == 403:
            raise PortalError("Akamai blocked the browser (403): %s" % self.text()[:300])
        self.page.wait_for_selector("#folioFactura", timeout=60000)
        self.page.wait_for_timeout(3000)
        if not self.args.qr:
            self.page.fill("#folioFactura", self.args.folio)
            self.page.fill("#caja", self.args.caja)
            self.page.fill("#fechaCompra", self.args.fecha)
            self.page.fill("#ticket", self.args.ticket)
        if not self.page.is_checked("#politicasPr-input"):
            self.page.check("#politicasPr-input", force=True)
        self.show(["#folioFactura", "#caja", "#fechaCompra", "#ticket"], width=16)
        self.page.click("button:has-text('Validar Folio')")
        self.page.wait_for_selector(".swal2-popup", timeout=60000)
        self.page.wait_for_timeout(1000)
        message = self.alert_text()
        print("VALIDATION: %s" % message)
        # Anything else is an error: wrong data, too old, already invoiced...
        if "Validar sucursal" not in message:
            raise PortalError("the portal did not accept the folio")
        self.page.click(".swal2-confirm")
        self.page.wait_for_timeout(2000)

    def fill_02_receiver(self):
        # Typing the RFC loads the data the portal keeps for it (name, CP, regime, uso, email).
        self.page.fill("#rfc", self.receiver.rfc)
        self.page.press("#rfc", "Tab")
        self.page.wait_for_timeout(5000)
        self.page.fill("#codigoPostal", self.receiver.postal_code)
        self.page.fill("#razonSocial", self.receiver.name)
        self.page.select_option("#regimenFiscal", self.regime())
        self.page.select_option("#usoCfdi", self.args.uso)
        if not self.page.is_checked("#envioCorreo-input"):
            self.page.check("#envioCorreo-input", force=True)
            self.page.wait_for_timeout(1000)
        self.page.fill("#correo", self.args.email)
        self.page.fill("#correoConfirm", self.args.email)
        self.show(self.receiver_fields, width=16)

    def submit_01_invoice(self):
        self.page.click("button:has-text('Obtener Factura')")
        self.page.wait_for_selector(".swal2-popup", timeout=30000)
        print("CONFIRMATION: %s" % self.alert_text())
        # "¿Está seguro que quiere facturar?" -> Aceptar
        self.page.click(".swal2-confirm")
        self.page.wait_for_function(
            "() => !document.querySelector('.swal2-popup')"
            " || !/seguro que quiere facturar/.test(document.querySelector('.swal2-popup').innerText)",
            timeout=120000,
        )
        self.page.wait_for_selector(".swal2-popup", timeout=120000)
        self.page.wait_for_timeout(2000)
        print("RESULT: %s" % self.alert_text())
        for response in self.answers:
            body = response.text()
            print("code %s: %s" % (self.tag(body, "responseCode"), self.tag(body, "responseMessage")))
            for data, name in (("xmlFile", "xmlFileName"), ("pdfFile", "pdfFileName")):
                if self.tag(body, data):
                    path = self.out / Path(self.tag(body, name) or data).name
                    path.write_bytes(base64.b64decode(self.tag(body, data)))
                    print("file: %s" % path)


if __name__ == "__main__":
    sys.exit(FarmaciasGuadalajara.main())
