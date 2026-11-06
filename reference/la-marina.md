# La Marina

- **Issuer:** BODESA SAPI DE CV
- **RFC:** `BOD9809059Z6`
- **Portal:** https://servicios.lamarina.com.mx/Facturacion
- **Script:**
  [`la_marina.py`](../scripts/la_marina.py)

La Marina is a department store chain of western Mexico (Colima, Jalisco, Michoacán, Guanajuato).
The portal is linked as "Facturación" in the footer of www.lamarina.com.mx. It also invoices online
and marketplace purchases, which the script doesn't cover.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Tienda | "Tienda", such as "LA MARINA ZAPOTLAN". The portal lists it with that name, ignoring case and accents. |
| Terminal and Transacción | "Folio", the terminal and the transaction separated by a dash: 101-2345 is terminal 101, transaction 2345. |
| Fecha | the date at the end of the receipt, after "GRACIAS POR SU COMPRA", as dd-mm-yyyy. |
| Forma de pago | "FORMA DE PAGO" and the card section below it: "TARJETA DE CRÉDITO" is 04. "BANCOS" alone doesn't say which kind of card. |

## Flow

1. Pick "Tienda departamental" and "Persona física". The radio buttons are hidden behind cards, so
   the script clicks their text.
2. The form has three sections that open one after the other with "Continuar", which checks the
   section's fields: personal data, address and the receipt's data.
3. Each catalog (regime, Uso CFDI, state, municipality, locality, postal code, colony, store) is a
   hidden select behind a search field. The script chooses the option in the select, which
   loads the next catalog of the address and updates the search field.
4. The portal asks for the mobile phone and the full address, which go in the receiver's
   optional fields of the configuration (see `config.example.toml`). The locality is the city
   as the SAT's catalog names it, which can differ from the municipality ("Ciudad Guzmán" in
   Zapotlán el Grande); when it doesn't match, the script prints the options.
5. "GENERAR FACTURA" opens a summary with every field. The dry run stops there. "Generar" in the
   summary issues the invoice.

The portal doesn't look the receipt up before "Generar", so a wrong terminal, transaction or date
only shows up after it. That's why the dry run can't tell whether the receipt exists.

## Known answers

| Message | Meaning |
|---|---|
| `Factura Enviada UUID: ... Folio: ... serie: ...` | Issued. The CFDI goes by email to the address of the form. |
| `La transaccion ya ha sido facturada anteriormente. (clave 110)` | Already invoiced. |
| `La transaccion esta cancelada, no es posible facturar. (clave 105)` | The answer to a made-up terminal and transaction, so it may also mean the receipt wasn't found. |
| `Fuera del periodo de facturación` | The date is past the deadline; the portal shows it when the date is entered. |

## Limits

- **Deadline:** the month of the purchase. A purchase on the last day of the month has 3 more
  business days. The receipt says "the same day", but the portal follows the month rule (it says
  so in its notice "Fuera del periodo de facturación").
- **Not invoiced:** online purchases can be invoiced from the day after the purchase.

## How the CFDI arrives

By email from `invoice@solucionfactible.com` ("BODESA SAPI DE CV"), an invoicing provider, with the
XML and the PDF attached, about a minute after "Generar".
