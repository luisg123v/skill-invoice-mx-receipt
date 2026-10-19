# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Get the CFDI of an OXXO receipt from its invoicing portal.

The portal asks for the email after issuing the invoice; see reference/oxxo.md.

Usage:
    oxxo.py --fecha 26/09/2026 --folio 123456 --venta 10ABC20XYZ1 --total 100.00 --uso S01 [--send]
"""

import datetime
import sys

from playwright.sync_api import Error as PlaywrightError
from config import CFDI_USAGES, REGIMES
from portal import InvoicePortal, PortalError


class Oxxo(InvoicePortal):
    name = "oxxo"
    url = "https://www4.oxxo.com/facturacionElectronica-web/views/layout/inicio.do"
    # Behind Imperva, which answers 403 to IPs outside Mexico.
    blocks_foreign_ips = True
    months = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--fecha", required=True, help="dd/mm/yyyy")
        parser.add_argument("--folio", required=True, help="Fol_Vta")
        parser.add_argument("--venta", required=True, help="ID de venta, e.g. 10ABC20XYZ1")
        parser.add_argument("--total", required=True)

    def ticket(self):
        return self.args.folio

    def close_info_dialog(self):
        for selector in ["#form\\:dlgInfoTicket a.ui-dialog-titlebar-close", "a.ui-dialog-titlebar-close"]:
            element = self.page.query_selector(selector)
            if element and element.is_visible():
                try:
                    element.click(timeout=4000)
                    self.page.wait_for_timeout(800)
                except PlaywrightError as error:
                    # The overlay is removed below anyway.
                    print("NOTE: could not close the info dialog: %s" % error.message.splitlines()[0])
                break
        self.page.evaluate("()=>{document.querySelectorAll('.ui-widget-overlay').forEach(e=>e.remove());}")
        self.page.wait_for_timeout(400)

    def set_date(self, date):
        """Pick the date in the read-only datepicker, moving back months when needed."""
        self.page.click("#form\\:fecha_input")
        self.page.wait_for_timeout(1400)
        for _attempt in range(12):
            month = (self.page.inner_text("#ui-datepicker-div .ui-datepicker-month") or "").strip().lower()
            year = (self.page.inner_text("#ui-datepicker-div .ui-datepicker-year") or "").strip()
            if month in self.months and int(year) * 12 + self.months.index(month) > date.year * 12 + date.month - 1:
                self.page.click("#ui-datepicker-div a.ui-datepicker-prev")
                self.page.wait_for_timeout(500)
                continue
            break
        for link in self.page.query_selector_all("#ui-datepicker-div td:not(.ui-datepicker-other-month) a"):
            if (link.inner_text() or "").strip() == str(date.day):
                link.click()
                break
        self.page.wait_for_timeout(900)
        return self.page.input_value("#form\\:fecha_input")

    def click_validate(self):
        for element in self.page.query_selector_all("a, button, span"):
            try:
                label = (element.inner_text() or "").strip().lower()
            except Exception:
                continue
            if label.startswith("validar ticket") and element.is_visible():
                element.click()
                return

    def wait_messages(self, seen=()):
        """Return the portal's new messages, which show as a growl that fades out.

        `seen` are the messages of the previous action, which may still be on the page.
        """
        messages = []
        for _ in range(40):
            self.page.wait_for_timeout(500)
            for selector in [".ui-messages", ".ui-message", ".ui-growl-item"]:
                for element in self.page.query_selector_all(selector):
                    message = " ".join((element.inner_text() or "").split())
                    if message and message not in messages and message not in seen:
                        messages.append(message)
            if messages:
                break
        return messages

    def fill_01_ticket(self):
        date = datetime.datetime.strptime(self.args.fecha, "%d/%m/%Y").date()
        self.page.goto(self.url, wait_until="networkidle", timeout=60000)
        self.close_info_dialog()
        picked = self.set_date(date)
        if picked.strip() != self.args.fecha:
            # An empty date makes the portal answer "ejercicio fiscal diferente", which is misleading.
            raise PortalError("the datepicker has %r instead of %s" % (picked, self.args.fecha))
        self.page.fill("#form\\:folio", self.args.folio)
        self.page.fill("#form\\:venta", self.args.venta)
        self.page.fill("#form\\:total", self.args.total)
        self.click_validate()
        messages = self.wait_messages()
        button = self.page.query_selector("#form\\:continuar")
        print("fecha=%s folio=%s venta=%s total=%s" % (picked, self.args.folio, self.args.venta, self.args.total))
        print("message: %s" % (messages[0] if messages else "(none)"))
        print("continue enabled: %s" % bool(button and button.is_enabled()))
        if not button or not button.is_enabled():
            raise PortalError("the portal didn't validate the receipt")

    def pick(self, menu, label):
        """Pick an option of a PrimeFaces menu by its label, stopping when it isn't offered."""
        options = self.page.eval_on_selector_all(
            "[id='form:%s_input'] option" % menu, "options => options.map(option => option.textContent.trim())"
        )
        matching = [
            option for option in options if option and self.comparable_text(option) == self.comparable_text(label)
        ]
        if not matching:
            raise PortalError("%r not offered; options: %s" % (label, [option for option in options if option]))
        self.page.click("[id='form:%s']" % menu)
        self.page.wait_for_timeout(700)
        self.page.click("[id='form:%s_panel'] li:text-is('%s')" % (menu, matching[0]))
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(1500)
        return self.page.inner_text("[id='form:%s_label']" % menu).strip()

    def fill_02_receiver(self):
        # The address is optional; the CFDI only needs the postal code.
        self.page.click("#form\\:continuar")
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)
        self.page.fill("#form\\:rfc", self.receiver.rfc)
        # The regime options load when the RFC field loses the focus.
        self.page.press("#form\\:rfc", "Tab")
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(1500)
        self.page.fill("#form\\:razon", self.receiver.name)
        self.page.fill("#form\\:codigo", self.receiver.postal_code)
        self.page.press("#form\\:codigo", "Tab")
        self.page.wait_for_load_state("networkidle")
        # The Uso CFDI options load after the regime is picked.
        regime = self.pick("selectOneMenuRegFis", REGIMES[self.regime()])
        usage = self.pick("selectOneMenuCFDI", CFDI_USAGES[self.args.uso].description)
        self.show(["#form\\:rfc", "#form\\:razon", "#form\\:codigo"])
        print("%-22s %r" % ("regime", regime))
        print("%-22s %r" % ("uso", usage))

    def send_email(self, seen=()):
        """Send the CFDI to the email, from the page that shows the invoice.

        The page shows it after issuing the invoice, and after finding it in "Reimprime tu factura".
        """
        self.page.fill("input[placeholder='correo@dominio.com']:visible", self.args.email)
        self.page.click("button:visible:has-text('Enviar correo')")
        self.page.wait_for_load_state("networkidle")
        messages = self.wait_messages(seen)
        print("email %s: %s" % (self.args.email, messages or "(no message)"))

    def submit_01_invoice(self):
        self.page.click("#form\\:generarFactura")
        self.page.wait_for_load_state("networkidle", timeout=90000)
        messages = self.wait_messages()
        print("messages: %s" % (messages or "(none)"))
        self.send_email(messages)


if __name__ == "__main__":
    sys.exit(Oxxo.main())
