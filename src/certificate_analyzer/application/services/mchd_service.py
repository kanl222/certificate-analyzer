from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException

from certificate_analyzer.infrastructure.certificates.scanner import scan_files
from certificate_analyzer.infrastructure.mchd.xml_parser import MchdXmlParser


class MchdService:
    def __init__(self):
        self.errors = {}

    def scan(self, folder):
        self.errors = {}
        documents = []
        for path in scan_files(folder, (".xml",)):
            try:
                documents.append(MchdXmlParser().parse(path))
            except (ValueError, OSError, ParseError, DefusedXmlException) as exc:
                self.errors[path] = str(exc)
        return documents
