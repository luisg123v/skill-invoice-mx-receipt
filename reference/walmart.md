# Walmart

- **Issuer:** Nueva Wal Mart de Mexico
- **RFC:** `NWM9709244W4`
- **Portal:** https://facturacion-clientes.walmart.com/
- **Script:**
  [`walmart.py`](../scripts/walmart.py)

`https://facturacion.walmartmexico.com.mx/` redirects to the portal.

## Where the data is on the receipt

Near the barcode, in two lines like these:

```
TDA#1234  OP#00000012  TE#001  TR#01234
TC#1234567890123456789012
```

The portal only asks for two of those numbers:

| Portal field | On the receipt |
|---|---|
| Número de ticket | `TC#`, 22 digits. Count them on an enlarged crop, because a digit is easy to drop |
| Número de transacción | `TR#`, 5 digits |

## Flow

1. A notice opens on load (`#popup_btn_accept`). The site is a single-page app: opening `/ticket`
   directly lands on the home page, so click "Obtener factura".
2. `/ticket`: RFC (`#membershipOrRFC`), postal code, TC (`#ticketNumber`) and TR
   (`#transactionNumber`), then `#form_btn_accept`.
3. `/address`: a notice says the fiscal data has to be entered on every request. RFC, postal code,
   state and municipality come prefilled; the address is optional. Fill Razón Social, email,
   Régimen Fiscal and then Uso Factura (its options load after the regime). The field ids have
   spaces and accents (`[id='Razón Social']`). `Aceptar` opens "¿Están correctos todos sus datos?"
   with Cerrar / Continuar.
4. `/payment`: Forma de Pago (Efectivo, Cheque nominativo, Transferencia, Tarjeta de crédito,
   Monedero electrónico, Vales de despensa, Tarjeta de débito). The receipt shows how it was paid;
   ask when it doesn't say whether a card is credit or debit.
5. `/invoiceSelection`: "Enviar a correo electrónico" comes selected with the email of the data
   step; `Facturar` stamps it and shows "FACTURA ENVIADA, CONSERVE SU TICKET PARA FUTURAS
   ACLARACIONES."

Only the last button stamps the invoice, so an interrupted run can be repeated from the start.

The CFDI's product descriptions are abbreviated as printed on the receipt (for instance,
"JITOMATE SAL" for "jitomate saladet"), and each line has the product's barcode as
NoIdentificacion.

## Limits

- **Deadline:** unknown.
- **Not invoiced:** the portal's form says "Vales electrónicos y de papel, certificados de regalo,
  gift card y cupones pre pagados no serán Facturados."

## How the CFDI arrives

By email from `facturaelectronica@wal-mart.com`, with the XML attached.
