from ..core.chambers import LOWER
from ..core.structure import Country, Territory

# Spanish political parties
PP = "PP"
PSOE = "PSOE"
VOX = "VOX"
FRENTE = "Frente Amplio"
PODEMOS = "Podemos"
ERC = "ERC"
PNV = "PNV"
JUNTS = "Junts"

# Spanish Autonomous Communities
ANDALUCIA = "Andalucía"
ARAGON = "Aragón"
ASTURIAS = "Asturias"
BALEARES = "Islas Baleares"
CANARIAS = "Canarias"
CANTABRIA = "Cantabria"
CASTILLA_LA_MANCHA = "Castilla-La Mancha"
CASTILLA_Y_LEON = "Castilla y León"
CATALUNYA = "Catalunya"
CEUTA = "Ceuta"
COMUNIDAD_DE_MADRID = "Comunidad de Madrid"
COMUNIDAD_VALENCIANA = "Comunidad Valenciana"
EXTREMADURA = "Extremadura"
GALICIA = "Galicia"
LA_RIOJA = "La Rioja"
MELILLA = "Melilla"
PAIS_VASCO = "País Vasco"
MURCIA = "Región de Murcia"
NAVARRA = "Navarra"

# Spanish provinces
# Andalucia
SEVILLA = "Sevilla"
CADIZ = "Cádiz"
CORDOBA = "Córdoba"
GRANADA = "Granada"
HUELVA = "Huelva"
JAEN = "Jaén"
MALAGA = "Málaga"
ALMERIA = "Almería"
# Aragon
HUESCA = "Huesca"
TERUEL = "Teruel"
ZARAGOZA = "Zaragoza"
# Canarias
LAS_PALMAS = "Las Palmas"
SANTA_CRUZ_DE_TENERIFE = "Santa Cruz de Tenerife"
# Castilla la Mancha
ALBACETE = "Albacete"
CIUDAD_REAL = "Ciudad Real"
CUENCA = "Cuenca"
GUADALAJARA = "Guadalajara"
TOLEDO = "Toledo"
# Castilla y León
AVILA = "Ávila"
BURGOS = "Burgos"
LEON = "León"
PALENCIA = "Palencia"
SALAMANCA = "Salamanca"
SEGOVIA = "Segovia"
SORIA = "Soria"
VALLADOLID = "Valladolid"
ZAMORA = "Zamora"
# Catalunya
BARCELONA = "Barcelona"
GIRONA = "Girona"
LLEIDA = "Lleida"
TARRAGONA = "Tarragona"
# Valencian Community
ALICANTE = "Alicante"
CASTELLON = "Castellón"
VALENCIA = "Valencia"
# Extremadura
BADAJOZ = "Badajoz"
CACERES = "Cáceres"
# Galicia
A_CORUNA = "A Coruña"
LUGO = "Lugo"
OURENSE = "Ourense"
PONTEVEDRA = "Pontevedra"
# Pais Vasco
ARABA = "Araba"
GIPUZKOA = "Gipuzkoa"
BIZKAIA = "Bizkaia"

COUNTRY_NAME = "Spain"
LEVEL_NAMES = ("Autonomous Community", "Province", "Island")


def _province(name: str, congress: int) -> Territory:
    return Territory(name, seats={LOWER: congress})


def _region(name: str, *provinces: Territory) -> Territory:
    return Territory(name, children=tuple(provinces))


# TODO: add upper house (Senate) seats. Mainland provinces are districts with
# 4 seats; in the islands the district is each island (level 3), so those
# provinces get island children with `seats={UPPER: n}` instead of seats
# on the province itself.
COUNTRY = Country(
    name=COUNTRY_NAME,
    level_names=LEVEL_NAMES,
    expected_seats={LOWER: 350},
    regions=(
        _region(ANDALUCIA,
                _province(SEVILLA, 12), _province(CADIZ, 8),
                _province(CORDOBA, 6), _province(GRANADA, 7),
                _province(HUELVA, 5), _province(JAEN, 5),
                _province(MALAGA, 11), _province(ALMERIA, 6)),
        _region(ARAGON,
                _province(HUESCA, 3), _province(TERUEL, 3),
                _province(ZARAGOZA, 7)),
        _region(ASTURIAS, _province(ASTURIAS, 7)),
        _region(BALEARES, _province(BALEARES, 8)),
        _region(CANARIAS,
                _province(LAS_PALMAS, 8),
                _province(SANTA_CRUZ_DE_TENERIFE, 7)),
        _region(CANTABRIA, _province(CANTABRIA, 5)),
        _region(CASTILLA_LA_MANCHA,
                _province(ALBACETE, 4), _province(CIUDAD_REAL, 5),
                _province(CUENCA, 3), _province(GUADALAJARA, 3),
                _province(TOLEDO, 6)),
        _region(CASTILLA_Y_LEON,
                _province(AVILA, 3), _province(BURGOS, 4),
                _province(LEON, 4), _province(PALENCIA, 3),
                _province(SALAMANCA, 4), _province(SEGOVIA, 3),
                _province(SORIA, 2), _province(VALLADOLID, 5),
                _province(ZAMORA, 3)),
        _region(CATALUNYA,
                _province(BARCELONA, 32), _province(GIRONA, 6),
                _province(LLEIDA, 4), _province(TARRAGONA, 6)),
        _region(CEUTA, _province(CEUTA, 1)),
        _region(COMUNIDAD_DE_MADRID, _province(COMUNIDAD_DE_MADRID, 38)),
        _region(COMUNIDAD_VALENCIANA,
                _province(ALICANTE, 12), _province(CASTELLON, 5),
                _province(VALENCIA, 16)),
        _region(EXTREMADURA,
                _province(BADAJOZ, 5), _province(CACERES, 4)),
        _region(GALICIA,
                _province(A_CORUNA, 8), _province(LUGO, 4),
                _province(OURENSE, 4), _province(PONTEVEDRA, 7)),
        _region(LA_RIOJA, _province(LA_RIOJA, 4)),
        _region(MELILLA, _province(MELILLA, 1)),
        _region(PAIS_VASCO,
                _province(ARABA, 4), _province(GIPUZKOA, 6),
                _province(BIZKAIA, 8)),
        _region(MURCIA, _province(MURCIA, 10)),
        _region(NAVARRA, _province(NAVARRA, 5)),
    ),
)
COUNTRY.validate()   