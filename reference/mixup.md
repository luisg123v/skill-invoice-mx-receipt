# iShop / Mixup

- **Issuer:** Promotora Musical
- **RFC:** `PMU940317114`
- **Portal:** https://facturaelectronica.mixup.com
- **Script:** none yet

The portal is linked as "Facturación" from ishopmixup.com. It blocks IPs outside Mexico: from
abroad it answered 503 ("Backend unavailable") and later a "Client Challenge" page. There is no
script yet, but the steps below worked by hand.

## Where the data is on the receipt

| Portal field | On the receipt |
|---|---|
| No. de Ticket | `No. de Ticket`, 18 digits in large print below the barcode (the same number as the barcode). The receipt also prints transaction, terminal and store, which the form doesn't need |

## Flow

1. `Continuar` (`#btn-go-invoice`), then click the labels of "Facturar Compra"
   (`label[for=action-intake]`) and "Tengo RFC" (`label[for=option-local]`).
2. Type the RFC in `#txt-rfc` and press Enter. Clicking "Buscar" does nothing; the form only
   advances through its validation, which Enter starts.
3. Datos de factura: `#txt-name`, `#txt-email`, `#txt-codigo-postal`, `#RegimenFiscalDll`,
   `#txt-noTicket` (the receipt number), `#txt-amount` and `#txt-cfdi` (Uso CFDI).
4. Verification number: `#image-captcha` shows a plain 5-digit number on a red background, which
   the form calls "folio". Take a screenshot of that element, read the number and type it in
   `#txt-captcha`.
5. `#btn-generate-invoice` stamps it: "Su factura con folio: <folio> fué generada exitosamente",
   with XML and PDF download links.

## Limits

- **Deadline:** the month of the purchase, as the portal says, although the receipt says 30 days.

## How the CFDI arrives

Unknown yet; the result page has the XML and the PDF.
