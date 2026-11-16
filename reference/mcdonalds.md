# McDonald's

- **Issuer:** the franchise company that runs the restaurant, printed at the top of the receipt
- **Portal:** https://www.facturacionmcdonalds.com.mx/
- **Script:**
  [`mcdonalds.py`](../scripts/mcdonalds.py)

The portal is run by Emite, an invoicing provider, for every McDonald's restaurant. It doesn't ask
for the Uso CFDI and chooses it by the receiver's regime; for regime 605 it issued S01. So after
issuing, the script saves the XML and warns when the use isn't the one asked for.

The page has no field for the use, whatever the receiver: its code fills only the regime options,
and the lines that filled the use are commented out. To get another use, the portal says to email
facturacion@facturacionmcdonalds.com.mx with the issuer's name in the subject, the Constancia de
Situación Fiscal in PDF and a photo of the receipt attached (one receipt per email), and the payment
method and the Uso CFDI in the body.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Número de restaurante | the 4 digits before the restaurant's name, such as "0123 McDonalds Centro" |
| Número de ticket | "Nro. Ticket", without the zeros on its left |
| Número Reg. o Caja | "Reg." |
| Fecha | "Fecha", as dd/mm/yyyy |
| Importe total | the total |

## Flow

1. **Información del Ticket.** The date picker clears a filled date, so the script types it. When
   the ticket fields are complete, the portal looks the ticket up and enables the receiver's fields.
2. **Información del receptor.** RFC, name, postal code, regime and email. The regime options load
   when the RFC field loses the focus. The button "Realizar facturación" is enabled when a key is
   released in the form, so the script presses one.
3. **Confirma tus datos.** "Realizar facturación" opens a window with the receiver's data. The dry run
   stops here, and "Aceptar" issues the invoice.

## Known answers

| Message | Meaning |
|---|---|
| `¡Factura generada exitosamente! La factura con el UUID ... y folio ...` | Issued; the CFDI also goes by email. |
| `¡El ticket ha sido facturado anteriormente!` | Already invoiced. It shows when the ticket is looked up, with links to the XML and the PDF. |
| `Error en el ticket. Verifica los datos ingresados.` | No ticket with that data. |

## Limits

- **Deadline:** the month of the purchase, as the receipt says.

## How the CFDI arrives

By email to the address of the form, and from the links of the result window.
