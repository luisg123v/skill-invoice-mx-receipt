"""Base class of the portal scripts.

A portal script subclasses `InvoicePortal` and fills each step of the portal in its own method,
named `fill_<NN>_<step>()`. The steps that issue the invoice are named `submit_<NN>_<step>()`. The
base class opens the browser, prints the portal's dialogs, runs the steps in the order of their
numbers with a screenshot after each one, and only runs the submit steps with `--send`, so a run
without it never issues anything. `template.py` is the starting point for a new portal.
"""

import argparse
import sys
from pathlib import Path

from config import CFDI_USAGES, Config
from playwright.sync_api import sync_playwright


class PortalError(Exception):
    """The portal answered something that stops the run."""


class PortalDone(Exception):
    """The run ends early because there is nothing left to do, such as a receipt already invoiced."""


class InvoicePortal:
    """Base class of a portal script.

    A subclass sets `name` and `url`, adds the receipt's fields in `add_arguments()`, and implements
    the step methods described in the module's docstring.
    """

    name = ""
    url = ""
    # The portal blocks IPs outside Mexico, so browse through the configured proxy.
    blocks_foreign_ips = False
    # Portals don't always write all the accents, such as "Adquisición de mercancias".
    accents = str.maketrans("áéíóúü", "aeiouu")

    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.receiver = config.receiver
        self.out = config.receipt_folder(self.name, self.ticket())
        self.page = None

    @classmethod
    def add_arguments(cls, parser):
        """Add the arguments of the fields that the portal asks for, usually the receipt's.

        A subclass overrides it to add them. The arguments that every portal has (`--uso`,
        `--email`, `--send` and `--config`) are added by `main()`.
        """

    @classmethod
    def step_names(cls, prefix):
        """Return the names of the step methods with that prefix, in the order of their numbers."""
        return sorted(name for name in dir(cls) if name.startswith(prefix) and callable(getattr(cls, name)))

    @classmethod
    def submits(cls):
        """Return whether the script issues the invoice; some only validate the receipt."""
        return bool(cls.step_names("submit_"))

    def ticket(self):
        """Return the receipt's number, for the evidence folder.

        It is the `--ticket` argument; a portal that names it differently overrides this method.
        """
        return self.args.ticket

    def default_email(self):
        """Return where the portal sends the CFDI when --email isn't given."""
        return self.config.email

    def regime(self):
        """Return the receiver's regime for the Uso CFDI of this run."""
        return self.receiver.regime_for(self.args.uso)

    def text(self, selector="body"):
        """Return the visible text of an element, in one line."""
        return " ".join(self.page.inner_text(selector).split())

    def screenshot(self, name):
        path = self.out / ("%s.png" % name)
        self.page.screenshot(path=str(path), full_page=True)
        return path

    def show(self, selectors, width=22):
        """Print the value of each field, to compare it with the receipt and the receiver."""
        for selector in selectors:
            print("%-*s %r" % (width, selector, self.page.input_value(selector)))

    def comparable_text(self, text):
        """Return a text in lowercase and without accents, to compare it with the portal's."""
        return text.strip().lower().translate(self.accents)

    def select_offered(self, selector, value, what):
        """Select a value, stopping when the portal doesn't offer it.

        A Uso CFDI that the regime doesn't admit, for example, is missing from the options.
        """
        offered = [option.get_attribute("value") for option in self.page.query_selector_all(selector + " option")]
        if value not in offered:
            raise PortalError(
                "%s %s not offered; options: %s" % (what, value, [option for option in offered if option])
            )
        self.page.select_option(selector, value)

    def print_dialog(self, dialog):
        """Print an alert() or confirm() and dismiss it.

        Many portals report errors this way, and Playwright would dismiss them without a trace.
        Dismissing answers "No" to offers such as resending the invoice.
        """
        print("DIALOG: %s" % " ".join(dialog.message.split()))
        dialog.dismiss()

    def launch(self, playwright):
        """Open Chromium without a window, through the proxy if the portal blocks foreign IPs.

        Some portals block headless browsers, so it is the full Chromium (the "chromium" channel),
        not the reduced headless build, and its user agent says "Chrome" instead of
        "HeadlessChrome". The flag hides `navigator.webdriver`, which some blocking services check.
        """
        options = {"headless": True, "channel": "chromium", "args": ["--disable-blink-features=AutomationControlled"]}
        if self.blocks_foreign_ips:
            if self.config.proxy:
                self.config.open_proxy()
                options["proxy"] = {"server": self.config.proxy}
            else:
                print("NOTE: this portal blocks IPs outside Mexico and there is no proxy; browsing directly")
        browser = playwright.chromium.launch(**options)
        probe = browser.new_page()
        user_agent = probe.evaluate("navigator.userAgent").replace("HeadlessChrome", "Chrome")
        probe.close()
        context = browser.new_context(
            locale="es-MX", viewport={"width": 1400, "height": 1200}, accept_downloads=True, user_agent=user_agent
        )
        return browser, context.new_page()

    def run_steps(self, prefix):
        for name in self.step_names(prefix):
            getattr(self, name)()
            print("screenshot: %s" % self.screenshot(name))

    def run(self):
        with sync_playwright() as playwright:
            browser, self.page = self.launch(playwright)
            self.page.on("dialog", self.print_dialog)
            try:
                self.run_steps("fill_")
                if self.submits() and not self.args.send:
                    print("dry run: not submitted")
                elif self.submits():
                    self.run_steps("submit_")
            except PortalDone as done:
                print("DONE: %s" % done)
                print("screenshot: %s" % self.screenshot("done"))
            except PortalError as error:
                print("ABORT: %s" % error)
                print("screenshot: %s" % self.screenshot("abort"))
                return 2
            finally:
                browser.close()
        return 0

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(
            description=sys.modules[cls.__module__].__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
        )
        cls.add_arguments(parser)
        if cls.submits():
            parser.add_argument("--uso", required=True, choices=CFDI_USAGES, metavar="USO", help="Uso CFDI, e.g. G03")
            parser.add_argument("--email", help="where the portal sends the CFDI (default: from the configuration)")
            parser.add_argument(
                "--send", action="store_true", help="issue the invoice; without it, only fill the portal"
            )
        parser.add_argument("--config", type=Path, help="configuration file")
        args = parser.parse_args()
        config = Config.load(args.config)
        if cls.submits():
            # Stop before opening the browser when no regime of the receiver admits the use.
            config.receiver.regime_for(args.uso)
        portal = cls(args, config)
        if cls.submits() and not args.email:
            args.email = portal.default_email()
        return portal.run()
