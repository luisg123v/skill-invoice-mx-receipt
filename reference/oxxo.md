# OXXO

- **Issuer:** Cadena Comercial OXXO
- **RFC:** `CCO8605231N4`
- **Portal:** https://www4.oxxo.com/facturacionElectronica-web/views/layout/inicio.do
- **Script:**
  [`oxxo.py`](../scripts/oxxo.py)

The site is behind Imperva (Incapsula), which answers 403 to any IP outside Mexico, browser or curl,
IPv4 or IPv6.

## Where the data is on the receipt

In the upper third of the receipt:

| Portal field | On the receipt |
|---|---|
| Fecha | top right, with the time; the portal only wants the date |
| Folio | `Fol_Vta:`, left, below the item list |
| ID de venta | `ID=` (or `ID:`), just below the folio |
| Total | `Total: $`, right, level with the folio; not the "IVA INCLUIDO" line below it |

The ID de venta has the shape `NN LLL NN AAA N`: 2 digits, 3 letters, 2 digits, 3 letters or
digits, and 1 or 2 digits, such as `10ABC20XYZ1`. So a leading `T0` in a blurry photo is really
`10`, and an ambiguous `I` in the letter block is an `L` if the portal rejects the `I` version.

## Flow

1. An informative dialog about the ID opens on load; the script closes it.
2. The date field is a read-only datepicker. The script opens it, moves back to the right month and
   clicks the day, then checks the field. An empty date makes the portal answer "ejercicio fiscal
   diferente", which is misleading, so the script stops instead of submitting.
3. `Validar Ticket` answers with a message that fades out after a few seconds, so the script
   checks for it repeatedly. `#form:continuar` becomes enabled when the receipt is valid.
4. `Continuar` enables the receiver's form on the same page. The regime options load when the RFC
   field loses the focus, and the Uso CFDI options load after the regime is picked. Both are
   PrimeFaces menus with the names of the SAT catalogs and no codes, so the script picks them by
   name, ignoring accents, because the portal leaves some out: "Adquisición de mercancias" has the
   first accent but not the second. The address is optional; the script fills the name and the
   postal code.
5. "Previsualiza Factura" shows the receipt's data but leaves the receiver's empty, so it doesn't
   help to check them.
6. `Generar Factura` issues the invoice and then asks for the email, with `Enviar correo`, next to
   `Descargar PDF` and `Descargar XML`. The script sends the CFDI to the email.

## Known answers

| Message | Meaning |
|---|---|
| `El ticket ingresado es válido` | Valid; it can show less than an hour after the purchase. |
| `La búsqueda del Folio N, no tuvo éxito, favor de volver a intentar.` | The sale isn't in OXXO's system yet, which can take more than a day; retry later. |
| `El campo ID de Venta es inválido, verifícalo en tu ticket de compra.` | The ID has the wrong shape. |
| `No se permite facturar tickets que fueron emitidos en un ejercicio fiscal diferente.` | Also the answer to an empty date; check the date field first. |
| `El mail ha sido enviado.` | The CFDI was sent to the email. |
| `El ticket fue facturado previamente` | Already invoiced. It stops before the second step, so retrying is harmless. |

## Limits

- **Deadline:** unknown. The official manual (`ManualUsuarioAnt.pdf`, linked from the portal)
  gives no waiting time and no deadline, and the "24 hours" and "60 days" found on blogs are
  unconfirmed.
- **Deferred invoice:** the manual also describes one ("recibir la factura en tu correo una vez que
  tus datos sean validados"), which needs a registered account.

## How the CFDI arrives

By email, sent after issuing the invoice. "Reimprime tu factura" sends it again or downloads it
later: it asks for the same four fields of the receipt and answers `Su factura ha sido encontrada,
puede descargar o bien solicitar que se envié a su cuenta de correo`.
