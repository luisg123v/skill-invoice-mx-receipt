"""Configuration of the scripts: the receiver, where the CFDI goes, and the optional proxy.

They come from a TOML file, `~/.config/invoice-mx-receipt/config.toml` by default (see
`config.example.toml`), or the file the INVOICE_MX_RECEIPT_CONFIG environment variable points to.
"""

import datetime
import os
import re
import socket
import subprocess
from dataclasses import dataclass, field, fields
from pathlib import Path
from urllib.parse import urlsplit

try:
    import tomllib
except ModuleNotFoundError:
    # Python 3.10 doesn't have tomllib; tomli is the same parser as a separate package.
    import tomli as tomllib

DEFAULT_CONFIG = Path("~/.config/invoice-mx-receipt/config.toml")
DEFAULT_EVIDENCE = Path("~/.local/share/invoice-mx-receipt")

REGIMES = {
    "601": "General de Ley Personas Morales",
    "603": "Personas Morales con Fines no Lucrativos",
    "605": "Sueldos y Salarios e Ingresos Asimilados a Salarios",
    "606": "Arrendamiento",
    "607": "Régimen de Enajenación o Adquisición de Bienes",
    "608": "Demás ingresos",
    "610": "Residentes en el Extranjero sin Establecimiento Permanente en México",
    "611": "Ingresos por Dividendos (socios y accionistas)",
    "612": "Personas Físicas con Actividades Empresariales y Profesionales",
    "614": "Ingresos por intereses",
    "615": "Régimen de los ingresos por obtención de premios",
    "616": "Sin obligaciones fiscales",
    "620": "Sociedades Cooperativas de Producción que optan por diferir sus ingresos",
    "621": "Incorporación Fiscal",
    "622": "Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras",
    "623": "Opcional para Grupos de Sociedades",
    "624": "Coordinados",
    "625": "Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas",
    "626": "Régimen Simplificado de Confianza",
}


@dataclass(frozen=True)
class CfdiUsage:
    """An entry of the SAT's c_UsoCFDI catalog."""

    description: str
    # The receiver regimes that admit it.
    regimes: tuple


EXPENSE_REGIMES = ("601", "603", "606", "612", "620", "621", "622", "623", "624", "625", "626")
DEDUCTION_REGIMES = ("605", "606", "607", "608", "611", "612", "614", "615", "625")
CFDI_USAGES = {
    "G01": CfdiUsage("Adquisición de mercancías", EXPENSE_REGIMES),
    "G02": CfdiUsage("Devoluciones, descuentos o bonificaciones", EXPENSE_REGIMES + ("616",)),
    "G03": CfdiUsage("Gastos en general", EXPENSE_REGIMES),
    "I01": CfdiUsage("Construcciones", EXPENSE_REGIMES),
    "I02": CfdiUsage("Mobiliario y equipo de oficina por inversiones", EXPENSE_REGIMES),
    "I03": CfdiUsage("Equipo de transporte", EXPENSE_REGIMES),
    "I04": CfdiUsage("Equipo de cómputo y accesorios", EXPENSE_REGIMES),
    "I05": CfdiUsage("Dados, troqueles, moldes, matrices y herramental", EXPENSE_REGIMES),
    "I06": CfdiUsage("Comunicaciones telefónicas", EXPENSE_REGIMES),
    "I07": CfdiUsage("Comunicaciones satelitales", EXPENSE_REGIMES),
    "I08": CfdiUsage("Otra maquinaria y equipo", EXPENSE_REGIMES),
    "D01": CfdiUsage("Honorarios médicos, dentales y gastos hospitalarios", DEDUCTION_REGIMES),
    "D02": CfdiUsage("Gastos médicos por incapacidad o discapacidad", DEDUCTION_REGIMES),
    "D03": CfdiUsage("Gastos funerales", DEDUCTION_REGIMES),
    "D04": CfdiUsage("Donativos", DEDUCTION_REGIMES),
    "D05": CfdiUsage(
        "Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)", DEDUCTION_REGIMES
    ),
    "D06": CfdiUsage("Aportaciones voluntarias al SAR", DEDUCTION_REGIMES),
    "D07": CfdiUsage("Primas por seguros de gastos médicos", DEDUCTION_REGIMES),
    "D08": CfdiUsage("Gastos de transportación escolar obligatoria", DEDUCTION_REGIMES),
    "D09": CfdiUsage(
        "Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones", DEDUCTION_REGIMES
    ),
    "D10": CfdiUsage("Pagos por servicios educativos (colegiaturas)", DEDUCTION_REGIMES),
    "S01": CfdiUsage("Sin efectos fiscales", tuple(REGIMES)),
}


