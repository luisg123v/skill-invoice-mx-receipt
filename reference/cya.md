# C&A

- **Issuer:** C&A MEXICO
- **RFC:** `CME961203360`
- **Portal:** https://facturacion.cyamoda.com/
- **Script:**
  [`cya.py`](../scripts/cya.py)

The portal is linked as "Facturación" on cyamoda.com. It doesn't invoice tickets paid with a gift
card or a welcomeCard.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Tienda | "TIENDA", under "Datos para Facturar", e.g. 012 |
| Ticket | "TICKET", 14 digits |
| Fecha | "FECHA", as dd/mm/yyyy; the script types it as yyyy-mm-dd, as the portal takes it |
| Total | "TOTAL" |

## Flow

1. **Buscar documentos.** Store, ticket, date and total, and the terms checkbox. The portal finds
   the ticket before going on.
2. **Indicar sus datos fiscales.** RFC, name, postal code and email. The regime options load after
   the RFC is typed. The value of each option is in the form "code - name", not the code alone,
   e.g. "626 - Régimen Simplificado de Confianza", and so are the Uso CFDI options, e.g.
   "S01 - Sin efectos fiscales".
3. **Validar datos.** A summary with the ticket and the receiver's data. The dry run stops here.
4. **Generar su CFDI.** "Siguiente" in the summary issues the invoice.

## Known answers

| Message | Meaning |
|---|---|
| `Los datos del ticket solicitados se encuentran disponibles para facturar` | The ticket was found. |
| `Ticket timbrado correctamente` | Issued; the page offers the PDF and the XML. |
| `TICKET YA FACTURADO - Tienda: ... \| Ticket: ...` | Already invoiced. |
| `Los datos del ticket solicitados NO SE ENCONTRARON` | No ticket with that data. |
| `Los datos del ticket solicitados NO se encuentran disponibles para facturar, contiene metodos de pago no faturables` | A ticket paid with a gift card. It's also the answer to a made-up ticket, so it can mean that the ticket doesn't exist. |

## Limits

- **Deadline:** December 31 of the year of the purchase, as the receipt says.

## How the CFDI arrives

By email from notificaciones_facturacionpr@cyamexico.com ("Factura del ticket <ticket>"), about an
hour after issuing. Both files come named "attachment", and the XML as `text/plain`, so a program
that goes by the name or the type doesn't see the XML.
