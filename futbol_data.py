"""
Futbol lig ve takım verileri.
3 lig: Premier League, La Liga, Bundesliga
Her ligde gerçek takımlar ve oyuncular.
"""

LIGLER = {
    "premier_league": {
        "id": "premier_league",
        "ad": "Premier League",
        "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "takimlar": [
            {
                "id": "manchester_city",
                "ad": "Manchester City",
                "kisaad": "MCI",
                "emoji": "🔵",
                "stadyum": "Etihad Stadium",
                "oyuncular": [
                    {"ad": "Ederson", "mevki": "GK", "overall": 89},
                    {"ad": "Rúben Dias", "mevki": "CB", "overall": 88},
                    {"ad": "Rodri", "mevki": "CM", "overall": 91},
                    {"ad": "Kevin De Bruyne", "mevki": "CAM", "overall": 91},
                    {"ad": "Erling Haaland", "mevki": "ST", "overall": 94},
                ],
            },
            {
                "id": "arsenal",
                "ad": "Arsenal",
                "kisaad": "ARS",
                "emoji": "🔴",
                "stadyum": "Emirates Stadium",
                "oyuncular": [
                    {"ad": "David Raya", "mevki": "GK", "overall": 85},
                    {"ad": "William Saliba", "mevki": "CB", "overall": 87},
                    {"ad": "Thomas Partey", "mevki": "CM", "overall": 84},
                    {"ad": "Martin Ødegaard", "mevki": "CAM", "overall": 88},
                    {"ad": "Bukayo Saka", "mevki": "RW", "overall": 88},
                ],
            },
            {
                "id": "liverpool",
                "ad": "Liverpool",
                "kisaad": "LIV",
                "emoji": "🔴",
                "stadyum": "Anfield",
                "oyuncular": [
                    {"ad": "Alisson", "mevki": "GK", "overall": 90},
                    {"ad": "Virgil van Dijk", "mevki": "CB", "overall": 88},
                    {"ad": "Alexis Mac Allister", "mevki": "CM", "overall": 84},
                    {"ad": "Mohamed Salah", "mevki": "RW", "overall": 90},
                    {"ad": "Darwin Núñez", "mevki": "ST", "overall": 83},
                ],
            },
            {
                "id": "chelsea",
                "ad": "Chelsea",
                "kisaad": "CHE",
                "emoji": "🔵",
                "stadyum": "Stamford Bridge",
                "oyuncular": [
                    {"ad": "Robert Sánchez", "mevki": "GK", "overall": 82},
                    {"ad": "Levi Colwill", "mevki": "CB", "overall": 82},
                    {"ad": "Enzo Fernández", "mevki": "CM", "overall": 84},
                    {"ad": "Cole Palmer", "mevki": "CAM", "overall": 87},
                    {"ad": "Nicolas Jackson", "mevki": "ST", "overall": 82},
                ],
            },
        ],
    },
    "la_liga": {
        "id": "la_liga",
        "ad": "La Liga",
        "emoji": "🇪🇸",
        "takimlar": [
            {
                "id": "real_madrid",
                "ad": "Real Madrid",
                "kisaad": "RMA",
                "emoji": "⚪",
                "stadyum": "Santiago Bernabéu",
                "oyuncular": [
                    {"ad": "Thibaut Courtois", "mevki": "GK", "overall": 90},
                    {"ad": "Éder Militão", "mevki": "CB", "overall": 86},
                    {"ad": "Luka Modrić", "mevki": "CM", "overall": 87},
                    {"ad": "Jude Bellingham", "mevki": "CAM", "overall": 90},
                    {"ad": "Kylian Mbappé", "mevki": "ST", "overall": 94},
                ],
            },
            {
                "id": "barcelona",
                "ad": "Barcelona",
                "kisaad": "BAR",
                "emoji": "🔵🔴",
                "stadyum": "Spotify Camp Nou",
                "oyuncular": [
                    {"ad": "Marc-André ter Stegen", "mevki": "GK", "overall": 88},
                    {"ad": "Ronald Araújo", "mevki": "CB", "overall": 86},
                    {"ad": "Pedri", "mevki": "CM", "overall": 87},
                    {"ad": "Gavi", "mevki": "CM", "overall": 86},
                    {"ad": "Robert Lewandowski", "mevki": "ST", "overall": 88},
                ],
            },
            {
                "id": "atletico_madrid",
                "ad": "Atlético Madrid",
                "kisaad": "ATM",
                "emoji": "🔴⚪",
                "stadyum": "Cívitas Metropolitano",
                "oyuncular": [
                    {"ad": "Jan Oblak", "mevki": "GK", "overall": 88},
                    {"ad": "José Giménez", "mevki": "CB", "overall": 83},
                    {"ad": "Koke", "mevki": "CM", "overall": 82},
                    {"ad": "Antoine Griezmann", "mevki": "CAM", "overall": 86},
                    {"ad": "Álvaro Morata", "mevki": "ST", "overall": 82},
                ],
            },
        ],
    },
    "bundesliga": {
        "id": "bundesliga",
        "ad": "Bundesliga",
        "emoji": "🇩🇪",
        "takimlar": [
            {
                "id": "bayer_leverkusen",
                "ad": "Bayer Leverkusen",
                "kisaad": "LEV",
                "emoji": "🔴⚫",
                "stadyum": "BayArena",
                "oyuncular": [
                    {"ad": "Lukáš Hrádecký", "mevki": "GK", "overall": 84},
                    {"ad": "Jonathan Tah", "mevki": "CB", "overall": 85},
                    {"ad": "Granit Xhaka", "mevki": "CM", "overall": 84},
                    {"ad": "Florian Wirtz", "mevki": "CAM", "overall": 89},
                    {"ad": "Victor Boniface", "mevki": "ST", "overall": 84},
                ],
            },
            {
                "id": "bayern_munich",
                "ad": "Bayern München",
                "kisaad": "BAY",
                "emoji": "🔴",
                "stadyum": "Allianz Arena",
                "oyuncular": [
                    {"ad": "Manuel Neuer", "mevki": "GK", "overall": 88},
                    {"ad": "Dayot Upamecano", "mevki": "CB", "overall": 84},
                    {"ad": "Joshua Kimmich", "mevki": "CM", "overall": 88},
                    {"ad": "Jamal Musiala", "mevki": "CAM", "overall": 89},
                    {"ad": "Harry Kane", "mevki": "ST", "overall": 91},
                ],
            },
            {
                "id": "borussia_dortmund",
                "ad": "Borussia Dortmund",
                "kisaad": "BVB",
                "emoji": "🟡⚫",
                "stadyum": "Signal Iduna Park",
                "oyuncular": [
                    {"ad": "Gregor Kobel", "mevki": "GK", "overall": 85},
                    {"ad": "Nico Schlotterbeck", "mevki": "CB", "overall": 83},
                    {"ad": "Emre Can", "mevki": "CM", "overall": 81},
                    {"ad": "Julian Brandt", "mevki": "CAM", "overall": 83},
                    {"ad": "Serhou Guirassy", "mevki": "ST", "overall": 84},
                ],
            },
        ],
    },
}


def get_lig(lig_id: str) -> dict | None:
    return LIGLER.get(lig_id)


def get_takim(lig_id: str, takim_id: str) -> dict | None:
    lig = get_lig(lig_id)
    if not lig:
        return None
    for t in lig["takimlar"]:
        if t["id"] == takim_id:
            return t
    return None


def tum_takimlar() -> list[dict]:
    """Tüm liglerdeki tüm takımları düz liste olarak döndür."""
    sonuc = []
    for lig in LIGLER.values():
        for takim in lig["takimlar"]:
            sonuc.append({**takim, "lig_id": lig["id"], "lig_adi": lig["ad"]})
    return sonuc
