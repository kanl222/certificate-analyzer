from docx import Document
from certificate_analyzer.application.services.phonebook_service import PhoneBook


def test_txt_phone_lookup_and_email_filter(tmp_path):
    path = tmp_path / "phones.txt"
    path.write_text(
        "| Отдел кадров | Иванов Иван | 101 | 123-45 | email@test | 555 |\n",
        encoding="utf-8",
    )
    book = PhoneBook()
    book.load(path)
    assert book.find_phone({"subject_cn": "ИВАНОВ ИВАН"}) == "123-45, 555"
    assert book.find_phone({"office_number": "101"}) == "123-45, 555"
    assert book.find_phone({"subject_cn": "Другой"}) == "—"


def test_docx_lookup(tmp_path):
    path = tmp_path / "phones.docx"
    doc = Document()
    table = doc.add_table(rows=1, cols=4)
    for cell, text in zip(table.rows[0].cells, ["Кадры", "Иванов Иван", "101", "123"]):
        cell.text = text
    doc.save(path)
    book = PhoneBook()
    book.load(path)
    assert book.find_phone({"subject_cn": "Иванов Иван"}) == "123"
