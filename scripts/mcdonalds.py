# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a McDonald's receipt on www.facturacionmcdonalds.com.mx.

The receipt prints the restaurant's number before its name (such as "0123 McDonalds
Centro"), the register ("Reg."), the ticket ("Nro. Ticket") and the date. The portal
doesn't ask for the Uso CFDI, so after issuing, the script saves the XML and says which
use the portal chose.

Usage:
    mcdonalds.py --restaurante 0123 --ticket 1234 --caja 12 --fecha 10/11/2026 \
        --total 49.00 --uso S01 [--send]
"""

import sys
from xml.etree import ElementTree

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from portal import InvoicePortal, PortalDone, PortalError, pattern_argument


class McDonalds(InvoicePortal):
    name = "mcdonalds"
    url = "https://www.facturacionmcdonalds.com.mx/"

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument(
            "--restaurante", required=True, help="the 4 digits before the restaurant"
        )
        parser.add_argument(
            "--ticket",
            required=True,
            type=pattern_argument(
                pattern=r"\d+", error="the ticket should be only digits"
            ),
            help='"Nro. Ticket"',
        )
        parser.add_argument("--caja", required=True, help='"Reg.", the register')
        parser.add_argument("--fecha", required=True, help="dd/mm/yyyy")
        parser.add_argument("--total", required=True, help="the total, with cents")

    def ticket(self):
        """Return the number without the zeros on its left, as the portal takes it."""
        return self.args.ticket.lstrip("0")

    def fill_01_ticket(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        self.page.fill("#number_store", self.args.restaurante)
        self.page.fill("#num_ticket", self.ticket())
        self.page.fill("#num_caja", self.args.caja)
        # The date picker clears a filled value, so the date is typed.
        self.page.click("#fecha_ticket")
        self.page.keyboard.type(self.args.fecha, delay=50)
        self.page.click("#total_ticket")
        self.page.fill("#total_ticket", self.args.total)
        self.page.keyboard.press("Tab")
        # The portal enables the receiver's fields once it finds the ticket. A ticket
        # already invoiced opens a window with the invoice's UUID and folio, and one it
        # doesn't find, a window that says why ("Error en el ticket ... Verifica los
        # datos").
        self.wait_for_answer(
            "#tax_id_receiver:enabled, #result_previously",
            errors=[".modal.show:not(#result_previously)"],
        )
        if self.page.is_visible("#result_previously"):
            raise PortalDone("already invoiced: %s" % self.text("#result_previously"))
        self.show(
            [
                "#number_store",
                "#num_ticket",
                "#num_caja",
                "#fecha_ticket",
                "#total_ticket",
            ]
        )

    def fill_02_receiver(self):
        # The regime options load when the RFC field loses the focus.
        self.page.fill("#tax_id_receiver", self.receiver.rfc)
        self.page.keyboard.press("Tab")
        self.page.fill("#name_receiver", self.receiver.name)
        self.page.fill("#cp_client", self.receiver.postal_code)
        self.select_offered("#regime_id", self.regime(), "Régimen fiscal")
        self.page.fill("#email_receiver", self.args.email)
        # The portal enables its button when a key is released in the form.
        self.page.press("#email_receiver", "End")
        self.page.check("#condiciones", force=True)
        self.show(
            [
                "#tax_id_receiver",
                "#name_receiver",
                "#cp_client",
                "#regime_id",
                "#email_receiver",
            ]
        )

    def fill_03_review(self):
        """Open the portal's confirmation of the data, the step before issuing."""
        self.page.click("#facturar")
        modal = self.page.locator("#confirm_data")
        modal.wait_for(state="visible", timeout=60000)
        try:
            self.page.locator("#id_accept").wait_for(timeout=10000)
        except PlaywrightTimeoutError:
            raise PortalError(
                "the portal did not accept the ticket: %s" % self.text("#confirm_data")
            )
        print("SUMMARY: %s" % self.text("#confirm_data"))

    def submit_01_invoice(self):
        self.page.click("#id_accept")
        answer = self.page.locator("#results:visible, #result_previously:visible")
        answer.first.wait_for(timeout=120000)
        self.page.wait_for_timeout(1000)
        text = " ".join(answer.first.inner_text().split())
        if self.page.is_visible("#result_previously"):
            raise PortalDone("the ticket was already invoiced: %s" % text)
        print("RESULT: %s" % text)

    def submit_02_check_usage(self):
        """Save the issued XML and say which Uso CFDI the portal chose for it."""
        with self.page.expect_download() as download:
            self.page.click("#down_xml")
        path = self.out / "cfdi.xml"
        download.value.save_as(path)
        receiver = ElementTree.parse(path).find("{*}Receptor")
        usage = receiver.get("UsoCFDI") if receiver is not None else None
        print("XML: %s, Uso CFDI %s" % (path, usage))
        if usage != self.args.uso:
            print(
                "WARNING: the portal issued it with Uso CFDI %s, not %s"
                % (usage, self.args.uso)
            )


if __name__ == "__main__":
    sys.exit(McDonalds.main())
