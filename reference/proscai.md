# Proscai (Promoda, Mumuso, Aldo Conti and other stores)

- **Issuer:** each store's company, e.g. 27 Micras Internacional (Aldo Conti) or Mumugrand
  (Mumuso)
- **RFC:** each store's
- **Portal:** `https://cw.pos.mx/factura/<tienda>`, e.g. `cw.pos.mx/factura/mumuso`
- **Script:**
  [`proscai.py`](../scripts/proscai.py)

Proscai is a point-of-sale system for stores. Its receipts end with "Obtenga su factura con su
celular", a QR, the portal's address and a "Clave para facturar". Some receipts print the store's
own site instead, e.g. `aldoconti.com/facturacion`, which blocks IPs outside Mexico. Use
`cw.pos.mx/factura/<tienda>` for those, which doesn't.

## Stores

The portal doesn't list its stores. These are the ones known to have an address on it:

| Store | Address |
|---|---|
| Aldo Conti | [`aldoconti`](https://cw.pos.mx/factura/aldoconti) |
| Ay Güey | [`ayguey`](https://cw.pos.mx/factura/ayguey) |
| Bari Swimwear | [`bariswimwear`](https://cw.pos.mx/factura/bariswimwear) |
| Hang Ten | [`hangten`](https://cw.pos.mx/factura/hangten) |
| Juguetibici | [`juguetibici`](https://cw.pos.mx/factura/juguetibici) |
| Karele | [`karele`](https://cw.pos.mx/factura/karele) |
| Liz Minelli | [`lizminelli`](https://cw.pos.mx/factura/lizminelli) |
| Mumuso | [`mumuso`](https://cw.pos.mx/factura/mumuso) |
| Promoda | [`multibrand`](https://cw.pos.mx/factura/multibrand) |
| Quarry Jeans | [`quarry`](https://cw.pos.mx/factura/quarry) |
| Toxic | [`toxic`](https://cw.pos.mx/factura/toxic) |
| Trender | [`trender`](https://cw.pos.mx/factura/trender) |
| Tropic | [`tropic`](https://cw.pos.mx/factura/tropic) |

An address the portal doesn't know answers "Lo sentimos! La página que estabas buscando no fue
encontrada."

The key finds the receipt from any store's address, so `--tienda` only changes the logo and the
evidence folder. Still, pass the store of the receipt.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| Clave para facturar | `Clave para facturar`, 12 consonants in groups of three, e.g. `BCD FGH JKL MNP` |

## Flow

1. The first page asks for the key. The portal takes it with or without spaces.
2. The receiver's form asks for RFC, last names, first names, postal code, regime, Uso CFDI and
   email. The regime and the use are searchable lists, and the uses load after the regime.
   A "Subir" button can fill the form from the Constancia de Situación Fiscal; the script doesn't
   use it.
3. `Enviar` requests the invoice, with no preview. The form says the data can't be changed after
   that.

## Known answers

| Message | Meaning |
|---|---|
| `¡Solicitud realizada! Tu solicitud ha sido registrada. Recibirás tu factura por email en un máximo de 24 horas.` | Requested. |
| `Clave inválida. La clave para facturar es incorrecta, por favor revísala.` | Wrong key, in a dialog. A key with one letter changed gets it too. |
| `La clave para facturar debe constar exclusivamente de consonantes.` | The key has a vowel; check the reading. The script checks it before opening the portal. |
| `¡Tu factura está en proceso!` | Already requested, not issued yet. |
| `Descarga tus comprobantes`, with XML and PDF links | Already issued. This page is how to download the files again. |

## Limits

- **Deadline:** 30 days after the purchase, as the receipt says.
- **Store hours:** the FAQ says the invoices are only issued while the store is open; a request
  made after closing is issued when it opens.

## How the CFDI arrives

By email from cfdi@pos.mx, with the subject "Factura Electrónica" and the XML and the PDF attached,
within a minute. The XML comes as `text/plain`. Its total can be a few cents more than the
receipt's, because the CFDI computes the VAT apart (FAQ 30).
