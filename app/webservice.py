"""Portal service endpoints (/webservice/api/...)."""
import logging
import os
import random
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

log = logging.getLogger("fibergrid.webservice")

bp = Blueprint("webservice", __name__, url_prefix="/webservice")

EXPORT_DIR = Path(__file__).resolve().parent / "exports"

_PROVINCES = (
    "Adana,Adıyaman,Afyonkarahisar,Ağrı,Aksaray,Amasya,Ankara,Antalya,Ardahan,Artvin,"
    "Aydın,Balıkesir,Bartın,Batman,Bayburt,Bilecik,Bingöl,Bitlis,Bolu,Burdur,"
    "Bursa,Çanakkale,Çankırı,Çorum,Denizli,Diyarbakır,Düzce,Edirne,Elazığ,Erzincan,"
    "Erzurum,Eskişehir,Gaziantep,Giresun,Gümüşhane,Hakkâri,Hatay,Iğdır,Isparta,İstanbul,"
    "İzmir,Kahramanmaraş,Karabük,Karaman,Kars,Kastamonu,Kayseri,Kırıkkale,Kırklareli,Kırşehir,"
    "Kilis,Kocaeli,Konya,Kütahya,Malatya,Manisa,Mardin,Mersin,Muğla,Muş,"
    "Nevşehir,Niğde,Ordu,Osmaniye,Rize,Sakarya,Samsun,Siirt,Sinop,Sivas,"
    "Şanlıurfa,Şırnak,Tekirdağ,Tokat,Trabzon,Tunceli,Uşak,Van,Yalova,Yozgat,Zonguldak"
).split(",")

_ADLAR = ("Ahmet", "Mehmet", "Ayşe", "Fatma", "Mustafa", "Zeynep", "Emre", "Elif",
          "Burak", "Merve", "Onur", "Selin", "Kerem", "Deniz", "Cem", "Ece")
_SOYADLAR = ("Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Yıldırım",
             "Öztürk", "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan",
             "Çetin", "Kara")

_ISTANBUL_ILCELER = [
    "Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler",
    "Bakırköy", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beykoz", "Beylikdüzü",
    "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler", "Esenyurt",
    "Eyüpsultan", "Fatih", "Gaziosmanpaşa", "Güngören", "Kadıköy", "Kağıthane",
    "Kartal", "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer",
    "Silivri", "Sultanbeyli", "Sultangazi", "Şile", "Şişli", "Tuzla",
    "Ümraniye", "Üsküdar", "Zeytinburnu",
]

_ILLER = []
for _index, _il in enumerate(_PROVINCES):
    _sorumlu = f"{_ADLAR[_index % len(_ADLAR)]} {_SOYADLAR[_index % len(_SOYADLAR)]}"
    _not = None
    if _il == "İstanbul":
        _not = ("İç saha notu: izleme anahtarı "
                "FLAG{r3c0n_publ1c_4ddr3ss_d4t4} — 2026-08 bakımı")
    elif _il in ("Ankara", "İzmir"):
        _not = "Bölge saha koordinasyonu güncellendi."
    _ILLER.append({
        "plaka": _index + 1,
        "il": _il,
        "sorumlu": _sorumlu,
        "not": _not,
    })


@bp.get("/api/AddressData/Iller")
def address_iller():
    return jsonify({"iller": _ILLER})


@bp.get("/api/AddressData/Ilceler")
def address_ilceler():
    il = request.args.get("il", "").strip()
    if il == "İstanbul":
        return jsonify({"il": il, "ilceler": _ISTANBUL_ILCELER})
    return jsonify({
        "il": il,
        "ilceler": [],
        "not": "İlçe listesi yalnızca saha paketi kapsamındaki iller için yayımlanır.",
    })


@bp.route("/api/FTTH_ENVANTER/export", methods=["GET", "POST"])
def ftth_envanter_export():
    job_id = f"EXP-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{random.randint(1000, 9999)}"
    log.info("FTTH_ENVANTER export job queued: %s", job_id)
    return jsonify({
        "is_id": job_id,
        "durum": "KUYRUKTA",
        "mesaj": "Dışa aktarma işi kuyruğa alındı.",
    })


@bp.get("/api/Export")
def export_download():
    name = request.args.get("file", "").strip()
    if not name or name != os.path.basename(name):
        return jsonify({"hata": "Geçersiz dosya adı."}), 400
    path = EXPORT_DIR / name
    if not path.is_file():
        return jsonify({"hata": "Dosya bulunamadı."}), 404
    return send_file(path, as_attachment=True, download_name=name)
