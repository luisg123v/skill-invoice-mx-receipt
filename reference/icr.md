# ICR (Carl's Jr and other restaurants)

- **Issuer:** ICR
- **RFC:** `ICR9305317G4`
- **Portal:** https://facturacion4.icr.mx (EDX Solutions), whose "Genere su factura aquí" button
  opens the form at https://retailedx.com/ICR4/
- **Script:** none yet

The receipt prints the portal under "Necesita Factura?", along with the email
`facturacion@icr.mx`. There is no script yet, and what follows comes from a receipt invoiced by
hand, so explore the portal as "A new portal" in SKILL.md says the first time.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| No. Referencia | `REFERENCIA`, 14 digits at the end of the receipt, below the portal address. It is also printed under "Comedor" near the top, after an `@` |

## Flow

Four steps: 1 Ingresar Ticket, 2 Datos Fiscales, 3 Confirmar Datos, 4 Descargar Factura. The first
asks for "No. Referencia" (`#txt_ticket`) and "RFC Cliente" (`#txt_rfccliente`). The "Siguiente"
button submits it; pressing Enter doesn't. The portal shows its messages in a "Notificación"
modal, not in an `alert()`.

## Known answers

| Message | Meaning |
|---|---|
| `El ticket con el número N no esta completo y no tiene un conector configurado.` | The portal has no ticket with that reference. A made-up reference gets it too, so check the reference first; if it is right, the sale hasn't reached the portal yet, so retry later. |

## Limits

- **Deadline:** 30 days from the date of the receipt.

## How the CFDI arrives

Unknown yet. The CFDI has one line per receipt: "Consumo del ticket <number> con fecha de
expedición ...".
