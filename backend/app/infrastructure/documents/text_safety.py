"""Text that may go in a generated document."""

import re

# XML 1.0 has no place for these control characters (python-docx refuses them), and a PDF would
# draw them as empty boxes.
_ILLEGAL_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def xml_safe(text: str) -> str:
    return _ILLEGAL_XML.sub("", text)
