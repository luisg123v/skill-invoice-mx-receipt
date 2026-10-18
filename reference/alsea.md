# Alsea (Starbucks, Domino's, Burger King, Chili's, Vips, ...)

- **Issuer:** Cafe Sirena, for Starbucks; each brand has its own company
- **RFC:** `CSI020226MV4` (Cafe Sirena)
- **Portal:** `https://alsea.interfactura.com/wwwroot?opc=<brand>`
- **Script:**
  [`alsea.py`](../scripts/alsea.py)

`<brand>` is the name in the portal's left menu (`Starbucks`, `Dominos`, `BurgerKing`, ...). Check
the exact `opc` value of a brand in the menu link before using it.

## Where the data is on the receipt

A block near the bottom headed `====Datos para Facturar====`:

| Portal field | On the receipt |
|---|---|
| Ticket | `Ticket :`, 9 digits |
| Tienda | `Tienda :`, 5 digits |
| Fecha | `Fecha :`, printed as dd-mm-yyyy; the portal wants dd/mm/yyyy |

## Flow

1. The first step asks for RFC, ticket, store and date. Errors come back as a JavaScript `alert()`
   or `confirm()`, not on the page; the script prints them as `DIALOG:`.
2. The second step asks for persona (`FISICA`), RFC, first names and last names in separate
   fields, postal code, regime, Uso CFDI and email. The Uso CFDI list loads after the regime.
3. After `Enviar`, the page says the invoice will be emailed. The portal turns the email into
   uppercase, which is harmless.

## Known answers

| Message | Meaning |
|---|---|
| `El Ticket ya fue facturado. Desea que se le reenvie?` | Already invoiced. The script answers No. Answer Yes only to get the email again. |

## Limits

- **Deadline:** 30 calendar days from the purchase, and within the same calendar year, as the
  receipt and the portal say.
- **Not invoiced:** gift card top-ups and prepaid coupons.

## How the CFDI arrives

By email from `mx_ms@notificaciones.interfactura.com`, usually within a minute, with links to the
PDF and the XML instead of attachments. That is why the script sends it to `email_links` when the
configuration has one. The subject has the form `Facturación Electrónica Alsea: Ticket <number>
Folio ...`, where the long number has the store and the ticket.
