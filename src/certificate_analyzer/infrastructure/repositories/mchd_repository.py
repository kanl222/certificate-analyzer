from typing import List, Optional
from sqlalchemy.orm import Session
from certificate_analyzer.infrastructure.database.models import MchdModel
from certificate_analyzer.domain.models.mchd import MchdDocument
from certificate_analyzer.domain.enums.mchd_status import MchdStatus

class MchdRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, mchd: MchdDocument) -> None:
        model = self.session.query(MchdModel).filter_by(unified_number=mchd.unified_number).first()
        
        if not model:
            model = MchdModel(unified_number=mchd.unified_number)
            self.session.add(model)

        model.internal_number = mchd.internal_number
        model.principal_inn = mchd.principal_inn
        model.principal_name = mchd.principal_name
        model.representative_inn = mchd.representative_inn
        model.representative_fio = mchd.representative_fio
        model.representative_snils = mchd.representative_snils
        model.valid_from = mchd.valid_from
        model.valid_to = mchd.valid_to
        model.status = mchd.status.name
        model.authority_codes = ",".join(mchd.authority_codes) if mchd.authority_codes else None

        self.session.commit()

    def get_all(self) -> List[MchdDocument]:
        models = self.session.query(MchdModel).all()
        return [self._to_domain(model) for model in models]

    def _to_domain(self, model: MchdModel) -> MchdDocument:
        return MchdDocument(
            unified_number=model.unified_number,
            internal_number=model.internal_number,
            principal_inn=model.principal_inn,
            principal_name=model.principal_name,
            representative_inn=model.representative_inn,
            representative_fio=model.representative_fio,
            representative_snils=model.representative_snils,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            status=MchdStatus[model.status],
            authority_codes=model.authority_codes.split(",") if model.authority_codes else []
        )
