import argparse
import base64
import io
import os
import secrets
import zipfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encrypt(data: bytes, key: bytes, aad: bytes) -> bytes:
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, data, aad)


def build_team_package(source_zip: zipfile.ZipFile, team_id: int) -> bytes:
    package = io.BytesIO()
    prefix = f"cansat_datasets_v2/dataset_{team_id:02d}/"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for name in ("stage1/mission_brief.md", "stage1/telemetry.csv"):
            out.writestr(name, source_zip.read(prefix + name))
        out.writestr("stage2_locked.zip", source_zip.read(prefix + "stage2_locked.zip"))
        out.writestr("stage3_locked.zip", source_zip.read(prefix + "stage3_locked.zip"))
    return package.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", required=True)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--out", default="round2_data")
    parser.add_argument("--key", default="")
    args = parser.parse_args()

    key_text = args.key or os.environ.get("ROUND2_DATA_KEY", "")
    if not key_text:
        key_text = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        print("Generated ROUND2_DATA_KEY:")
        print(key_text)
        print("Store this only as a deployment secret. Do not commit it.")

    key = base64.urlsafe_b64decode(key_text + "=" * (-len(key_text) % 4))
    if len(key) != 32:
        raise SystemExit("ROUND2_DATA_KEY must decode to exactly 32 bytes.")

    os.makedirs(args.out, exist_ok=True)

    with zipfile.ZipFile(args.datasets) as source:
        for team_id in range(1, 12):
            encrypted = encrypt(build_team_package(source, team_id), f"dataset_{team_id:02d}".encode())
            path = os.path.join(args.out, f"dataset_{team_id:02d}.b64")
            with open(path, "wb") as f:
                f.write(base64.b64encode(encrypted))

    with zipfile.ZipFile(args.answers) as source:
        answer = source.read("ORGANIZER_KEYS_v2/master_answer_key_v2.csv")
    encrypted_answer = encrypt(answer, key, b"answer_key_v2")
    with open(os.path.join(args.out, "answer_key.b64"), "wb") as f:
        f.write(base64.b64encode(encrypted_answer))

    print(f"Prepared encrypted Round 2 data in: {args.out}")


if __name__ == "__main__":
    main()
