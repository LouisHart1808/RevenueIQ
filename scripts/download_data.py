"""Download Olist from its publisher's public Kaggle endpoint."""

from pathlib import Path
import hashlib
import json
import zipfile
import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / "olist.zip"
    url = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
    if not archive.exists():
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        archive.write_bytes(response.content)
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            if Path(name).name != name or not name.endswith(".csv"):
                raise ValueError(f"Unexpected archive member: {name}")
        z.extractall(raw)
    manifest = {
        "source": url,
        "license": "CC BY-NC-SA 4.0",
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.glob("*.csv")},
    }
    (ROOT / "docs/data_manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
