import pytest

from certificate_analyzer.infrastructure.encryption import DataCipher, DecryptionError


@pytest.mark.parametrize("data", [b"", b"certificate", bytes(range(256))])
def test_roundtrip_and_randomized_encryption(data):
    cipher = DataCipher(DataCipher.generate_key())
    first = cipher.encrypt(data, context=b"certificate:123")
    second = cipher.encrypt(data, context=b"certificate:123")
    assert first != second
    assert cipher.decrypt(first, context=b"certificate:123") == data


def test_wrong_key_and_context_are_rejected():
    cipher = DataCipher(DataCipher.generate_key())
    envelope = cipher.encrypt(b"secret", context=b"employee:1:phone")
    with pytest.raises(DecryptionError):
        cipher.decrypt(envelope, context=b"employee:2:phone")
    with pytest.raises(DecryptionError):
        DataCipher(DataCipher.generate_key()).decrypt(envelope, context=b"employee:1:phone")


def test_every_envelope_byte_is_authenticated():
    cipher = DataCipher(DataCipher.generate_key())
    envelope = cipher.encrypt(b"secret")
    for index in range(len(envelope)):
        tampered = bytearray(envelope)
        tampered[index] ^= 1
        with pytest.raises(DecryptionError):
            cipher.decrypt(bytes(tampered))


@pytest.mark.parametrize("key", [b"", b"a" * 16, b"a" * 31, b"a" * 33, "a" * 32])
def test_invalid_key_rejected(key):
    with pytest.raises(ValueError):
        DataCipher(key)


def test_limits_and_truncated_input(monkeypatch):
    cipher = DataCipher(DataCipher.generate_key())
    monkeypatch.setattr(DataCipher, "MAX_DATA_SIZE", 4)
    with pytest.raises(ValueError):
        cipher.encrypt(b"12345")
    envelope = cipher.encrypt(b"1234")
    with pytest.raises(DecryptionError):
        cipher.decrypt(envelope[:-1])
    with pytest.raises(DecryptionError):
        cipher.decrypt(envelope + b"x")
    with pytest.raises(ValueError):
        cipher.encrypt(b"", context=b"x" * 4097)
