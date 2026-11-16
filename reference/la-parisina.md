# La Parisina

- **Issuer:** GRUPO PARISINA
- **RFC:** `GPA930101QI7`
- **Portal:** https://facturacion.laparisina.com.mx/
- **Script:**
  [`la_parisina.py`](../scripts/la_parisina.py)

The receipt points to www.laparisina.com.mx, but that site doesn't open. The invoicing portal is
the one above.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Estado | The state in the branch's address, near the top ("Guadalajara, Jalisco") |
| Sucursal | The 4 digits of "Sucursal" at the end ("Sucursal 1401 GUADALAJARA CENTRO") |
| Caja | "Caja" at the end |
| Ticket | "No Ticket" at the end, the same number as the top's "No TICKET" |
| Importe | "Total a pagar" |
| Fecha | "Fecha" at the end, dd/mm/yyyy; the script types it as yyyy-mm-dd |

## Flow

1. Choose "Fisica", type the RFC and press "Buscar".
2. The first time, the portal answers "No se encontró tu RFC, Regístrate!!" and asks to register
   it, with the name, the address, the state, the regime and the email. After "Registrar", it
   shows the data in a dialog, sometimes says that the system isn't available, and then says "Se
   realizo registro exitoso". The script registers the RFC even without `--send`, because the
   portal needs it to show the ticket's form, and registering doesn't issue anything.

   The text fields reject "Á", "ü" and "Ü", though they take the other accents and "ñ". So the
   script writes those letters without the accent in the address, and stops when the name has
   one, because the name has to be the one of the Constancia. The exterior number rejects "Ñ" but
   takes other letters, e.g. "12-A" or "S/N".
3. The portal shows the data it keeps for the RFC and asks "¿Sus datos estan correctos?". It
   shows the regime in the box of "Entre calles" and leaves the box of the regime empty. The
   regime can't change per invoice, so the script stops when the Uso CFDI needs another one.
4. "¿Deseas Facturar?" opens the ticket's form. The branches load after the state.
5. "Facturar" issues the invoice at once, with no preview. The answer comes in a dialog.

## Known answers

| Message | Meaning |
|---|---|
| `Se Genero la Factura No. 1401-12345` | Issued. |
| `Los campos en rojo estan incorrectos o vacios` | The registration rejected the fields in red; nothing is saved. |
| `ESTE TICKET YA FUE FACTURADO` | Already invoiced. |
| `NO EXISTE EL TICKET, VERIFICAR NUMERO DE FOLIO Y NUMERO DE CAJA` | No ticket with that number in that register. |

The portal only answers about the ticket after "Facturar", so a dry run can't tell that a ticket
is already invoiced or doesn't exist.

## Limits

- **Deadline:** the portal doesn't say. It dates the invoice on the day it is requested.

## How the CFDI arrives

By email from "GRUPO PARISINA" <services@mysuitecfdi.com>, with the subject "Envío de CFDI" and the
XML and the PDF attached. The portal says it takes up to 24 hours, but it arrived within a minute.
