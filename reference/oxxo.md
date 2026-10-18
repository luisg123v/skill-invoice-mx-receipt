# OXXO

- **Issuer:** Cadena Comercial OXXO
- **RFC:** `CCO8605231N4`
- **Portal:** https://www4.oxxo.com/facturacionElectronica-web/views/layout/inicio.do
- **Script:**
  [`oxxo.py`](../scripts/oxxo.py) (first step only)

The script only automates the first step (receipt validation), because the second step hasn't
been reached by script yet. The first time a receipt validates, explore the second step as "A new
portal" in SKILL.md says, then extend the script and this file.

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

## Flow, first step

1. An informative dialog about the ID opens on load; the script closes it.
2. The date field is a read-only datepicker. The script opens it, moves back to the right month and
   clicks the day, then checks the field. An empty date makes the portal answer "ejercicio fiscal
   diferente", which is misleading, so the script stops instead of submitting.
3. `Validar Ticket` answers with a message that fades out after a few seconds, so the script
   checks for it repeatedly. `#form:continuar` becomes enabled when the receipt is valid.

## Known answers

| Message | Meaning |
|---|---|
| `La búsqueda del Folio N, no tuvo éxito, favor de volver a intentar.` | The sale isn't in OXXO's system yet, which can take more than a day; retry later. |
| `El campo ID de Venta es inválido, verifícalo en tu ticket de compra.` | The ID has the wrong shape. |
| `No se permite facturar tickets que fueron emitidos en un ejercicio fiscal diferente.` | Also the answer to an empty date; check the date field first. |
| `El ticket fue facturado previamente` | Already invoiced. It stops before the second step, so retrying is harmless. |

## Limits

- **Deadline:** unknown. The official manual (`ManualUsuarioAnt.pdf`, linked from the portal)
  gives no waiting time and no deadline, and the "24 hours" and "60 days" found on blogs are
  unconfirmed.
- **Deferred invoice:** the manual also describes one ("recibir la factura en tu correo una vez que
  tus datos sean validados"), which needs a registered account.

## How the CFDI arrives

Unknown yet whether OXXO attaches the XML to the email. Until it is known, send it to
`email_links`, and write down here what arrives. "Reimprimir" on the portal also gives the files.
