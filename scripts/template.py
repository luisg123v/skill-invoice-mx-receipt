# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright", "tomli; python_version < '3.11'"]
# ///
"""Invoice a receipt of <Store> on <portal URL>.

This is the starting point for a new portal: copy it to scripts/<store>.py, rename the
class, and replace the URL, the arguments and the selectors with the portal's. Each step
of the portal is a method, numbered in the order the portal shows them. See the
docstring of portal.py.

Keep everything the script needs in its class, as methods or class attributes, including
the checks of its arguments. For an argument with a fixed format, such as a folio, use
`pattern_argument()` of portal.py.

After each click, wait for the portal's answer with `wait_for_answer()`, not for a fixed
time. A portal that takes longer than usual would make the script stop, or go on with a
page that isn't ready.

Usage:
    template.py --ticket 12345 --fecha 23/10/2026 --total 100.00 --uso G03 [--send]
"""

import sys

from portal import InvoicePortal


class Template(InvoicePortal):
    name = "template"
    url = "https://facturacion.example.com/"

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--ticket", required=True, help="receipt number")
        parser.add_argument("--fecha", required=True, help="dd/mm/yyyy")
        parser.add_argument("--total", required=True)

    def fill_01_ticket(self):
        self.page.goto(self.url, wait_until="networkidle", timeout=90000)
        self.page.fill("#ticket", self.args.ticket)
        self.page.fill("#fecha", self.args.fecha)
        self.page.fill("#total", self.args.total)
        self.page.click("button[type=submit]")
        # When the portal doesn't move on, its message says why: already invoiced, not
        # found yet...
        self.wait_for_answer("#rfc", errors=[".alert-danger"])

    def fill_02_receiver(self):
        self.page.fill("#rfc", self.receiver.rfc)
        self.page.fill("#nombre", self.receiver.name)
        self.page.fill("#cp", self.receiver.postal_code)
        self.page.select_option("#regimen", self.regime())
        # The Uso CFDI options usually load after the regime, and select_offered() waits
        # for them.
        self.select_offered("#uso", self.args.uso, "Uso CFDI")
        self.page.fill("#email", self.args.email)
        self.show(["#rfc", "#nombre", "#cp", "#regimen", "#uso", "#email"])

    def submit_01_invoice(self):
        self.page.click("button:has-text('Facturar')")
        self.wait_for_answer(".result", errors=[".alert-danger"], timeout=120)
        print("RESULT: %s" % self.text()[:1200])


if __name__ == "__main__":
    sys.exit(Template.main())
