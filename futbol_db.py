import sqlite3
import random
import logging
from futbol_data import LIGLER

DB_PATH = "futbol.db"
logger = logging.getLogger(__name__)


# ─── Bağlantı ────────────────────────────────────────────────────────────────

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Kurulum ─────────────────────────────────────────────────────────────────

def setup_db():
    """Tabloları oluştur (yoksa)."""
    try:
        with db_connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS liglar (
                    lig_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    lig_adi  TEXT UNIQUE NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS takimlar (
                    takim_id  INTEGER PRIMARY KEY AUTOINCREMENT,
                    lig_id    INTEGER NOT NULL,
                    isim      TEXT NOT NULL,
                    puan      INTEGER DEFAULT 0,
                    galibiyet INTEGER DEFAULT 0,
                    beraberlik INTEGER DEFAULT 0,
                    maglubiyet INTEGER DEFAULT 0,
                    atilan_gol  INTEGER DEFAULT 0,
                    yenilen_gol INTEGER DEFAULT 0,
                    FOREIGN KEY (lig_id) REFERENCES liglar(lig_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oyuncular (
                    oyuncu_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    takim_id  INTEGER NOT NULL,
                    isim      TEXT NOT NULL,
                    pozisyon  TEXT NOT NULL,
                    guc       INTEGER NOT NULL,
                    FOREIGN KEY (takim_id) REFERENCES takimlar(takim_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS maclar (
                    mac_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    lig_id    INTEGER NOT NULL,
                    hafta     INTEGER NOT NULL,
                    ev_takim  INTEGER NOT NULL,
                    dep_takim INTEGER NOT NULL,
                    ev_gol    INTEGER,
                    dep_gol   INTEGER,
                    oynanmis  INTEGER DEFAULT 0,
                    FOREIGN KEY (lig_id)    REFERENCES liglar(lig_id),
                    FOREIGN KEY (ev_takim)  REFERENCES takimlar(takim_id),
                    FOREIGN KEY (dep_takim) REFERENCES takimlar(takim_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kullanici_takimlar (
                    kullanici_id INTEGER NOT NULL,
                    takim_id     INTEGER NOT NULL,
                    PRIMARY KEY (kullanici_id, takim_id),
                    FOREIGN KEY (takim_id) REFERENCES takimlar(takim_id)
                )
            """)
            conn.commit()
        logger.info("Veritabanı kurulumu tamamlandı.")
    except Exception as e:
        logger.error(f"setup_db hatası: {e}")
        raise


# ─── Lig işlemleri ───────────────────────────────────────────────────────────

def lig_olustur(lig_adi: str) -> dict:
    """
    Yeni bir lig oluşturur; futbol_data.py'de tanımlıysa takımları/oyuncuları
    da ekler. Zaten varsa mevcut kaydı döner.
    Döner: {"lig_id": int, "yeni": bool}
    """
    try:
        with db_connect() as conn:
            mevcut = conn.execute(
                "SELECT lig_id FROM liglar WHERE lig_adi = ?", (lig_adi,)
            ).fetchone()
            if mevcut:
                return {"lig_id": mevcut["lig_id"], "yeni": False}

            conn.execute("INSERT INTO liglar (lig_adi) VALUES (?)", (lig_adi,))
            lig_id = conn.execute(
                "SELECT lig_id FROM liglar WHERE lig_adi = ?", (lig_adi,)
            ).fetchone()["lig_id"]

            # futbol_data.py'de bu lig varsa takımları yükle
            if lig_adi in LIGLER:
                for takim in LIGLER[lig_adi]:
                    conn.execute(
                        "INSERT INTO takimlar (lig_id, isim) VALUES (?, ?)",
                        (lig_id, takim["isim"]),
                    )
                    takim_id = conn.execute(
                        "SELECT takim_id FROM takimlar WHERE lig_id=? AND isim=?",
                        (lig_id, takim["isim"]),
                    ).fetchone()["takim_id"]
                    for o in takim["oyuncular"]:
                        conn.execute(
                            "INSERT INTO oyuncular (takim_id, isim, pozisyon, guc) "
                            "VALUES (?, ?, ?, ?)",
                            (takim_id, o["isim"], o["pozisyon"], o["guc"]),
                        )

            conn.commit()
            return {"lig_id": lig_id, "yeni": True}
    except Exception as e:
        logger.error(f"lig_olustur hatası: {e}")
        raise


def lig_listesi() -> list[dict]:
    """Tüm ligleri döner."""
    try:
        with db_connect() as conn:
            rows = conn.execute("SELECT * FROM liglar ORDER BY lig_id").fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"lig_listesi hatası: {e}")
        return []


def lig_bilgisi_id(lig_id: int) -> dict | None:
    try:
        with db_connect() as conn:
            row = conn.execute(
                "SELECT * FROM liglar WHERE lig_id = ?", (lig_id,)
            ).fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"lig_bilgisi_id hatası: {e}")
        return None


# ─── Takım işlemleri ─────────────────────────────────────────────────────────

def takimlari_getir(lig_id: int) -> list[dict]:
    """Ligi sıralı takım tablosu olarak döner."""
    try:
        with db_connect() as conn:
            rows = conn.execute(
                """SELECT * FROM takimlar WHERE lig_id = ?
                   ORDER BY puan DESC,
                            (atilan_gol - yenilen_gol) DESC,
                            atilan_gol DESC""",
                (lig_id,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"takimlari_getir hatası: {e}")
        return []


def takim_bilgisi(takim_id: int) -> dict | None:
    try:
        with db_connect() as conn:
            row = conn.execute(
                "SELECT * FROM takimlar WHERE takim_id = ?", (takim_id,)
            ).fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"takim_bilgisi hatası: {e}")
        return None


# ─── Oyuncu işlemleri ────────────────────────────────────────────────────────

def oyunculari_getir(takim_id: int) -> list[dict]:
    try:
        with db_connect() as conn:
            rows = conn.execute(
                "SELECT * FROM oyuncular WHERE takim_id = ? ORDER BY guc DESC",
                (takim_id,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"oyunculari_getir hatası: {e}")
        return []


# ─── Kullanıcı–takım eşleşmesi ───────────────────────────────────────────────

def takim_sec(kullanici_id: int, takim_id: int) -> bool:
    """Kullanıcıya takım atar (önceki seçimi siler)."""
    try:
        with db_connect() as conn:
            conn.execute(
                "DELETE FROM kullanici_takimlar WHERE kullanici_id = ?",
                (kullanici_id,),
            )
            conn.execute(
                "INSERT INTO kullanici_takimlar (kullanici_id, takim_id) VALUES (?, ?)",
                (kullanici_id, takim_id),
            )
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"takim_sec hatası: {e}")
        return False


def kullanici_takimi(kullanici_id: int) -> dict | None:
    """Kullanıcının seçtiği takımı döner."""
    try:
        with db_connect() as conn:
            row = conn.execute(
                """SELECT t.* FROM takimlar t
                   JOIN kullanici_takimlar kt ON kt.takim_id = t.takim_id
                   WHERE kt.kullanici_id = ?""",
                (kullanici_id,),
            ).fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error(f"kullanici_takimi hatası: {e}")
        return None


# ─── Fikstür ─────────────────────────────────────────────────────────────────

def fikstur_olustur(lig_id: int) -> int:
    """
    Round-robin fikstür oluşturur.
    Döner: oluşturulan maç sayısı (0 ise zaten fikstür vardı).
    """
    try:
        with db_connect() as conn:
            mevcut = conn.execute(
                "SELECT COUNT(*) as n FROM maclar WHERE lig_id = ?", (lig_id,)
            ).fetchone()["n"]
            if mevcut > 0:
                return 0  # Zaten oluşturulmuş

        takimlar = takimlari_getir(lig_id)
        if len(takimlar) < 2:
            return 0

        ids = [t["takim_id"] for t in takimlar]
        # Tek sayıda takım varsa "bay" ekle
        if len(ids) % 2 != 0:
            ids.append(None)

        n = len(ids)
        toplam_mac = 0

        with db_connect() as conn:
            for tur in range(n - 1):
                for j in range(n // 2):
                    ev = ids[j]
                    dep = ids[n - 1 - j]
                    if ev is None or dep is None:
                        continue  # Bay haftası
                    hafta = tur + 1
                    conn.execute(
                        "INSERT INTO maclar (lig_id, hafta, ev_takim, dep_takim) "
                        "VALUES (?, ?, ?, ?)",
                        (lig_id, hafta, ev, dep),
                    )
                    toplam_mac += 1
                # Round-robin rotasyonu (ilk eleman sabit)
                ids = [ids[0]] + [ids[-1]] + ids[1:-1]
            conn.commit()

        return toplam_mac
    except Exception as e:
        logger.error(f"fikstur_olustur hatası: {e}")
        raise


def fikstur_getir(lig_id: int) -> list[dict]:
    """Tüm fikstürü döner."""
    try:
        with db_connect() as conn:
            rows = conn.execute(
                "SELECT * FROM maclar WHERE lig_id = ? ORDER BY hafta, mac_id",
                (lig_id,),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"fikstur_getir hatası: {e}")
        return []


def hafta_maclari(lig_id: int, hafta: int) -> list[dict]:
    """Belirli haftanın tüm maçlarını döner (oynanmış + oynanmamış)."""
    try:
        with db_connect() as conn:
            rows = conn.execute(
                "SELECT * FROM maclar WHERE lig_id = ? AND hafta = ? ORDER BY mac_id",
                (lig_id, hafta),
            ).fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"hafta_maclari hatası: {e}")
        return []


# ─── Maç simülasyonu ─────────────────────────────────────────────────────────

def _gol_hesapla(oyuncular: list[dict]) -> int:
    """Takım gücüne göre rastgele gol sayısı üretir."""
    if not oyuncular:
        return random.randint(0, 2)
    ort_guc = sum(o["guc"] for o in oyuncular) / len(oyuncular)
    # Güç 80-92 aralığında → ortalama ~1.5-2.5 gol
    beklenen = ort_guc / 40.0
    gol = max(0, round(random.gauss(beklenen, 1.0)))
    return gol


def hafta_oyna(lig_id: int, hafta: int) -> list[dict]:
    """
    Haftanın oynanmamış maçlarını simüle eder.
    Döner: oynanan maçların sonuç listesi
        [{"ev": "...", "dep": "...", "ev_gol": n, "dep_gol": n}, ...]
    """
    try:
        maclar = hafta_maclari(lig_id, hafta)
        oynanmamis = [m for m in maclar if not m["oynanmis"]]

        if not oynanmamis:
            return []

        sonuclar = []
        with db_connect() as conn:
            for mac in oynanmamis:
                ev_id  = mac["ev_takim"]
                dep_id = mac["dep_takim"]

                ev_oyuncular  = oyunculari_getir(ev_id)
                dep_oyuncular = oyunculari_getir(dep_id)

                ev_gol  = _gol_hesapla(ev_oyuncular)
                dep_gol = _gol_hesapla(dep_oyuncular)

                # Maç sonucunu kaydet
                conn.execute(
                    "UPDATE maclar SET ev_gol=?, dep_gol=?, oynanmis=1 WHERE mac_id=?",
                    (ev_gol, dep_gol, mac["mac_id"]),
                )

                # Puan tablosunu güncelle
                if ev_gol > dep_gol:
                    ev_p, dep_p = 3, 0
                    ev_g, dep_g = 1, 0
                    ev_b, dep_b = 0, 0
                    ev_m, dep_m = 0, 1
                elif ev_gol < dep_gol:
                    ev_p, dep_p = 0, 3
                    ev_g, dep_g = 0, 1
                    ev_b, dep_b = 0, 0
                    ev_m, dep_m = 1, 0
                else:
                    ev_p = dep_p = 1
                    ev_g = dep_g = 0
                    ev_b = dep_b = 1
                    ev_m = dep_m = 0

                conn.execute(
                    """UPDATE takimlar SET
                        puan       = puan       + ?,
                        galibiyet  = galibiyet  + ?,
                        beraberlik = beraberlik + ?,
                        maglubiyet = maglubiyet + ?,
                        atilan_gol  = atilan_gol  + ?,
                        yenilen_gol = yenilen_gol + ?
                       WHERE takim_id = ?""",
                    (ev_p, ev_g, ev_b, ev_m, ev_gol, dep_gol, ev_id),
                )
                conn.execute(
                    """UPDATE takimlar SET
                        puan       = puan       + ?,
                        galibiyet  = galibiyet  + ?,
                        beraberlik = beraberlik + ?,
                        maglubiyet = maglubiyet + ?,
                        atilan_gol  = atilan_gol  + ?,
                        yenilen_gol = yenilen_gol + ?
                       WHERE takim_id = ?""",
                    (dep_p, dep_g, dep_b, dep_m, dep_gol, ev_gol, dep_id),
                )

                ev_takim  = takim_bilgisi(ev_id)
                dep_takim = takim_bilgisi(dep_id)
                sonuclar.append({
                    "ev":      ev_takim["isim"]  if ev_takim  else str(ev_id),
                    "dep":     dep_takim["isim"] if dep_takim else str(dep_id),
                    "ev_gol":  ev_gol,
                    "dep_gol": dep_gol,
                })

            conn.commit()

        return sonuclar
    except Exception as e:
        logger.error(f"hafta_oyna hatası: {e}")
        raise