@dataclass
class Receiver:
    rfc: str
    first_names: str
    last_names: str
    postal_code: str
    # Every regime in the Constancia de Situación Fiscal, the preferred one first.
    regimes: list

    @property
    def name(self):
        """Return the full name, as registered with the SAT."""
        return "%s %s" % (self.first_names, self.last_names)

    def regime_for(self, usage):
        """Return the first of the receiver's regimes that the Uso CFDI admits."""
        if usage not in CFDI_USAGES:
            raise SystemExit("ABORT: unknown Uso CFDI %s" % usage)
        for regime_code in self.regimes:
            if regime_code in CFDI_USAGES[usage].regimes:
                return regime_code
        raise SystemExit(
            "ABORT: Uso CFDI %s admits none of the receiver's regimes (%s)" % (usage, ", ".join(self.regimes))
        )


@dataclass
class Config:
    receiver: Receiver
    email: str
    # Some portals email links instead of attaching the XML; they send to this address, if set.
    email_links: str = ""
    evidence_dir: Path = DEFAULT_EVIDENCE
    proxy: str = ""
    proxy_command: list = field(default_factory=list)
    csf: Path | None = None
    sender: str = ""
    signature: list = field(default_factory=list)
    # Commands that read the email on stdin: one sends it, the other keeps a copy.
    sendmail: list = field(default_factory=list)
    sent_copy_command: list = field(default_factory=list)

    @classmethod
    def load(cls, path=None):
        """Read the configuration file, stopping when it lacks a required value."""
        path = Path(path or os.environ.get("INVOICE_MX_RECEIPT_CONFIG") or DEFAULT_CONFIG).expanduser()
        if not path.exists():
            raise SystemExit("ABORT: no configuration at %s; copy config.example.toml there and fill it" % path)
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
        receiver = data.get("receiver", {})
        missing = ["receiver." + key for key in (item.name for item in fields(Receiver)) if not receiver.get(key)]
        if not data.get("email"):
            missing.append("email")
        if missing:
            raise SystemExit("ABORT: %s lacks %s" % (path, ", ".join(missing)))
        unknown = [regime_code for regime_code in receiver["regimes"] if regime_code not in REGIMES]
        if unknown:
            raise SystemExit("ABORT: %s has unknown regimes: %s" % (path, ", ".join(unknown)))
        request = data.get("request", {})
        return cls(
            receiver=Receiver(**receiver),
            email=data["email"],
            email_links=data.get("email_links", ""),
            evidence_dir=Path(data.get("evidence_dir", DEFAULT_EVIDENCE)).expanduser(),
            proxy=data.get("proxy", ""),
            proxy_command=data.get("proxy_command", []),
            csf=Path(data["csf"]).expanduser() if data.get("csf") else None,
            sender=request.get("sender", ""),
            signature=request.get("signature", []),
            sendmail=request.get("sendmail", []),
            sent_copy_command=request.get("sent_copy_command", []),
        )

    def receipt_folder(self, portal, ticket):
        """Return (and create) the folder that keeps the screenshots and files of one receipt."""
        stamp = datetime.date.today().isoformat()
        path = self.evidence_dir / ("%s-%s-%s" % (stamp, portal, re.sub(r"\W+", "_", ticket)))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def proxy_listening(self):
        address = urlsplit(self.proxy)
        with socket.socket() as sock:
            sock.settimeout(2)
            return not sock.connect_ex((address.hostname, address.port))

    def open_proxy(self):
        """Run `proxy_command` when nothing listens on the proxy's port.

        The proxy stays open for the next receipts.
        """
        if self.proxy_listening():
            return
        if not self.proxy_command:
            raise SystemExit("ABORT: nothing listens on the proxy %s and there is no proxy_command" % self.proxy)
        subprocess.run(self.proxy_command, check=False, timeout=30)
        if not self.proxy_listening():
            raise SystemExit("ABORT: %r did not open the proxy %s" % (" ".join(self.proxy_command), self.proxy))
