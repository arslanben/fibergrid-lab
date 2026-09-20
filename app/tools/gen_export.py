#!/usr/bin/env python3
"""Generates the FTTH_ENVANTER export archive served by /webservice/api/Export."""
import csv
import io
import os
import random
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(HERE, "..", "exports")
EXPORT_NAME = "FTTH_ENVANTER_20260814_a91f3c.zip"
FLAG = "FLAG{un4uth_3xp0rt_4rch1v3}"

ILCELER = [
    ("İSTANBUL", "KADIKÖY"), ("İSTANBUL", "MALTEPE"), ("İSTANBUL", "ÜMRANİYE"),
    ("İSTANBUL", "PENDİK"), ("ANKARA", "ÇANKAYA"), ("ANKARA", "ETİMESGUT"),
    ("İZMİR", "BORNOVA"), ("İZMİR", "BUCA"), ("BURSA", "NİLÜFER"),
    ("ANTALYA", "KEPEZ"), ("ADANA", "ÇUKUROVA"), ("KONYA", "SELÇUKLU"),
]

NOTLAR = [
    "saha doğrulaması bekliyor",
    "port kapasitesi güncellendi",
    "splitter değişimi planlandı",
    "UAVT kodu eşleşti",
    "BBK kaydı kontrol edilecek",
]


def main() -> None:
    random.seed(20260814)
    os.makedirs(EXPORT_DIR, exist_ok=True)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["OLT_KODU", "PORT", "SPLITTER", "UAVT", "BBK", "IL", "ILCE",
                     "DURUM", "ACIKLAMA"])
    for index in range(300):
        il, ilce = ILCELER[index % len(ILCELER)]
        olt = f"OLT-{il[:3]}-{index // 12 + 1:03d}"
        port = f"P{(index % 16) + 1:02d}"
        splitter = f"SPL-{(index % 8) + 1:02d}"
        uavt = f"{10000000 + index * 37}"
        bbk = f"BBK{400000 + index * 13}"
        durum = "DOĞRULANDI" if index % 5 else "BEKLEMEDE"
        aciklama = FLAG if index == 0 else NOTLAR[index % len(NOTLAR)]
        writer.writerow([olt, port, splitter, uavt, bbk, il, ilce, durum, aciklama])

    readme = (
        "Lodos Telekom - FTTH_ENVANTER haftalık dışa aktarım\n"
        "Oluşturma: 2026-08-14 03:12 UTC\n"
        "Kayıt sayısı: 300\n"
        "Bu dosya kurum içi kullanım içindir; dağıtımı yasaktır.\n"
    )

    target = os.path.join(EXPORT_DIR, EXPORT_NAME)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("FTTH_ENVANTER_20260814.csv", buffer.getvalue())
        archive.writestr("OKUBENI.txt", readme)
    print(f"generated {target}")


if __name__ == "__main__":
    main()
