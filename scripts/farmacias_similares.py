# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a receipt of Farmacias Similares on SimiFactura, which sends each franchise to its own portal.

The franchises' portals that the script knows are in `providers`; see reference/farmacias-similares.md.

Usage:
    farmacias_similares.py --referencia FH0123 --codigo 0123456000012 --total 100.00 --forma 04 --uso S01 [--send]
    farmacias_similares.py --referencia FH0123 --codigo 0123456000012 --total 100.00 --forma 04 --uso S01 --resend
"""

import sys
from urllib.parse import urlparse
from xml.etree import ElementTree

from portal import InvoicePortal, PortalDone, PortalError


class FarmaciasSimilares(InvoicePortal):
    name = "farmacias_similares"
    url = "https://facturacion.gpupm.com/simifactura/portal"
    # The host of each franchise portal, and the prefix of the methods that fill it: <prefix>_ticket,
    # <prefix>_receiver, <prefix>_summary and <prefix>_invoice.
    providers = {
        "facturasoltec.com": "soltec",
    }

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--referencia", required=True, help="Referencia de Facturación FRANQUICIA, e.g. FH0123")
        parser.add_argument("--codigo", required=True, help="the digits under the barcode")
        parser.add_argument("--total", required=True, help="Total M.N., with cents, e.g. 100.00")
        parser.add_argument("--forma", required=True, help="Forma de pago code, e.g. 04 for a credit card")
        parser.add_argument(
            "--resend",
            action="store_true",
            help="for a receipt already invoiced, have the portal email the CFDI again, to --email",
        )

    def __init__(self, args, config):
        super().__init__(args, config)
        self.provider = None

    def ticket(self):
        return self.args.codigo

    def fill_01_reference(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        self.page.fill("#Referencia", self.args.referencia)
        self.page.click("button:has-text('Continuar')")
        # A franchise's reference opens a confirmation before sending to the franchise's portal.
        self.page.wait_for_selector("#btnConfirmacion", state="visible", timeout=30000)
        pages_before = len(self.page.context.pages)
        self.page.click("#btnConfirmacion")
        self.page.wait_for_timeout(8000)
        if len(self.page.context.pages) > pages_before:
            self.page = self.page.context.pages[-1]
        self.page.wait_for_load_state("networkidle", timeout=60000)
        host = urlparse(self.page.url).hostname or ""
        for provider_host, prefix in self.providers.items():
            if host == provider_host or host.endswith("." + provider_host):
                self.provider = prefix
                return
        raise PortalError("the reference sends to %s, a portal this script doesn't know" % self.page.url)

    def run_provider_step(self, step):
        getattr(self, "%s_%s" % (self.provider, step))()

    def fill_02_ticket(self):
        self.run_provider_step("ticket")

    def fill_03_receiver(self):
        self.run_provider_step("receiver")

    def fill_04_summary(self):
        self.run_provider_step("summary")

    def submit_01_invoice(self):
        self.run_provider_step("invoice")

    def soltec_type_fields(self, values):
        """Type each field and leave it.

        The portal checks a field as it is typed and when it loses the focus, and only then loads the
        next one.
        """
        for name, value in values:
            field = self.page.locator("input[name=%s]" % name)
            field.fill("", timeout=15000)
            field.press_sequentially(value)
            field.press("Tab")
            self.page.wait_for_timeout(1500)

    def soltec_ticket(self):
        # The branch is the same reference that SimiFactura asked for. Each field stays read-only until
        # the one before it is checked.
        self.soltec_type_fields(
            [
                ("sucursal", self.args.referencia),
                ("codigoBarras", self.args.codigo),
            ]
        )
        # A receipt already invoiced goes to its status page, with links to download the XML and the PDF.
        if "/ticket_en_datos_ticket/" in self.page.url:
            print("status page: %s" % self.text()[:500])
            self.soltec_download()
            if not self.args.resend:
                raise PortalError("the receipt is already invoiced; pass --resend to have the CFDI emailed again")
            self.soltec_resend()
            raise PortalDone("the receipt is already invoiced; the portal was asked to email the CFDI again")
        # The portal checks the barcode's format and writes below the field whether it is right.
        if "CodigoBarras correcto" not in self.text("form"):
            raise PortalError("the portal didn't accept the barcode: %s" % self.text("form")[:400])
        self.soltec_type_fields([("total", self.args.total)])
        self.show(["input[name=sucursal]", "input[name=codigoBarras]", "input[name=total]"], width=30)

    def soltec_receiver(self):
        # The regime options load after the postal code.
        self.soltec_type_fields(
            [
                ("rfc", self.receiver.rfc),
                ("razonSocial", self.receiver.name),
                ("cp", self.receiver.postal_code),
            ]
        )
        self.page.wait_for_timeout(1500)
        self.select_offered("select[name=idRegimenFiscal]", self.regime(), "regime")
        # The Uso CFDI options load after the regime.
        self.page.wait_for_timeout(3000)
        self.select_offered("select[name=claveCfdi]", self.args.uso, "Uso CFDI")
        self.select_offered("select[name=formaPago]", self.args.forma, "Forma de pago")
        self.soltec_type_fields(
            [
                ("correo", self.args.email),
                # Confirms the email.
                ("correo2", self.args.email),
            ]
        )
        self.show(
            [
                "input[name=rfc]",
                "input[name=razonSocial]",
                "input[name=cp]",
                "select[name=idRegimenFiscal]",
                "select[name=claveCfdi]",
                "select[name=formaPago]",
                "input[name=correo]",
            ],
            width=30,
        )
        # Each field shows a message below it saying whether its format is right.
        print("checks: %s" % self.text("form")[:1500])

    def soltec_summary(self):
        # This button only opens a summary to check; the summary's own button issues the invoice.
        self.page.click("button:has-text('Procesar factura v4.0')")
        summary = self.page.locator(".modal.show")
        summary.wait_for(state="visible", timeout=30000)
        print("summary: %s" % " ".join(summary.inner_text().split()))

    def soltec_invoice(self):
        self.page.click(".modal.show button:text-is('Procesar factura')")
        self.page.wait_for_load_state("networkidle", timeout=90000)
        self.page.wait_for_timeout(8000)
        print("RESULT: %s" % self.text()[:1500])
        # The answer is the receipt's status page.
        if "/ticket_en_datos_ticket/" in self.page.url:
            self.soltec_download()

    @staticmethod
    def receiver_rfc(xml):
        """Return the receiver's RFC of a CFDI 4.0."""
        receiver = ElementTree.fromstring(xml).find("{http://www.sat.gob.mx/cfd/4}Receptor")
        return receiver.get("Rfc") if receiver is not None else None

    def soltec_download(self):
        """Save the XML and the PDF from the receipt's status page, which needs no sign-in.

        The page opens with only the branch and the barcode, so a misread barcode can open another
        person's receipt. The files are kept only when the XML is issued to the receiver.
        """
        paths = {}
        for label in ("XML", "PDF"):
            with self.page.expect_download(timeout=60000) as download:
                self.page.get_by_role("link", name=label, exact=True).click()
            paths[label] = self.out / download.value.suggested_filename
            download.value.save_as(paths[label])
        if self.receiver_rfc(paths["XML"].read_bytes()) != self.receiver.rfc:
            for path in paths.values():
                path.unlink()
            raise PortalError("the receipt was invoiced to another RFC; check the barcode")
        for label, path in paths.items():
            print("%s: %s" % (label, path))

    def soltec_resend(self):
        """Send the CFDI again with the form of the status page.

        The page asks to download the XML and the PDF first. The form comes filled in with the email
        given when invoicing, so the script writes --email in it.
        """
        form = self.page.locator("form[action*=enviarCorreoFacturaDatosTicket]")
        # The form is gone once it has been used, and the page only says where the CFDI was sent.
        if not form.count():
            raise PortalError("the status page has no form to send the CFDI again: %s" % self.text()[:800])
        form.locator("input[name=correoPara]").fill(self.args.email)
        form.locator("button[type=submit]").click()
        self.page.wait_for_load_state("networkidle", timeout=60000)
        self.page.wait_for_timeout(3000)
        # It says the documents were already sent before ("Ya se envío con anterioridad"), but the
        # email arrives within seconds.
        print("RESEND to %s: %s" % (self.args.email, self.text()[:800]))


if __name__ == "__main__":
    sys.exit(FarmaciasSimilares.main())
