# Carlscol (Carl's Jr in Colima and Manzanillo)

- **Issuer:** Carlscol
- **RFC:** `CAR1402278J9`
- **Portal:** https://carlscol.libellum.com.mx
- **Script:**
  [`carlscol.py`](../scripts/carlscol.py)

Carlscol runs the Carl's Jr branches of Colima and Manzanillo. It is a different company from ICR
([`icr.md`](icr.md)).
The receipt prints the portal under "Puedes obtener tu factura en el portal".

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Número de orden | `Ticket#`, below "Mesa" |
| Fecha orden | the date next to the server's name. The receipt prints it as mm/dd/yyyy (`10/25/2026 2:30 PM` is October 25), and the portal wants dd/mm/yyyy (`25/10/2026`) |
| Monto orden | `TOTAL` |
| Sucursal | the branch name at the top (`CARL'S JR ZENTRALIA`). The portal lists Diosa del Agua, Manzanillo, Punto Bahia, San Fernando, Sendera and Zentralia |

## Flow

1. Home page: RFC, date, amount, order number and branch, then "FACTURAR". A slideshow of
   instructions may cover the form; its "ACEPTAR" button closes it.
2. `transaccion.aspx`: razón social, email, CP, regime and Uso CFDI are required. The address and
   "Ultimos 4 digitos tarjeta de pago" are optional. Choosing the regime reloads the page. Uso
   CFDI offers only G03 and S01.
3. "DATOS CORRECTOS Y FACTURAR" should open a dialog ("¿Está seguro que los datos ingresados son
   correctos?") before issuing. Clicked while the page is still loading after the regime reload,
   it issues the invoice right away, without the dialog. That is why the script doesn't click it
   without `--send`, and waits for the page's scripts before clicking it.

## Known answers

| Message | Meaning |
|---|---|
| `LA FACTURA HA SIDO ENVIADA AL CORREO DE CONTACTO QUE PROPORCIONÓ.` | Issued. |
| `ESTE COMPROBANTE YA HA SIDO GENERADO...` (page `historial.aspx`) | Already invoiced. The page has "DESCARGAR XML", "DESCARGAR PDF" and "ENVIAR CORREO", so entering the same receipt again is how to download the files. |

## Limits

- **Deadline:** the month of the purchase, as the receipt says.

## How the CFDI arrives

By email from `facturacion@correolibellum.com.mx`, with the XML and the PDF attached, but it can
take hours. Wait for it before downloading the files from the portal.
