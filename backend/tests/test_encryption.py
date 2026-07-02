from app.security.encryption import decrypt_secret, encrypt_secret


def test_encrypt_decrypt_roundtrip():
    plaintext = "ghp_supersecrettoken1234567890"
    ciphertext = encrypt_secret(plaintext)
    assert ciphertext != plaintext
    assert decrypt_secret(ciphertext) == plaintext
