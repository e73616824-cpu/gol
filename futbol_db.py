import sqlite3
import random
from datetime import date
from futbol_data import LIGLER

DB_PATH = "futbol.db"

def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def setup_db():
    with db_connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS takimlar (
            takim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lig TEXT, isim TEXT,
            puan INTEGER DEFAULT 0, galibiyet INTEGER DEFAULT 0, beraberlik INTEGER DEFAULT 0, maglubiyet INTEGER DEFAULT 0,
            atilan_gol INTEGER DEFAULT 0, yenilen_gol INTEGER DEFAULT 0
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS oyuncular (
            oyuncu_id INTEGER PRIMARY KEY AUTOINCREMENT,
            takim_id INTEGER, isim TEXT, pozisyon TEXT, guc INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS maclar (
            mac_id INTEGER PRIMARY KEY AUTOINCREMENT,
            hafta INTEGER, lig TEXT,
            ev_takim INTEGER, dep_takim INTEGER,
            ev_gol INTEGER, dep_gol INTEGER,
            oynanmis INTEGER DEFAULT 0
        )""")
        c.commit()

def init_lig(lig_adi):
    with db_connect() as c:
        # Takımları ve oyuncuları veritabanına ekle
        for takim in LIGLER[lig_adi]:
            c.execute("INSERT INTO takimlar (lig, isim) VALUES (?, ?)", (lig_adi, takim["isim"]))
            takim_id = c.execute("SELECT takim_id FROM takimlar WHERE isim=? AND lig=?", (takim["isim"], lig_adi)).fetchone()["takim_id"]
            for o in takim["oyuncular"]:
                c.execute("INSERT INTO oyuncular (takim_id, isim, pozisyon, guc) VALUES (?, ?, ?, ?)", (takim_id, o["isim"], o["pozisyon"], o["guc"]))
        c.commit()

def takimlari_getir(lig):
    with db_connect() as c:
        rows = c.execute("SELECT * FROM takimlar WHERE lig=? ORDER BY puan DESC, atilan_gol-yenilen_gol DESC", (lig,)).fetchall()
        return [dict(r) for r in rows]
        
def oyunculari_getir(takim_id):
    with db_connect() as c:
        rows = c.execute("SELECT * FROM oyuncular WHERE takim_id=?", (takim_id,)).fetchall()
        return [dict(r) for r in rows]

def fikstur_olustur(lig):
    takimlar = takimlari_getir(lig)
    ids = [t["takim_id"] for t in takimlar]
    n = len(ids)
    fikstur = []
    for i in range(n - 1):
        for j in range(n // 2):
            ev = ids[j]
            dep = ids[n - 1 - j]
            if i % 2 == 0:
                fikstur.append((ev, dep, i+1))
            else:
                fikstur.append((dep, ev, i+1))
        ids = [ids[0]] + ids[2:] + [ids[1]]
    with db_connect() as c:
        for ev, dep, hafta in fikstur:
            c.execute("INSERT INTO maclar (hafta, lig, ev_takim, dep_takim) VALUES (?, ?, ?, ?)", (hafta, lig, ev, dep))
        c.commit()

def bu_hafta_maclari(lig, hafta):
    with db_connect() as c:
        rows = c.execute("SELECT * FROM maclar WHERE lig=? AND hafta=? AND oynanmis=0", (lig, hafta)).fetchall()
        return [dict(r) for r in rows]

def takim_bilgisi(takim_id):
    with db_connect() as c:
        t = c.execute("SELECT * FROM takimlar WHERE takim_id=?", (takim_id,)).fetchone()
        return dict(t) if t else None

def otomatik_maclari_oyna(lig, hafta):
    maclar = bu_hafta_maclari(lig, hafta)
    for mac in maclar:
        ev_id, dep_id = mac["ev_takim"], mac["dep_takim"]
        ev_oy = oyunculari_getir(ev_id)
        dep_oy = oyunculari_getir(dep_id)
        ev_guc = sum(o["guc"] for o in ev_oy[:11]) // 11
        dep_guc = sum(o["guc"] for o in dep_oy[:11]) // 11
        ev_gol = max(0, int(random.gauss(ev_guc/15, 0.9)))
        dep_gol = max(0, int(random.gauss(dep_guc/15, 0.9)))
        with db_connect() as c:
            c.execute("UPDATE maclar SET ev_gol=?, dep_gol=?, oynanmis=1 WHERE mac_id=?",
                      (ev_gol, dep_gol, mac["mac_id"]))
            g = 3 if ev_gol > dep_gol else (1 if ev_gol == dep_gol else 0)
            d = 3 if dep_gol > ev_gol else (1 if dep_gol == ev_gol else 0)
            c.execute("UPDATE takimlar SET puan=puan+?, galibiyet=galibiyet+?, beraberlik=beraberlik+?, maglubiyet=maglubiyet+?, atilan_gol=atilan_gol+?, yenilen_gol=yenilen_gol+? WHERE takim_id=?",
                      (g, 1 if g == 3 else 0, 1 if g == 1 else 0, 1 if g == 0 else 0, ev_gol, dep_gol, ev_id))
            c.execute("UPDATE takimlar SET puan=puan+?, galibiyet=galibiyet+?, beraberlik=beraberlik+?, maglubiyet=maglubiyet+?, atilan_gol=atilan_gol+?, yenilen_gol=yenilen_gol+? WHERE takim_id=?",
                      (d, 1 if d == 3 else 0, 1 if d == 1 else 0, 1 if d == 0 else 0, dep_gol, ev_gol, dep_id))
            c.commit()
