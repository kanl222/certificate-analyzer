import re
from pathlib import Path
from certificate_analyzer.infrastructure.phonebook.txt_loader import TxtPhonebookLoader


def normalize(text):
    return " ".join(re.sub(r"[^\w\s]", "", text.casefold().replace("ё", "е")).split())


class PhoneBook:
    def __init__(self):
        self.employees = []
        self.data = []

    def load(self, path):
        if Path(path).suffix.lower() == ".docx":
            from certificate_analyzer.infrastructure.phonebook.docx_loader import (
                DocxPhonebookLoader,
            )

            loader = DocxPhonebookLoader()
        else:
            loader = TxtPhonebookLoader()
        employees = loader.load(path)
        self.employees = employees
        self.data = [
            {
                "name": e.full_name,
                "department": e.department,
                "cabinet": e.office,
                "phone": ", ".join(e.phones) or "—",
            }
            for e in employees
        ]
        return True

    load_from_docx = load
    load_from_txt = load

    def find_phone(self, cert_info):
        office = normalize(cert_info.get("office_number", ""))
        name = normalize(cert_info.get("subject_cn", ""))
        department = normalize(cert_info.get("department", ""))
        for predicate in (
            lambda e: office and normalize(e.office or "") == office,
            lambda e: name and normalize(e.full_name) == name,
            lambda e: department and normalize(e.department or "") == department,
        ):
            phones = {
                p
                for e in self.employees
                if predicate(e)
                for p in e.phones
                if re.search(r"\d", p)
                and not any(v in p.lower() for v in ("@", "http", "mail"))
            }
            if phones:
                return ", ".join(sorted(phones))
        return "—"

    get_phone_for_cert = find_phone
