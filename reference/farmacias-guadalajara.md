# Farmacias Guadalajara

- **Issuer:** Farmacia Guadalajara
- **RFC:** `FGU830930PD3`
- **Portal:** https://www.movil.farmaciasguadalajara.com/facturacion/
- **Script:**
  [`farmacias_guadalajara.py`](../scripts/farmacias_guadalajara.py)

The portal blocks IPs outside Mexico and headless browsers, so the script needs the proxy (see
"Blocking").

## Where the data is on the receipt

Below "COPIA CLIENTE":

| Portal field | On the receipt |
|---|---|
| Folio factura | `FOLIO FACTURA`, three groups of 6 digits (`123456-123456-123456`) |
| Caja | `CAJA <n> - <cashier>`, above the products |
| Fecha de compra | `FECHA COMPRA`, yyyy-mm-dd and the time |
| No. Ticket | `No TICKET` |

The QR ("Escanea el QR para facturar") opens the portal with all four already filled, plus the
store number:

```
https://www.movil.farmaciasguadalajara.com/facturacion/?folio=<folio>&caja=<caja>&ticket=<ticket>&fecha=<yyyy-mm-dd>&tienda=<store>
```

So read it with
[`read_qr.py`](../scripts/read_qr.py)
and pass it with `--qr` instead of reading the numbers.

## Flow

1. "Validar Folio" checks the folio and opens a dialog with the branch ("Tu compra fue realizada
   en SUC ..."). "SI" enables the next step.
2. Typing the RFC loads the data the portal keeps for it, which may be old, so the script sets
   every field anyway. "Quiero recibir la factura por correo" shows the email fields.
3. "Obtener Factura" opens "¿Está seguro que quiere facturar?"; "Aceptar" issues it. The answer
   of the portal's service already has the XML and the PDF (base64), and the script saves them in
   the evidence folder.

## Known answers

| Message | Meaning |
|---|---|
| `Factura Generada ... serie: <serie> Folio: <folio>` (code 200, `Aprobada`) | Issued. |
| `Factura previamente generada` (code 201) | Already invoiced. The answer has the same files again, so this is how to download them. |
| `El ticket N no corresponde a una venta, no se puede facturar` (code 409) | Not a sale of the pharmacy, for instance gift cards that the store sells on behalf of others, such as App Store cards. There is nothing to invoice. |

## Limits

- **Deadline:** 30 days from the purchase, as the portal says.

## Blocking

Akamai answers 403 to IPs outside Mexico and, from Mexico, to curl with any user agent. It also
answers 403 to Playwright's default headless browser, even with the user agent changed, and to the
full Chromium without a window while its user agent says "HeadlessChrome". The full Chromium
without a window and with the user agent changed, which is what the scripts open, gets in.

## How the CFDI arrives

By email from `cfd@fragua.com.mx`, with the XML and the PDF attached, but it can take hours. If it
never arrives, the files the script saved are the same CFDI.
