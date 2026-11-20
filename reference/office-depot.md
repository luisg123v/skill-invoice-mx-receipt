# Office Depot

- **Issuer:** Office Depot de México, S.A. de C.V.
- **RFC:** `ODM950324V2A`
- **Portal:** https://facturacion.officedepot.com.mx/
- **Script:**
  [`office_depot.py`](../scripts/office_depot.py)

The receipt ends with "Factura tu compra y/o modifica tus datos escaneando el QR". The portal
answers 403 to IPs outside Mexico. It also has tabs for purchases on the website and app, by phone
and on Mercado Libre; the script only covers store receipts.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Número de ticket (ITU) | `ITU:`, above the barcode, 30 characters. They seem to be the date, the store, the register and the receipt number, with five letters and digits at the end, e.g. `2026111700123011000123456ABCD1`. The last five mix letters and digits, and the letter O looks like the digit 0. When it stays doubtful, try both: the wrong one gets `Error al validar el ITU`. |
| Monto | `Total`, with two decimals |
| (forma de pago) | The portal doesn't ask for it. |

## Flow

1. A welcome dialog opens over the page; the script closes it with "Omitir".
2. The first step asks for the ITU and the total, with "Tienda" chosen by default. "Validar y
   Continuar" checks them.
3. The second step asks for RFC, person type (`F - Persona física` or `M - Persona moral`), regime,
   Uso CFDI, postal code, name and email. The menus show each option as code and description,
   e.g. `605 - Sueldos y Salarios e Ingresos Asimilados a Salarios`. The address is optional.
4. "Facturar" issues the invoice and shows the third step, "Tu factura".

Validating a receipt reserves it for that browser for half an hour. Another browser that tries it
in that time gets `FES002-ITU NO DISPONIBLE`, even from the same IP. To free it, "Salir" asks
"¿Deseas cancelar el proceso de facturación?", and "Confirmar" frees the receipt. The dry run does
both before closing the browser, so the next run can validate the receipt right away. A run that
stops before that, e.g. on an error, leaves the receipt reserved for the half hour.

## Known answers

| Message | Meaning |
|---|---|
| `Factura generada correctamente. Tu factura será enviada al correo: <email>` | Issued. |
| `El ticket ingresado ya ha sido previamente facturado. ¿Qué deseas hacer?` | Already invoiced. It offers "Consultar factura" and "Refacturar". |
| `FES002-ITU NO DISPONIBLE, ESTE ITU ESTA SIENDO UTILIZADO, INTENTE EN MEDIA HORA POR FAVOR` | The receipt is reserved by another browser, e.g. an earlier run; retry in half an hour. |
| `Error al validar el ITU` | Not found, e.g. a misread ITU or total. The page shows nothing; the script reads it from the portal's answer to the validation. |

## Limits

- **Deadline:** the receipt says "de requerir factura deberá solicitarla a más tardar dentro del
  mes siguiente a la fecha de emisión del ticket".

## How the CFDI arrives

By email to the address of the form. The portal suggests checking the spam folder.
