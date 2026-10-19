---
name: invoice-mx-receipt
description: Get the CFDI (Mexican electronic invoice) of a purchase receipt (AKA "ticket" in Mexico) issued to you, on the store's self-invoicing portal (autofacturación), or by asking the store by email or WhatsApp when it has no portal. Use whenever the user sends a photo of a receipt, asks in any language to invoice one, or names a store with a receipt number (OXXO, Starbucks, Walmart, Alsea brands, gas stations, restaurants), even without saying "portal" or "CFDI". Also use to retry a receipt the portal didn't find yet, or to add a new store's portal.
---

# Invoice a Mexican receipt

In Mexico, a store's receipt is not a tax document. To deduct or record a purchase, the buyer asks
the store for a CFDI, usually on the store's portal, with the data printed on the receipt. This
skill reads the receipt, fills the portal, and gets the CFDI sent to the address in the
configuration.

A CFDI issued with wrong data has to be cancelled, and some portals allow only one invoice per
receipt. That is why every portal is filled in a dry run first and checked before submitting.

## Configuration

The scripts read the receiver's data from `~/.config/invoice-mx-receipt/config.toml`, or from the
file that the `INVOICE_MX_RECEIPT_CONFIG` environment variable points to. If it doesn't exist,
copy
[`config.example.toml`](config.example.toml)
there and fill it with the user, from their Constancia de Situación Fiscal (CSF). Read the file
before the first receipt of a conversation, because its `[cfdi_usages]` table and its `[request]`
section change what you do below.

Write the name as in the CSF. Case doesn't matter, but accents do.

## Uso CFDI

Take the use from the configuration's `[cfdi_usages]` table. When the purchase isn't there, or the
receipt mixes kinds of purchases, ask. The usual uses are:

- **G03 Gastos en general**, for anything that can be related to the user's economic activity,
  because it can be recorded as an expense. That includes what an office or a workplace uses
  (office supplies, computer equipment, cleaning products, snacks and soft drinks) and a meal at a
  restaurant, because it can be a business meal.
- **D01 to D10**, for personal deductions, such as medical, dental or hospital expenses (D01).
- **S01 Sin efectos fiscales**, for purchases the user doesn't deduct, such as groceries for the
  home (meat, bread, cheese).

Each use admits only some regimes, as the SAT's c_UsoCFDI catalog says. The scripts declare the
first of the receiver's `regimes` that admits the use, and stop when none does, so don't ask
about the regime. For example, RESICO (626) doesn't admit personal deductions, so a receiver with
626 and 614 gets 614 for D01.

## Workflow

1. **Read the receipt.** Find the store and the fields its portal needs. When a character is
   doubtful, crop and enlarge that area before guessing, and use the format rules in the portal's
   reference. If the receipt has a QR for invoicing, read it with
   [`read_qr.py`](scripts/read_qr.py);
   it often has every field.
2. **Pick the Uso CFDI**, as above.
3. **Open the portal's reference** from the index below. If the store isn't there, see "A new
   portal".
4. **Dry run.** Run the portal script without `--send`. Compare every printed value with the
   receipt and with the receiver's data. When the portal shows a preview of the invoice, compare
   its total with the receipt's too, because some restaurant systems round the CFDI to a cent more
   than the receipt.
5. **Submit** with `--send` when nothing is doubtful. The scripts keep a screenshot of each step
   in the evidence folder of the configuration.
6. **Report** in a few lines: store, receipt, Uso CFDI and the portal's answer, with the result's
   screenshot, since the user is likely on the phone.

## When to ask instead of continuing

Ask when:

- a field stays unreadable after enlarging it;
- the Uso CFDI isn't clear;
- the portal answers something its reference doesn't list;
- the portal asks for something not covered here.

Don't ask for confirmation otherwise, because the user wants the rules applied, not a yes for
every receipt.

A portal answer that means "try later" (the sale hasn't reached the store's system yet) is not a
failure. Tell the user, and offer to retry later.

## Stores with no portal

Small stores often print only an email or a WhatsApp number. Ask them for the invoice with
[`request_invoice.py`](scripts/request_invoice.py),
which writes the request with the receipt's data and the receiver's:

```
request_invoice.py --to <store email> --fecha 2026-10-23 --importe 82.00 --uso S01 --image <photo> \
    [--ref <receipt number>] [--field "Folio=123456" ...] [--csf] [--send]
request_invoice.py --whatsapp <number> --fecha 2026-10-23 --importe 82.00 --uso S01
```

- Pass `--ref` only when you are sure which number is the receipt's reference. Without it, the
  subject uses the date, which is enough for the store to find the sale.
- Pass every other field the receipt shows for invoicing, one `--field` each.
- Pass `--csf` when the store asks for the Constancia de Situación Fiscal.

How to send it:

- **Email.** If the configuration has a `sendmail` command, offer to send it. If not, give the
  user the subject and the text, and the photo to attach.
