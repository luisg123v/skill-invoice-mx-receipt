# /// script
# requires-python = ">=3.10"
# dependencies = ["tomli; python_version < '3.11'"]
# ///
"""Ask a store with no portal for the invoice, by email or WhatsApp.

Without --send it prints the email and saves it as .eml in the receipt's evidence folder; with
--send it also sends it with the `sendmail` command of the configuration. With --whatsapp instead
of --to, it prints a short message and a wa.me link that opens the chat with it filled in.

Usage:
    request_invoice.py --to tienda@example.com --fecha 2026-10-23 --importe 82.00 --uso S01 \
        --image receipt.jpg [--ref 12345] [--field "Folio=123456"] [--csf] [--send]
    request_invoice.py --whatsapp 3312345678 --fecha 2026-10-23 --importe 82.00 --uso S01
"""

import argparse
import mimetypes
import re
import subprocess
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape
from pathlib import Path
from urllib.parse import quote

from config import CFDI_USAGES, REGIMES, Config

EMAIL_GREETING = "Buenos días:"
EMAIL_REQUEST = "¿Me pueden apoyar con la facturación del ticket adjunto?"
EMAIL_CLOSING = "Quedo en espera."
CHAT_REQUEST = "Hola, ¿me pueden apoyar con la facturación de este ticket?"


def receipt_data(args):
    data = [("Referencia", args.ref)] if args.ref else []
    data += [("Fecha", args.fecha), ("Importe", args.importe)]
    for item in args.field:
        label, _sep, value = item.partition("=")
        data.append((label.strip(), value.strip()))
    return data


def billing_data(config, usage):
    receiver = config.receiver
    regime = receiver.regime_for(usage)
    return [
        ("Nombre", receiver.name),
        ("RFC", receiver.rfc),
        ("CP", receiver.postal_code),
        ("Régimen fiscal", "%s - %s" % (regime, REGIMES[regime])),
        ("Uso CFDI", "%s - %s" % (usage, CFDI_USAGES[usage].description)),
        ("Correo", config.email),
    ]


def chat_message(receipt, billing):
    """Return a short chat message: the request, then the data. The photo goes with it by hand."""
    lines = [CHAT_REQUEST, "", "Datos del ticket:"]
    lines += ["- %s: %s" % item for item in receipt]
    lines += ["", "Datos para la factura:"]
    lines += ["- %s: %s" % item for item in billing]
    return "\n".join(lines)


def whatsapp_link(number, message):
    """Return the wa.me link for a Mexican number, which needs the country code 52."""
    digits = re.sub(r"\D", "", number)
    if not digits.startswith("52") or len(digits) != 12:
        digits = "52" + digits[-10:]
    return "https://wa.me/%s?text=%s" % (digits, quote(message))


def email_text(receipt, billing, signature, intro=None):
    """Return the plain-text part, for mail clients that don't show HTML."""
    lines = [EMAIL_GREETING, ""] + ([intro, ""] if intro else []) + [EMAIL_REQUEST, "", "Datos del ticket:"]
    lines += ["- %s: %s" % item for item in receipt]
    lines += ["", "Datos de facturación:"]
    lines += ["- %s: %s" % item for item in billing]
    lines += ["", EMAIL_CLOSING]
    if signature:
        lines += ["", "--"] + signature
    return "\n".join(lines) + "\n"


def html_list(pairs):
    return "<ul>%s</ul>" % "".join("<li>%s: %s</li>" % (escape(key), escape(value)) for key, value in pairs)


def email_html(receipt, billing, signature, intro=None):
    parts = ["<html><body>", "<p>%s</p>" % escape(EMAIL_GREETING)]
    if intro:
        parts += ["<p>%s</p>" % escape(paragraph).replace("\n", "<br>") for paragraph in intro.split("\n\n")]
    parts += [
        "<p>%s</p>" % escape(EMAIL_REQUEST),
        "<p>Datos del ticket:</p>%s" % html_list(receipt),
        "<p>Datos de facturación:</p>%s" % html_list(billing),
        "<p>%s</p>" % escape(EMAIL_CLOSING),
    ]
    if signature:
        parts.append("<p>--<br>%s</p>" % "<br>".join(escape(line) for line in signature))
    parts.append("</body></html>")
    return "".join(parts)


