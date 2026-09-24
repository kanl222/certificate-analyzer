from typing import List, Optional
from sqlalchemy.orm import Session
from certificate_analyzer.infrastructure.database.models import CertificateModel, EmployeeModel
from certificate_analyzer.domain.models.certificate import Certificate
from certificate_analyzer.domain.models.employee import Employee
from certificate_analyzer.domain.enums.certificate_status import CertificateStatus

class CertificateRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, cert: Certificate) -> None:
        cert_model = self.session.query(CertificateModel).filter_by(fingerprint_sha256=cert.fingerprint_sha256).first()
        
        if not cert_model:
            cert_model = CertificateModel(fingerprint_sha256=cert.fingerprint_sha256)
            self.session.add(cert_model)

        cert_model.subject = cert.subject
        cert_model.issuer = cert.issuer
        cert_model.valid_from = cert.valid_from
        cert_model.valid_to = cert.valid_to
        cert_model.status = cert.status.name
        cert_model.serial_number = cert.serial_number
        cert_model.has_private_key_link = cert.has_private_key_link
        cert_model.owner_name = cert.owner_name

        if cert.employee:
            employee_model = self.session.query(EmployeeModel).filter_by(full_name=cert.employee.full_name).first()
            if not employee_model:
                employee_model = EmployeeModel(
                    full_name=cert.employee.full_name,
                    department=cert.employee.department,
                    office=cert.employee.office,
                    phones=",".join(cert.employee.phones) if cert.employee.phones else None
                )
                self.session.add(employee_model)
            cert_model.employee = employee_model

        self.session.commit()

    def get_all(self) -> List[Certificate]:
        models = self.session.query(CertificateModel).all()
        return [self._to_domain(model) for model in models]

    def find_by_fingerprint(self, fingerprint: str) -> Optional[Certificate]:
        model = self.session.query(CertificateModel).filter_by(fingerprint_sha256=fingerprint).first()
        if model:
            return self._to_domain(model)
        return None

    def _to_domain(self, model: CertificateModel) -> Certificate:
        cert = Certificate(
            fingerprint_sha256=model.fingerprint_sha256,
            subject=model.subject,
            issuer=model.issuer,
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            status=CertificateStatus[model.status],
            serial_number=model.serial_number,
            has_private_key_link=model.has_private_key_link,
            owner_name=model.owner_name
        )
        
        if model.employee:
            phones = model.employee.phones.split(",") if model.employee.phones else []
            cert.employee = Employee(
                full_name=model.employee.full_name,
                department=model.employee.department,
                office=model.employee.office,
                phones=phones
            )
            
        return cert