- **WhatsApp.** If you have a tool that sends WhatsApp messages, offer to send it with the photo.
  If not, give the user the `wa.me` link the script prints, which opens the chat with the message
  filled in, and remind them to add the photo.

Before sending an email or a message, show it to the user and wait for an explicit yes. It speaks
for the user, and you don't know what they have already talked about with the store. A
configuration with `confirm_before_sending = false` turns this off. Portal submissions don't need
it, because a portal only issues what the receipt and the configuration say.

## Running the scripts

The scripts are in `scripts/` and need Python 3.10 or later; on 3.10 they also need `tomli`. The
portal scripts need Playwright with its Chromium, and `read_qr.py` needs `pillow` and `zxing-cpp`.
Run any script with `--help` for its arguments.

- With `uv`, `uv run scripts/<script>.py` installs what the script declares at its top.
- Without it, install them with pipx, which keeps them in their own environment, and run the
  scripts with that environment's Python (`~/.local/share/pipx/venvs/playwright/bin/python`):

  ```
  pipx install playwright
  pipx inject playwright pillow zxing-cpp
  playwright install chromium

  # Only on Python 3.10, which doesn't have tomllib:
  pipx inject playwright tomli
  ```

## Portal index

| Store | Reference | Script | Blocks IPs outside Mexico |
|---|---|---|---|
| Alsea: Starbucks, Domino's, Burger King, Chili's, Vips, ... | [`reference/alsea.md`](reference/alsea.md) | [`alsea.py`](scripts/alsea.py) | no |
| Carlscol (Carl's Jr in Colima and Manzanillo) | [`reference/carlscol.md`](reference/carlscol.md) | [`carlscol.py`](scripts/carlscol.py) | no |
| Farmacias Guadalajara | [`reference/farmacias-guadalajara.md`](reference/farmacias-guadalajara.md) | [`farmacias_guadalajara.py`](scripts/farmacias_guadalajara.py) | yes |
| ICR (Carl's Jr and other restaurants) | [`reference/icr.md`](reference/icr.md) | none yet | no |
| iShop / Mixup | [`reference/mixup.md`](reference/mixup.md) | none yet (steps in the reference) | yes |
| Miniso (Diverza portal) | [`reference/miniso.md`](reference/miniso.md) | [`miniso.py`](scripts/miniso.py) | no |
| OXXO | [`reference/oxxo.md`](reference/oxxo.md) | [`oxxo.py`](scripts/oxxo.py) (first step only) | yes |
| Restaurants on Soft Restaurant, with two portals (mefacturo.com and mefacturo.mx links) | [`reference/soft-restaurant.md`](reference/soft-restaurant.md) | [`soft_restaurant.py`](scripts/soft_restaurant.py) (mefacturo.com only) | no |
| Walmart | [`reference/walmart.md`](reference/walmart.md) | [`walmart.py`](scripts/walmart.py) | no |

## A new portal

Look for the portal's URL on the receipt first, then search the web for "facturación <store>".
Explore the portal by hand, but issue the invoice only from a script, so the next receipt of that
store goes the same way and a mistake in the exploration can't issue a wrong CFDI.

1. Open it with Playwright and list the inputs, selects and buttons of each step, with
   screenshots. Read each screenshot; the visible text often explains the fields.
2. Register a dialog handler before doing anything (`page.on("dialog", ...)`). Playwright
   dismisses `alert()` and `confirm()` without a trace, and many portals report errors that way.
3. Fill each step and print what the fields have before moving on. Read-only datepickers,
   messages that fade out, and fields that only appear after another choice are common. Stop
   before the button that issues the invoice.
4. Copy
   [`scripts/template.py`](scripts/template.py)
   to `scripts/<store>.py` and write one method per step of the portal.
   Run it without `--send` and check the values, as in the workflow.
5. Issue the invoice with the script's `--send`.
6. Write it down for the next time:
   - `reference/<store>.md`, copied from
     [`reference/template.md`](reference/template.md);
   - a row in the index above, keeping it in alphabetical order.

A 403 from Imperva/Incapsula, Cloudflare, Akamai or similar, with any user agent, while the same
page opens from a connection in Mexico, means the portal blocks IPs outside Mexico. Set
`blocks_foreign_ips = True` in its script (see "Proxy"), and mark it in the index. Some portals
also block curl and headless browsers from Mexico; the scripts already open a browser that they
don't distinguish from a normal one, so explore those with Playwright, not curl.

## Proxy

Some portals block IPs outside Mexico, so they fail when the scripts run on a server abroad. For
those, the scripts browse through the `proxy` of the configuration, which has to have an IP in
Mexico, for example an SSH SOCKS tunnel to a machine at home. When nothing listens on the proxy's
port, they run `proxy_command` to open it, and leave it open for the next receipts. With no
`proxy`, they browse directly, which works when they run in Mexico.

If the proxy can't open, the script stops with a clear message; the machine at home may be off.
