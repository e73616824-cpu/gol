"""
Veritabanı işlemleri — SQLite.
Tablolar: liglar, kullanici_takimlar, maclar
"""

import sqlite3
import json
import random
import itertools
from pathlib import Path
from futbol_data import LIGLER, get_lig, get_takim

DB_PATH = Path("futbol.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Tabloları oluştur (yoksa)."""
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS liglar (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     TEXT NOT NULL,
                lig_id      TEXT NOT NULL,
                lig_adi     TEXT NOT NULL,
                durum       TEXT NOT NULL DEFAULT 'aktif',
                mevcut_hafta INTEGER NOT NULL DEFAULT 0,
                toplam_hafta INTEGER NOT NULL DEFAULT 0,
                fikstur     TEXT NOT NULL DEFAULT '[]',
                puan_tablosu TEXT NOT NULL DEFAULT '{}',
                olusturuldu INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                UNIQUE(chat_id, lig_id)
            );

            CREATE TABLE IF NOT EXISTS kullanici_takimlar (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT NOT NULL,
                chat_id     TEXT NOT NULL,
                lig_id      TEXT NOT NULL,
                takim_id    TEXT NOT NULL,
                UNIQUE(user_id, chat_id, lig_id)
            );

            CREATE TABLE IF NOT EXISTS maclar (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     TEXT NOT NULL,
                lig_id      TEXT NOT NULL,
                hafta       INTEGER NOT NULL,
                ev_takim    TEXT NOT NULL,
                deplasman   TEXT NOT NULL,
                ev_gol      INTEGER NOT NULL DEFAULT 0,
                dep_gol     INTEGER NOT NULL DEFAULT 0,
                olaylar     TEXT NOT NULL DEFAULT '[]',
                oynanma_zamani INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            );
            """
        )


# ─── Yardımcı ─────────────────────────────────────────────────────────────────

def _takim_gucu(takim: dict) -> float:
    oyuncular = takim.get("oyuncular", [])
    if not oyuncular:
        return 70.0
    return sum(o["overall"] for o in oyuncular) / len(oyuncular)


def _gol_uret(guc: float, rakip_guc: float) -> int:
    fark = guc - rakip_guc
    baz = 1.4 + (fark / 30)
    gol = max(0, round(baz + random.uniform(0, 2.5)))
    return min(gol, 7)


def _golcu_sec(oyuncular: list[dict]) -> str:
    agirliklar = {"ST": 40, "LW": 25, "RW": 25, "CAM": 20, "CM": 10,
                  "LB": 3, "RB": 3, "CB": 2, "GK": 0}
    havuz = []
    for o in oyuncular:
        w = agirliklar.get(o["mevki"], 5)
        havuz.extend([o["ad"]] * w)
    if not havuz:
        return random.choice(oyuncular)["ad"]
    return random.choice(havuz)


def _mac_olaylari(ev: dict, dep: dict, ev_gol: int, dep_gol: int) -> list[dict]:
    olaylar = []
    kullanilan_dakikalar: set[int] = set()

    def dakika() -> int:
        while True:
            d = random.randint(1, 90)
            if d not in kullanilan_dakikalar:
                kullanilan_dakikalar.add(d)
                return d

    for _ in range(ev_gol):
        olaylar.append({"tip": "gol", "takim": ev["kisaad"],
                        "oyuncu": _golcu_sec(ev["oyuncular"]), "dakika": dakika()})
    for _ in range(dep_gol):
        olaylar.append({"tip": "gol", "takim": dep["kisaad"],
                        "oyuncu": _golcu_sec(dep["oyuncular"]), "dakika": dakika()})

    sari_sayisi = random.randint(1, 4)
    for _ in range(sari_sayisi):
        takim = random.choice([ev, dep])
        oyuncu = random.choice(takim["oyuncular"])
        olaylar.append({"tip": "sari", "takim": takim["kisaad"],
                        "oyuncu": oyuncu["ad"], "dakika": dakika()})

    if random.random() < 0.1:
        takim = random.choice([ev, dep])
        oyuncu = random.choice(takim["oyuncular"])
        olaylar.append({"tip": "kirmizi", "takim": takim["kisaad"],
                        "oyuncu": oyuncu["ad"], "dakika": dakika()})

    return sorted(olaylar, key=lambda x: x["dakika"])


# ─── Fikstür ──────────────────────────────────────────────────────────────────

def _round_robin_fikstur(takimlar: list[dict]) -> list[list[dict]]:
    """
    Çift devreli round-robin fikstür üretir.
    Her eleman: [{"ev": takim_id, "dep": takim_id}, ...]
    """
    ids = [t["id"] for t in takimlar]
    n = len(ids)
    if n % 2 == 1:
        ids.append(None)  # bye
        n += 1

    haftalar = []
    for tur in range(2):  # çift devre
        for hafta_no in range(n - 1):
            mac_listesi = []
            for i in range(n // 2):
                ev_idx = (hafta_no + i) % (n - 1)
                dep_idx = (n - 1 - i + hafta_no) % (n - 1)
                if i == 0:
                    ev_idx = n - 1
                    dep_idx = hafta_no % (n - 1)

                ev_id = ids[ev_idx]
                dep_id = ids[dep_idx]

                if ev_id is None or dep_id is None:
                    continue

                if tur == 0:
                    mac_listesi.append({"ev": ev_id, "dep": dep_id})
                else:
                    mac_listesi.append({"ev": dep_id, "dep": ev_id})

            if mac_listesi:
                haftalar.append(mac_listesi)

    return haftalar


def _bos_puan_tablosu(takimlar: list[dict]) -> dict:
    tablo = {}
    for t in takimlar:
        tablo[t["id"]] = {
            "takim_id": t["id"],
            "takim_adi": t["ad"],
            "kisaad": t["kisaad"],
            "emoji": t["emoji"],
            "oynadigi": 0, "galibiyet": 0, "beraberlik": 0, "maglubiyet": 0,
            "attigi": 0, "yedigi": 0, "averaj": 0, "puan": 0,
        }
    return tablo


# ─── Lig İşlemleri ────────────────────────────────────────────────────────────

def lig_olustur(chat_id: str, lig_id: str) -> dict:
    """Yeni bir lig başlatır. Zaten varsa hata fırlatır."""
    lig_verisi = get_lig(lig_id)
    if not lig_verisi:
        raise ValueError(f"Lig bulunamadı: {lig_id}")

    takimlar = lig_verisi["takimlar"]
    fikstur = _round_robin_fikstur(takimlar)
    puan_tablosu = _bos_puan_tablosu(takimlar)

    with get_conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO liglar (chat_id, lig_id, lig_adi, durum,
                    mevcut_hafta, toplam_hafta, fikstur, puan_tablosu)
                VALUES (?, ?, ?, 'aktif', 0, ?, ?, ?)
                """,
                (
                    chat_id, lig_id, lig_verisi["ad"],
                    len(fikstur),
                    json.dumps(fikstur, ensure_ascii=False),
                    json.dumps(puan_tablosu, ensure_ascii=False),
                ),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"Bu ligde zaten bir sezon aktif! Önce /lig_sifirla komutunu kullan.")

    return {"lig_id": lig_id, "lig_adi": lig_verisi["ad"], "toplam_hafta": len(fikstur)}


