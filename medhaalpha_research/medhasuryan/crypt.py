# Keystream = SHA-256(key | nonce | counter) blocks; ciphertext = plaintext XOR keystream. Stdlib only, same code both ends.
import hashlib, hmac


def stream_xor(key: bytes, nonce: bytes, data: bytes) -> bytes:
    out = bytearray(len(data))
    for i in range(0, len(data), 32):
        ks = hashlib.sha256(key + nonce + (i // 32).to_bytes(8, 'big')).digest()
        chunk = data[i:i + 32]
        out[i:i + len(chunk)] = bytes(a ^ b for a, b in zip(chunk, ks))
    return bytes(out)
