# Cervecería de la Costa

- **Issuer:** DIRECTO DE LA COSTA SA DE CV
- **RFC:** `DCO210921CR5`
- **Portal:** https://facturacion.cerveceriadelacosta.com/facturar
- **Script:**
  [`cerveceria_de_la_costa.py`](../scripts/cerveceria_de_la_costa.py)

The portal, "Costa Factura", covers the brewery's own stores ("Tiendas de la Costa"). Its pages
call an API on efacturaglobal.gocsa.com.mx, which is behind Cloudflare. Cloudflare blocks `curl`
and a bare headless browser there, but lets the scripts' browser through.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Ticket number | "Referencia", under "Facturación en Línea", 13 digits such as 1234567890123. They are the store (5 digits), two digits of the register, and the register's folio (6 digits). |
| Total | "TOTAL$". The script checks it against the ticket the portal finds. |

## Flow

1. **Datos fiscales.** The RFC search only starts with typed keys. It returns the receiver's form:
   person type (read-only), postal code, name, email, regime and Uso CFDI. The regime and the Uso
   CFDI are dropdowns whose options start with their code ("626 - ...", "S01 - ...").
2. **Tickets.** "Buscar ticket" adds the ticket to a table with its date and amount. Several tickets
   can go on one invoice, and the script adds each `--ticket` with its `--total`. The script reads
   the answer of the portal's ticket service, which has the ticket's date and amount, or the error.
3. **Confirmación.** A summary with every field, and the payment method, which the portal fills
   with the sale's ("Tarjeta de crédito") a moment after the summary shows. The dry run stops here.
   "Solicitar factura" issues the invoice and shows "Enviando solicitud..." for up to some minutes.

The folio is consecutive, so a misread digit of it usually gives another person's ticket of the
same day. The date doesn't help to notice it, and the total helps only in part, because the amounts
repeat. So the script stops when the total differs, but check the ticket number against the
receipt before issuing.

## Known answers

| Message | Meaning |
|---|---|
| `Ticket agregado correctamente` | The ticket was found and added. |
| `El numero de ticket ya fue facturado y no se puede usar` | Already invoiced. |
| `El ticket no fue encontrado o es inválido, verifique bien el Folio` | No ticket with that number. |

## Limits

- **Deadline:** the first day of the next month, as the receipt says in "Fecha límite de
  facturación antes de".

## How the CFDI arrives

By email from `facturae@gocsa.com.mx` ("DIRECTO - CFDI - FACTURA - <serie><folio>"), with the XML
and the PDF attached. It took several minutes. That address belongs to the invoicing provider,
which also sends for other companies.
