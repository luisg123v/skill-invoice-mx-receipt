# invoice-mx-receipt

An agent skill that gets the CFDI (Mexican electronic invoice) of a purchase receipt issued to
you. From a photo of the receipt, the agent reads the data the store asks for and fills the store's
self-invoicing portal with a script. Every portal is filled without submitting first, so the
values can be checked. When the store has no portal, the agent asks for the invoice by email or
WhatsApp.

It works with Claude Code and with any other agent that reads `SKILL.md` files. The supported
stores are in the
[portal index](SKILL.md#portal-index).

## Installation

Clone the repository into the directory where your agent looks for skills. For Claude Code:

    git clone git@github.com:luisg123v/skill-invoice-mx-receipt.git ~/.claude/skills/invoice-mx-receipt

Then copy
[`config.example.toml`](config.example.toml)
to `~/.config/invoice-mx-receipt/config.toml` and fill it with your tax data, as it appears in
your Constancia de Situación Fiscal. The repository has no personal data; it is all in that file.

The scripts need Python 3.11 or later and Playwright with its Chromium.
[Running the scripts](SKILL.md#running-the-scripts)
explains how to install them with `uv` or `pipx`.

## Tests

The tests cover what doesn't need a browser, such as the configuration and the email requests.
Run them with
[uv](https://docs.astral.sh/uv/),
which installs their dependencies in its own environment:

    uv run --group test pytest

## License

[MIT](LICENSE)
