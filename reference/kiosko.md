# Kiosko

- **Issuer:** Super Kiosko
- **RFC:** `SKI020328NK5`
- **Portal:** https://facturas.mikiosko.mx
- **Script:**
  [`kiosko.py`](../scripts/kiosko.py)

The portal is behind Cloudflare, which answers 403 to curl but lets the script's browser in. It has
an invisible reCAPTCHA, which shows no challenge.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Referencia | the 23 digits under "Facturación en línea", after the portal's URL (`0123 4101 0765 4321 0123 456`). The first 16 have the store and the numbers of the `FOLIO` line in the header (`FOLIO 1234-1-1-7654321`), so use that line to check a blurry reading |

## Flow

1. A notice about checking that the RFC is active at the SAT opens first; `Aceptar` closes it.
2. The receiver's fields are RFC, Razón Social, Código Postal and email. The regime and Uso CFDI
   options load while the RFC is typed, so the script types it instead of filling it. Both are
   dropdowns whose options read `<code> - <name>`, and the Uso CFDI list doesn't depend on the
   regime. When the portal already knows the RFC, it fills the name, the postal code and the email
   it has for it. The script waits for that, then clears each field and types the configuration's
   values.
3. The reference goes in the "Tickets" section, and `Agregar` looks it up. The ticket appears in
   the table with its folio, date and amount, and the script prints its lines to compare them with
   the receipt. The field has a mask, so the script types the reference from the start of the field
   and checks it before `Agregar`.
4. `Facturar` issues the invoice right away, with no preview, and shows it with "Descargar PDF"
   and "Descargar XML" buttons. The portal's answer has both files, and the script saves them in
   the evidence folder.

The portal can put up to 10 receipts on one invoice, all with the same Uso CFDI. Pass one
`--referencia` for each receipt; the script adds them in that order and prints the total of all.

## Known answers

| Message | Meaning |
|---|---|
| The invoice with its download buttons | issued |
| `Referencia de ticket ya facturado [ <reference> ]` | the receipt already has an invoice |
| `Referencia no encontrada [ <reference> ]` | no receipt has that reference; check the reading |
| A dialog titled "Error" | the portal's message says why; the script prints it |

The portal finds the receipt by the first 16 digits of the reference, the store and the folio, and
doesn't check the last 7. This was tested with an invoiced receipt:

- Changing the last 7 digits, even to zeros, still answered "ya facturado".
- Adding or subtracting 1 to the folio found the store's previous and next receipts, which belonged
  to other people.

So a misread folio can invoice someone else's purchase. Before submitting, check that the folio,
date and amount the dry run prints are the receipt's.

## Limits

- **Deadline:** the calendar month of the purchase. The receipt prints the last day ("Fecha límite
  de facturación"), and the portal shows the period after a receipt is added.

## How the CFDI arrives

By email within a few seconds, from `notificaciones@mikiosko.com.mx`, with the XML and the PDF
attached.
