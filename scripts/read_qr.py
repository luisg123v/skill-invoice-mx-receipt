# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow", "zxing-cpp"]
# ///
"""Print the content of every QR or barcode in a photo of a receipt.

Some receipts print a QR that opens the portal with the receipt's data already filled; passing
that URL avoids misreading the numbers.

Usage:
    read_qr.py photo.jpg
"""

import sys

import zxingcpp
from PIL import Image


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    found = zxingcpp.read_barcodes(Image.open(sys.argv[1]))
    for result in found:
        print(result.text)
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())
