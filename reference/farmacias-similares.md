# Farmacias Similares

- **Issuer:** the owner of each franchise, a person or a company with its own RFC, printed at the top
  of the receipt (not Farmacias de Similares, S.A. de C.V.)
- **Portal:** SimiFactura,
  https://facturacion.gpupm.com/simifactura/portal
- **Script:** `farmacias_similares.py`

The page that farmaciasdesimilares.com links as "Facturación" explains the invoicing of online
orders, which goes by email to facturaelectronica@fsimilares.com, and links SimiFactura for
purchases in a store. SimiFactura asks only for the "Referencia de Facturación" and sends each
franchise to its own invoicing provider, on another site. The script knows the providers in its
`providers` table, Soltec (facturasoltec.com) so far, and stops on any other.

The "Proveedores de bienes y servicios" link (facturacfd.farmaciasdesimilares.com.mx) is the
portal where suppliers upload their invoices; it isn't for customers.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Referencia para Facturación (SimiFactura), Sucursal (Soltec) | "Referencia de Facturación FRANQUICIA", in large print above the barcode, e.g. `FH0123`. The same code follows "Sucursal:" at the top. |
| Código barras | The 13 digits under the barcode at the end, as printed, without adding digits |
| Total | "Total M.N.", with cents |
| Forma de pago | The SAT code of "Pagos >>", e.g. `04` for "Tarjeta Crédito" |

The receipt also has "Ticket:" with a long identifier in hexadecimal, which the portal doesn't use.

## Flow

1. SimiFactura: the reference and "Continuar". A franchise's reference opens a confirmation
   ("Usted será direccionado al portal de servicios de facturación correspondiente"), whose
   "Aceptar" opens the provider's portal.
2. Soltec, receipt: Sucursal, Código barras and Total. Each field stays read-only until the one
   before it is checked, and the checks run as each field is typed and when it loses the focus,
   so the script types them one character at a time. A green message under each field confirms it
   ("Sucursal valida", "Campo CodigoBarras correcto", "Campo Total valido"). A receipt already
   invoiced goes to its status page right after the barcode.
3. Soltec, receiver: RFC, Razón social, Código postal, then Régimen fiscal, whose options load after
   the postal code, Uso CFDI, whose options the server sends for the regime chosen, Forma de pago,
   and the email twice, the second time to confirm it. The "Persona física" and "Persona moral"
   links above them are only guides to the Constancia de Situación Fiscal; they open a modal that
   covers the page.
4. "Procesar factura v4.0" only opens a summary with every value and "Editar datos" and "Procesar
   factura" buttons, so the dry run stops there and prints it. "Procesar factura" in the summary
   issues the invoice.

## Known answers

| Message | Meaning |
|---|---|
| `Ticket procesado correctamente Se ha enviado la factura a su correo electrónico` | Issued. The status page offers the XML and the PDF. It shows again for a receipt already invoiced, right after its barcode. |
| `Estamos procesando su factura Su factura está en proceso de generación, la recibirá por mail en un maximo de 48 horas` | The portal didn't find the receipt, for example a wrong barcode. It says that the reason arrives by email, with a link to fix the data. |

## Limits

- **Deadline:** 30 days after the purchase ("El ticket no debe de ser mayor a 30 días", in the
  summary).
- The receipt asks to request the invoice in the store at the moment of the purchase, but the
  portal invoiced a receipt of the same day.

## How the CFDI arrives

By email to the address given, according to the portal. The status page of the receipt (enter the
branch and the barcode again) also has links to download the XML and the PDF.