def build_email(config, args, receipt, billing):
    msg = EmailMessage()
    msg["From"] = config.sender
    msg["To"] = args.to
    msg["Subject"] = "Facturación de consumo %s" % ("#%s" % args.ref if args.ref else "del día %s" % args.fecha)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=config.sender.rpartition("@")[2].strip("> ") or None)
    msg.set_content(email_text(receipt, billing, config.signature, args.intro))
    msg.add_alternative(email_html(receipt, billing, config.signature, args.intro), subtype="html")
    for path in args.image:
        maintype, subtype = (mimetypes.guess_type(path.name)[0] or "application/octet-stream").split("/", 1)
        msg.add_attachment(
            path.read_bytes(), maintype=maintype, subtype=subtype, filename="ticket_%s%s" % (args.fecha, path.suffix)
        )
    if args.csf:
        if not config.csf:
            raise SystemExit("ABORT: --csf needs `csf` in the configuration")
        msg.add_attachment(
            config.csf.read_bytes(),
            maintype="application",
            subtype="pdf",
            filename="Constancia_de_situacion_fiscal.pdf",
        )
    return msg


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--to", help="store email")
    target.add_argument("--whatsapp", help="store WhatsApp number")
    parser.add_argument("--fecha", required=True, help="yyyy-mm-dd")
    parser.add_argument("--importe", required=True)
    parser.add_argument("--uso", required=True, choices=CFDI_USAGES, metavar="USO", help="Uso CFDI, e.g. G03")
    parser.add_argument("--image", type=Path, action="append", default=[], help="photo of the receipt (email only)")
    parser.add_argument("--ref", help="receipt number, only when certain")
    parser.add_argument("--intro", help="paragraph before the request, e.g. that the portal failed")
    parser.add_argument("--field", action="append", default=[], help='other receipt field, "Label=value"')
    parser.add_argument("--csf", action="store_true", help="attach the Constancia de Situación Fiscal")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--config", type=Path, help="configuration file")
    args = parser.parse_args()
    config = Config.load(args.config)
    receipt = receipt_data(args)
    billing = billing_data(config, args.uso)

    if args.whatsapp:
        message = chat_message(receipt, billing)
        print(message)
        print()
        print(whatsapp_link(args.whatsapp, message))
        return 0
    if not args.image:
        parser.error("--image is required for an email")
    if not config.sender:
        raise SystemExit("ABORT: an email needs request.sender in the configuration")

    msg = build_email(config, args, receipt, billing)
    eml = config.receipt_folder("request", args.ref or args.fecha) / "request.eml"
    eml.write_bytes(bytes(msg))
    print("To: %s\nSubject: %s\n" % (msg["To"], msg["Subject"]))
    print(msg.get_body(("plain",)).get_content())
    print("attachments: %s" % ", ".join(part.get_filename() for part in msg.iter_attachments()))
    print("saved: %s" % eml)
    if not args.send:
        print("dry run: not sent")
        return 0
    if not config.sendmail:
        raise SystemExit("ABORT: sending needs request.sendmail in the configuration; send %s by hand" % eml)
    subprocess.run(config.sendmail, input=bytes(msg), check=True)
    print("SENT, Message-ID %s" % msg["Message-ID"])
    if config.sent_copy_command:
        # sendmail keeps no copy, unlike a mail client.
        subprocess.run(config.sent_copy_command, input=bytes(msg), check=True)
        print("copy saved with %s" % " ".join(config.sent_copy_command))
    return 0


if __name__ == "__main__":
    sys.exit(main())
