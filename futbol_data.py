# futbol_data.py: Test için 3 ligden 2-3 takım, her takımda 5 gerçek oyuncu

LIGLER = {
    "Premier League": [
        {"isim": "Manchester City", "oyuncular": [
            {"isim": "Erling Haaland",   "pozisyon": "Forvet",    "guc": 92},
            {"isim": "Kevin De Bruyne",  "pozisyon": "Orta Saha", "guc": 91},
            {"isim": "Ederson",          "pozisyon": "Kaleci",    "guc": 87},
            {"isim": "Phil Foden",       "pozisyon": "Orta Saha", "guc": 86},
            {"isim": "Kyle Walker",      "pozisyon": "Defans",    "guc": 85},
        ]},
        {"isim": "Arsenal", "oyuncular": [
            {"isim": "Bukayo Saka",      "pozisyon": "Forvet",    "guc": 87},
            {"isim": "Martin Odegaard",  "pozisyon": "Orta Saha", "guc": 86},
            {"isim": "David Raya",       "pozisyon": "Kaleci",    "guc": 83},
            {"isim": "William Saliba",   "pozisyon": "Defans",    "guc": 84},
            {"isim": "Gabriel Jesus",    "pozisyon": "Forvet",    "guc": 83},
        ]},
        {"isim": "Liverpool", "oyuncular": [
            {"isim": "Mohamed Salah",    "pozisyon": "Forvet",    "guc": 90},
            {"isim": "Virgil van Dijk",  "pozisyon": "Defans",    "guc": 88},
            {"isim": "Alisson Becker",   "pozisyon": "Kaleci",    "guc": 89},
            {"isim": "Trent Alexander",  "pozisyon": "Defans",    "guc": 85},
            {"isim": "Dominik Szoboszlai","pozisyon": "Orta Saha","guc": 84},
        ]},
    ],
    "La Liga": [
        {"isim": "Real Madrid", "oyuncular": [
            {"isim": "Jude Bellingham",  "pozisyon": "Orta Saha", "guc": 91},
            {"isim": "Vinicius Jr",      "pozisyon": "Forvet",    "guc": 90},
            {"isim": "Thibaut Courtois", "pozisyon": "Kaleci",    "guc": 90},
            {"isim": "Rodrygo Goes",     "pozisyon": "Forvet",    "guc": 84},
            {"isim": "Antonio Rudiger",  "pozisyon": "Defans",    "guc": 85},
        ]},
        {"isim": "Barcelona", "oyuncular": [
            {"isim": "Robert Lewandowski","pozisyon": "Forvet",   "guc": 89},
            {"isim": "Pedri",            "pozisyon": "Orta Saha", "guc": 86},
            {"isim": "Marc ter Stegen",  "pozisyon": "Kaleci",    "guc": 89},
            {"isim": "Frenkie de Jong",  "pozisyon": "Orta Saha", "guc": 85},
            {"isim": "Ronald Araujo",    "pozisyon": "Defans",    "guc": 84},
        ]},
        {"isim": "Atletico Madrid", "oyuncular": [
            {"isim": "Antoine Griezmann","pozisyon": "Forvet",    "guc": 87},
            {"isim": "Jan Oblak",        "pozisyon": "Kaleci",    "guc": 89},
            {"isim": "Marcos Llorente",  "pozisyon": "Orta Saha", "guc": 83},
            {"isim": "Jose Gimenez",     "pozisyon": "Defans",    "guc": 83},
            {"isim": "Alvaro Morata",    "pozisyon": "Forvet",    "guc": 82},
        ]},
    ],
    "Bundesliga": [
        {"isim": "Bayern Münih", "oyuncular": [
            {"isim": "Harry Kane",       "pozisyon": "Forvet",    "guc": 90},
            {"isim": "Jamal Musiala",    "pozisyon": "Orta Saha", "guc": 88},
            {"isim": "Manuel Neuer",     "pozisyon": "Kaleci",    "guc": 86},
            {"isim": "Leroy Sane",       "pozisyon": "Forvet",    "guc": 85},
            {"isim": "Joshua Kimmich",   "pozisyon": "Orta Saha", "guc": 87},
        ]},
        {"isim": "Borussia Dortmund", "oyuncular": [
            {"isim": "Gregor Kobel",     "pozisyon": "Kaleci",    "guc": 84},
            {"isim": "Karim Adeyemi",    "pozisyon": "Forvet",    "guc": 82},
            {"isim": "Emre Can",         "pozisyon": "Orta Saha", "guc": 81},
            {"isim": "Nico Schlotterbeck","pozisyon": "Defans",   "guc": 82},
            {"isim": "Julian Brandt",    "pozisyon": "Orta Saha", "guc": 83},
        ]},
    ],
}
