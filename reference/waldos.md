# Waldo's

- **Issuer:** Waldo's Dolar Mart de México, S. de R.L. de C.V.
- **RFC:** `WDM990126350`
- **Portal:** https://facturacion.waldos.com/facturacion/
- **Script:**
  [`waldos.py`](../scripts/waldos.py)

The "Facturación" link of waldos.com.mx opens the portal above, which shows the form in a frame.
The script opens the frame's page directly. The store's website answers 403 to IPs outside Mexico,
but the portal doesn't.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Fecha | `Fecha`, at the top, dd/mm/yyyy; the script types it as yyyy-mm-dd |
| Tienda | `Tienda`, at the top |
| Importe total del ticket | `Total`, with cents |
| Caja | `Caja`, at the top |
| Cajero | The number of `Cajero`, before the cashier's name, e.g. `123456` |
| Ticket | `Transacción`, at the top. The card's part prints it with zeros in front ("Número de transacción"). |

## Flow

1. The first page asks for the RFC and the receipt's data. The date field has a date picker that
   keeps its own date, today's at first, and writes it back into the field when the form is sent.
   It reads a date typed key by key, so the script types it that way. "Buscar" looks the receipt
   up.
2. A dialog, "DATOS DE FACTURA", asks for the email, RFC, regime, Uso CFDI, name and postal code,
   with an optional address. Choosing the regime reloads the uses it admits; for 605 it offers
   only S01. The form comes with the RFC typed on the first page. When the portal has invoiced
   that RFC before, it also fills the other fields with the data it keeps for it.
3. "Generar factura" issues the invoice, with no preview.

## Known answers

| Message | Meaning |
|---|---|
| `La factura se generó correctamente y se ha enviado a su correo electrónico.` | Issued. The dialog has links to the XML and the PDF. |
| `El ticket ya ha sido facturado` | Already invoiced. The same dialog has links to the XML and the PDF. |
| `El importe proporcionado [$<total>] no corresponde al ticket de compra.` | The receipt exists, but with another total; check the total and the transaction. |
| `Verifique los datos de su ticket e intente de nuevo.` | Not found, e.g. a wrong date or store. |
| No message, form or dialog | The receipt was invoiced to an RFC other than the one on the first page. The portal tries to open the dialog of the invoice's files, but leaves it out of the page. |

## Limits

- **Deadline:** the portal says "Después de su compra tiene hasta 90 días para facturar su
  ticket".

## How the CFDI arrives

By email to the address of the form, as the portal says. The script also saves the XML and the PDF
from the dialog of the invoice's files, both when it issues the invoice and when the receipt is
already invoiced. For questions, the portal gives `aclaracionescfd@waldos.com`.
