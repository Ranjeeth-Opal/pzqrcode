import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import ipaddress

def generate_cert():
    # Generate key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    # Generate Certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"AE"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Dubai"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Dubai"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Opal ERP"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, u"IT"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"mini.opalerp.com"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        # 10 years
        datetime.datetime.utcnow() + datetime.timedelta(days=3650)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"mini.opalerp.com"),
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(key, hashes.SHA256(), default_backend())

    # Save to disk
    with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    with open("key.pem", "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    print("Certificate and Key generated for mini.opalerp.com (using cryptography)")

if __name__ == "__main__":
    generate_cert()
