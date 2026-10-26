# Liverpool

- **Issuer:** Distribuidora Liverpool, S.A. de C.V.
- **RFC:** `DLI931201MI9`
- **Portal:** https://facturacionclientes.liverpool.com.mx
- **Script:**
  [`liverpool.py`](../scripts/liverpool.py)

The receipt says "Visita, factura y evalúanos en liverpool.com.mx". The "Facturación" link at the
bottom of liverpool.com.mx opens the portal, which doesn't need an account.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Código de facturación | the 20 characters under "CÓDIGO DE FACTURACIÓN", near the end, in 4 groups of 5 (`ABCDE FGH1J KLMNO PQRST`). The receipt underlines the digits, so a character without a line is a letter: an underlined `1` is a one, and `I` and `L` without it are letters |
| Monto a facturar | the line `TOTAL M.N. $`, with cents |

## Flow

1. The code and the total go in "Datos del ticket", and `Buscar ticket` looks the receipt up. The
   portal answers "Ticket encontrado exitosamente" in a green banner.
2. The RFC goes in "Datos fiscales", and its `Continuar` looks it up. When the RFC has invoiced
   before, a dialog lists the data the portal keeps for it (name, postal code, email and regime),
   and the rest of the form stays disabled until one row is selected. That data can be out of date,
   so the script selects the first row and then writes every field again.
3. Régimen fiscal and Uso CFDI are dropdowns, and the Uso CFDI options depend on the regime. The
   name goes in three fields: Nombre(s), Apellido paterno and Apellido materno. The portal
   uppercases the email.
4. The last `Continuar` only opens a summary of the data, with "Corregir datos" and "Generar
   factura". When the data differs from the last invoice of that RFC, the summary says it will be
   saved. "Generar factura" issues the invoice.

## Known answers

| Message | Meaning |
|---|---|
| `Ticket encontrado exitosamente. Puedes continuar con el proceso de facturación.` | the code and the total match a receipt |
| `El código ingresado no es válido. Verifica e intenta nuevamente.` | no receipt has that code; check the reading |
| `Monto incorrecto` | the code is right, but the total isn't the receipt's |
| `Este código ya fue facturado. Por favor, prueba con otro código.` | the receipt already has an invoice |

The portal finds an invoiced receipt like any other and shows the summary. It only answers "ya fue
facturado" after "Generar factura", so a dry run can't tell that a receipt is already invoiced.

A made-up code and the code of an invoiced receipt with one character changed, at the end or in the
middle, both answered "no es válido". So a misread character doesn't find someone else's receipt.

## Limits

- **Deadline:** the calendar year of the purchase. The portal's home page says that Liverpool
  doesn't invoice purchases from previous years.

## How the CFDI arrives

It doesn't arrive by email, even though the form asks for an address. Get the XML from the SAT's
download of received CFDIs instead.
