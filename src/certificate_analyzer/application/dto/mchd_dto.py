from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from certificate_analyzer.domain.enums.mchd_status import MchdStatus

@dataclass
class MchdDTO:
    file_name: str
    file_type: str
    doc_number: str
    issue_date: str
    expiry_date: str
    full_name: str
    inn: str
    snils: str
    authority_codes: List[str]
    authority_names: List[str]
    issuer_org_name: str
    issuer_org_inn: str
    status: str
    color: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def __getitem__(self, item):
        if hasattr(self, item) and item != 'details':
            return getattr(self, item)
        if item in self.details:
            return self.details[item]
        return "Не найдено"
        
    def get(self, item, default=None):
        if hasattr(self, item) and item != 'details':
            return getattr(self, item)
        return self.details.get(item, default)
        
    def keys(self):
        return [k for k in self.__annotations__.keys() if k != 'details'] + list(self.details.keys())

def mchd_to_dict(model):
    days = (model.valid_to.date() - datetime.now().date()).days
    status, color = {
        MchdStatus.EXPIRED: ("Просрочен", "#e57373"),
        MchdStatus.EXPIRING_SOON: (f"Истекает ({days} дн.)", "#ffd54f"),
        MchdStatus.ACTIVE: ("Действует", "#9b59b6"),
        MchdStatus.REVOKED: ("Отозвана", "#e57373"),
    }[model.status]
    
    raw_details = getattr(model, "details", None) or {}
    details_dict = {k: (v or "Не найдено") for k, v in raw_details.items()}
    
    return MchdDTO(
        file_name=str(getattr(model, "source_path", "—")),
        file_type="МЧД",
        doc_number=model.unified_number,
        issue_date=model.valid_from.strftime("%d.%m.%Y"),
        expiry_date=model.valid_to.strftime("%d.%m.%Y"),
        full_name=model.representative_fio or "Не найдено",
        inn=model.representative_inn or "Не найден",
        snils=model.representative_snils or "Не найден",
        authority_codes=getattr(model, "authority_codes", []),
        authority_names=getattr(model, "authority_names", []),
        issuer_org_name=model.principal_name,
        issuer_org_inn=model.principal_inn,
        status=status,
        color=color,
        details=details_dict
    )
