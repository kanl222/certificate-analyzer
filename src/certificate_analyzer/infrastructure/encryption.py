"""Standalone AES-256-GCM envelope; deliberately not wired into application services."""

import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class DecryptionError(ValueError):
    """Envelope cannot be authenticated or has an unsupported format."""


class DataCipher:
    """Encrypt bytes with an externally supplied 32-byte secret key.

    Context binds ciphertext to a record/field and must match on decryption.
    The caller owns key storage, backup, access control and rotation.
    This class performs no filesystem, database or logging operations.
    """

    _HEADER = b"CAENC\x01"
    _NONCE_SIZE = 12
    _TAG_SIZE = 16
    MAX_DATA_SIZE = 16 * 1024 * 1024
    MAX_CONTEXT_SIZE = 4096

    def __init__(self, key: bytes) -> None:
        if not isinstance(key, bytes) or len(key) != 32:
            raise ValueError("Ключ должен содержать ровно 32 байта")
        self._cipher = AESGCM(key)

    @staticmethod
    def generate_key() -> bytes:
        """Generate a secret; never store it alongside ciphertext."""
        return AESGCM.generate_key(bit_length=256)

    @classmethod
    def _check_context(cls, context: bytes) -> None:
        if not isinstance(context, bytes):
            raise TypeError("Контекст должен иметь тип bytes")
        if len(context) > cls.MAX_CONTEXT_SIZE:
            raise ValueError("Контекст превышает допустимый размер")

    def encrypt(self, data: bytes, *, context: bytes = b"") -> bytes:
        """Return versioned header + random nonce + authenticated ciphertext."""
        self._check_context(context)
        if not isinstance(data, bytes):
            raise TypeError("Данные должны иметь тип bytes")
        if len(data) > self.MAX_DATA_SIZE:
            raise ValueError("Данные превышают допустимый размер")
        nonce = os.urandom(self._NONCE_SIZE)
        ciphertext = self._cipher.encrypt(nonce, data, self._HEADER + context)
        return self._HEADER + nonce + ciphertext

    def decrypt(self, envelope: bytes, *, context: bytes = b"") -> bytes:
        """Release plaintext only after successful authentication."""
        self._check_context(context)
        if not isinstance(envelope, bytes):
            raise TypeError("Зашифрованные данные должны иметь тип bytes")
        overhead = len(self._HEADER) + self._NONCE_SIZE + self._TAG_SIZE
        if (
            not overhead <= len(envelope) <= self.MAX_DATA_SIZE + overhead
            or not envelope.startswith(self._HEADER)
        ):
            raise DecryptionError("Неподдерживаемый или повреждённый формат данных")
        offset = len(self._HEADER)
        nonce = envelope[offset:offset + self._NONCE_SIZE]
        ciphertext = envelope[offset + self._NONCE_SIZE:]
        try:
            return self._cipher.decrypt(nonce, ciphertext, self._HEADER + context)
        except InvalidTag:
            raise DecryptionError(
                "Не удалось расшифровать данные: неверный ключ, контекст или данные повреждены"
            ) from None
