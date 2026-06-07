from pathlib import Path
import requests

out_dir = Path("data/01_raw/nhanes_2013_2014")
out_dir.mkdir(parents=True, exist_ok=True)

files = {
    "DEMO_H.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2013-2014/DEMO_H.XPT",
    "BIOPRO_H.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2013-2014/BIOPRO_H.XPT",
    "BMX_H.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2013-2014/BMX_H.XPT",
    "BPX_H.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2013-2014/BPX_H.XPT",
    "SMQ_H.XPT": "https://wwwn.cdc.gov/Nchs/Nhanes/2013-2014/SMQ_H.XPT",
}

for name, url in files.items():
    out_path = out_dir / name
    resp = requests.get(url, timeout=120, allow_redirects=True)
    print(name, resp.status_code, resp.headers.get("content-type"))
    out_path.write_bytes(resp.content)
    print("→ guardado:", out_path)