# Soft Restaurant (many restaurants)

- **Issuer:** each restaurant, often the person who runs it rather than the restaurant's name
- **RFC:** each restaurant's
- **Portal:** `https://facturacion.softrestaurant.com/<slug>` or `https://admin.softrestaurant.com/<slug>`
- **Script:**
  [`soft_restaurant.py`](../scripts/soft_restaurant.py), for the first portal only

Soft Restaurant is a point-of-sale system for restaurants, and the receipt shows "SOFT RESTAURANT"
at the bottom. It has two invoicing portals, and the link on the receipt says which one the
restaurant uses:

- `https://mefacturo.com/<slug>` redirects to `facturacion.softrestaurant.com`, which the script
  covers. Most of this file is about it.
- `https://mefacturo.mx/<slug>` (`.mx`, not `.com`) redirects to `admin.softrestaurant.com`
  (Soft Restaurant V11), which has no script yet. See "The admin.softrestaurant.com portal".

The QR on the receipt opens the first portal with the receipt filled in:
`https://facturacion.softrestaurant.com/<slug>?Folio=<folio>&Reference=<código>`. The portal has an
invisible reCAPTCHA that doesn't block the script.

## Where the data is on the receipt

Near the QR, at the end of the receipt:

| Portal field | On the receipt |
|---|---|
| Folio | `FOLIO` |
| Código de facturación | `CODIGO FACT`, 14 letters and digits. When a photo is doubtful, the QR has the same values |
| (deadline) | `DIAS VIGENCIA` |

The QR is often cut off in photos, so ask for a photo of that end of the receipt if the code isn't
visible.

## Flow

1. The first page asks for folio, código de facturación and RFC, then `FACTURAR` opens
   `/Invoice/Ticket?saleId=...`. A wrong code stays on the first page.
2. A notice about CFDI 4.0 opens (`#acceptFeedback`).
3. For an RFC the restaurant doesn't know yet, a customer form opens: regime, name, email, postal
   code and Uso CFDI (the uses load after the regime). Its visible "Guardar" is a link
   (`a[onclick='enviarUserForm()']`); the two Guardar buttons in it are hidden.
4. For a known RFC the form doesn't open and the portal reuses the saved customer, including its
   Uso CFDI. That is why the script reads the receiver from the preview's XML tab and stops when
   RFC, Uso CFDI, postal code or regime differ. How to change a saved customer's Uso CFDI is not
   known yet.
5. `Siguiente` shows "Previsualizar factura" (PDF and XML tabs). The script also compares the
   XML's `Total` with `--total`.
6. `Facturar`, then `Aceptar` in "¿Estás seguro que deseas generar la factura?". Stamping shows
   "Facturando..." for more than 15 seconds.

## Known answers

| Message | Meaning |
|---|---|
| `Ya puedes descargar tu factura electrónica. Folio <folio>`, with PDF, XML and ENVIAR buttons | Already invoiced. This page is how to download the files again. |

## Known issues

- **One cent more than the receipt.** The system rounds the unit price before adding up the lines,
  but computes the VAT on the exact base. For instance, a receipt of 285.00 for 3 dishes of 95.00
  gets 3 × 81.90 = 245.70 plus the VAT of 245.69 (39.31), so the CFDI is 285.01. It shows in the
  preview, so the script stops when the totals differ.

## Limits

- **Deadline:** `DIAS VIGENCIA` on the receipt.

## How the CFDI arrives

By email from `no-reply@notifications.softrestaurant.com` ("Su factura ha sido generada con
éxito"), with the XML and the PDF attached.

## The admin.softrestaurant.com portal

These steps worked by hand:

1. `#FolioTicket`, `#CodigoUnicoTicket` and `#RFC`, then `#btn_facturar` opens
   `/Facturacion/Prefactura`.
2. Receiver: `#Prv_Cliente_RazonSocial`, `#Prv_Cliente_CodigoPostal`,
   `#Prv_Cliente_RegimenFiscal`, `#Prv_UsoCFDI` (RFC comes prefilled). "Agrupar por concepto"
   (`#Prv_EsAgrupado`) comes checked, which makes one line "CONSUMO DE ALIMENTOS Y BEBIDAS". It is
   a styled checkbox, so click its label. Unchecked, the CFDI lists every dish, and its total can
   match the receipt where the grouped one is a cent more. Leave it unchecked.
3. `#btn_previsualizar` shows the PDF preview on the same page; `#btn_confirmar` opens "Confirmar
   factura", which asks for recipients in a tag input (`#Correos_tag`: type and press Enter).
4. `#btn_timbrar` stamps it: "El comprobante se ha generado de forma exitosa. Se ha enviado un
   correo a ...", with a "Descargar archivos" link.
