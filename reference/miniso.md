# Miniso

- **Issuer:** Miniso Mexico
- **RFC:** `MME160812J15`
- **Portal:** https://tickets.diverza.com/miniso-mexico/facturar-ticket
- **Script:**
  [`miniso.py`](../scripts/miniso.py)

The receipt points to `https://www.miniso.com.mx/facturacion`, which links to the real portal, run
by Diverza. The Miniso page has a reCAPTCHA; the Diverza portal doesn't.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Número de ticket | the 19 digits under the barcode near the bottom. They are the store (5 digits), the register (2), the transaction (6, also printed as `SECTXN:<n>`) and the date (ddmmyy). Use the `SECTXN` value to check a blurry reading |
| Fecha | in the header (`Fecha: 10/23/2026 18:00:00`, month first) and next to the barcode (`2026-10-23 06:00`). The portal wants dd/mm/yyyy |
| Monto | the `Total` line (not `Subtotal`). Discounts are already applied |

## Flow

1. The first step asks for receipt, date and amount. The date field ignores typed text; it only
   takes a click in its calendar, which shows the current month only.
2. `Buscar` shows "Ticket encontrado" and a `Continuar` button (`#continue_button`).
3. The second step asks for RFC, name (one field, the full name), postal code, regime, Uso CFDI,
   email twice, and the privacy notice checkbox. "Recordar mis datos" is left unchecked.
4. `Facturar` (`#billing_button`) opens a modal: "Éxito. Se ha generado la factura <UUID> del
   ticket <ticket> y se ha enviado al correo electrónico ...", with XML and PDF download links.

The portal can also put several receipts on one invoice. The script doesn't, because each receipt
can need a different Uso CFDI.

## Limits

- **Deadline:** the calendar month of the purchase, as the portal says ("Facturación disponible
  sólo dentro del mes de su compra").

## How the CFDI arrives

By email within a minute, from `servicios@buzonfiscal.com`, with the XML and the PDF attached.