def lig_getir(chat_id: str, lig_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM liglar WHERE chat_id=? AND lig_id=?",
            (chat_id, lig_id),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["fikstur"] = json.loads(d["fikstur"])
    d["puan_tablosu"] = json.loads(d["puan_tablosu"])
    return d


def aktif_ligler(chat_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM liglar WHERE chat_id=? AND durum='aktif'",
            (chat_id,),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["fikstur"] = json.loads(d["fikstur"])
        d["puan_tablosu"] = json.loads(d["puan_tablosu"])
        result.append(d)
    return result


# ─── Takım Seçimi ─────────────────────────────────────────────────────────────

def takim_sec(user_id: str, chat_id: str, lig_id: str, takim_id: str) -> None:
    """Kullanıcıya bir takım atar. Zaten seçilmişse günceller."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO kullanici_takimlar (user_id, chat_id, lig_id, takim_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, chat_id, lig_id) DO UPDATE SET takim_id=excluded.takim_id
            """,
            (user_id, chat_id, lig_id, takim_id),
        )


def kullanici_takimi(user_id: str, chat_id: str, lig_id: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT takim_id FROM kullanici_takimlar WHERE user_id=? AND chat_id=? AND lig_id=?",
            (user_id, chat_id, lig_id),
        ).fetchone()
    return row["takim_id"] if row else None


# ─── Maç Simülasyonu ──────────────────────────────────────────────────────────

def _puan_tablosu_guncelle(tablo: dict, ev_id: str, dep_id: str,
                            ev_gol: int, dep_gol: int) -> None:
    ev = tablo[ev_id]
    dep = tablo[dep_id]

    ev["oynadigi"] += 1
    dep["oynadigi"] += 1
    ev["attigi"] += ev_gol
    ev["yedigi"] += dep_gol
    dep["attigi"] += dep_gol
    dep["yedigi"] += ev_gol
    ev["averaj"] = ev["attigi"] - ev["yedigi"]
    dep["averaj"] = dep["attigi"] - dep["yedigi"]

    if ev_gol > dep_gol:
        ev["galibiyet"] += 1
        ev["puan"] += 3
        dep["maglubiyet"] += 1
    elif dep_gol > ev_gol:
        dep["galibiyet"] += 1
        dep["puan"] += 3
        ev["maglubiyet"] += 1
    else:
        ev["beraberlik"] += 1
        dep["beraberlik"] += 1
        ev["puan"] += 1
        dep["puan"] += 1


def hafta_oyna(chat_id: str, lig_id: str) -> dict:
    """
    Bir sonraki haftanın maçlarını simüle eder.
    Döndürür: {"hafta": int, "maclar": [...], "bitti": bool}
    """
    lig = lig_getir(chat_id, lig_id)
    if not lig:
        raise ValueError("Lig bulunamadı.")
    if lig["durum"] != "aktif":
        raise ValueError("Bu lig aktif değil.")

    sonraki_hafta = lig["mevcut_hafta"] + 1
    if sonraki_hafta > lig["toplam_hafta"]:
        raise ValueError("Tüm haftalar oynandı! Lig bitti.")

    fikstur = lig["fikstur"]
    hafta_maclari = fikstur[sonraki_hafta - 1]
    puan_tablosu = lig["puan_tablosu"]
    lig_verisi = get_lig(lig_id)

    sonuclar = []
    for mac in hafta_maclari:
        ev_takim = get_takim(lig_id, mac["ev"])
        dep_takim = get_takim(lig_id, mac["dep"])
        if not ev_takim or not dep_takim:
            continue

        ev_guc = _takim_gucu(ev_takim) + 3  # ev sahibi avantajı
        dep_guc = _takim_gucu(dep_takim)
        ev_gol = _gol_uret(ev_guc, dep_guc)
        dep_gol = _gol_uret(dep_guc, ev_guc)
        olaylar = _mac_olaylari(ev_takim, dep_takim, ev_gol, dep_gol)

        _puan_tablosu_guncelle(puan_tablosu, mac["ev"], mac["dep"], ev_gol, dep_gol)

        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO maclar (chat_id, lig_id, hafta, ev_takim, deplasman,
                    ev_gol, dep_gol, olaylar)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat_id, lig_id, sonraki_hafta,
                    mac["ev"], mac["dep"],
                    ev_gol, dep_gol,
                    json.dumps(olaylar, ensure_ascii=False),
                ),
            )

        sonuclar.append({
            "ev_takim": ev_takim,
            "dep_takim": dep_takim,
            "ev_gol": ev_gol,
            "dep_gol": dep_gol,
            "olaylar": olaylar,
        })

    bitti = sonraki_hafta >= lig["toplam_hafta"]

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE liglar
            SET mevcut_hafta=?, puan_tablosu=?, durum=?
            WHERE chat_id=? AND lig_id=?
            """,
            (
                sonraki_hafta,
                json.dumps(puan_tablosu, ensure_ascii=False),
                "bitti" if bitti else "aktif",
                chat_id, lig_id,
            ),
        )

    return {
        "hafta": sonraki_hafta,
        "toplam_hafta": lig["toplam_hafta"],
        "maclar": sonuclar,
        "puan_tablosu": puan_tablosu,
        "bitti": bitti,
    }


def puan_tablosu_getir(chat_id: str, lig_id: str) -> list[dict]:
    lig = lig_getir(chat_id, lig_id)
    if not lig:
        return []
    tablo = lig["puan_tablosu"]
    return sorted(
        tablo.values(),
        key=lambda x: (-x["puan"], -x["averaj"], -x["attigi"]),
    )


def fikstur_getir(chat_id: str, lig_id: str) -> dict:
    lig = lig_getir(chat_id, lig_id)
    if not lig:
        return {}
    return {
        "fikstur": lig["fikstur"],
        "mevcut_hafta": lig["mevcut_hafta"],
        "toplam_hafta": lig["toplam_hafta"],
        "lig_adi": lig["lig_adi"],
    }
