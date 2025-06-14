from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from base64 import urlsafe_b64encode

# Generate a new private key for EC (Elliptic Curve)
private_key = ec.generate_private_key(ec.SECP256R1())

# Get the raw bytes of the private key
private_key_bytes = private_key.private_numbers().private_value.to_bytes(32, 'big')
public_key_bytes = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

# Convert to base64 url-safe format
def b64url_encode(data):
    return urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

print("VAPID_PUBLIC_KEY =", b64url_encode(public_key_bytes))
print("VAPID_PRIVATE_KEY =", b64url_encode(private_key_bytes))
