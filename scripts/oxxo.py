# /// script
# requires-python = ">=3.11"
# dependencies = ["playwright"]
# ///
"""Validate an OXXO receipt on its invoicing portal.

Only the first step (receipt validation) is automated, so it never issues anything. The second
step (receiver's data and submit) hasn't been explored yet; see reference/oxxo.md.

Usage:
    oxxo.py --fecha 26/09/2026 --folio 123456 --venta 10ABC20XYZ1 --total 100.00
"""

import datetime
import sys

from playwright.sync_api import Error as PlaywrightError
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

    def wait_messages(self):
        """Return the portal's messages, which show as a growl that fades out."""
        messages = []
        for _ in range(40):
            self.page.wait_for_timeout(500)
            for selector in [".ui-messages", ".ui-message", ".ui-growl-item"]:
                for element in self.page.query_selector_all(selector):
                    message = " ".join((element.inner_text() or "").split())
                    if message and message not in messages:
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


if __name__ == "__main__":
    sys.exit(Oxxo.main())
