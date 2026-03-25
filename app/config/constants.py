from __future__ import annotations

FUEL_DEFINITIONS: list[dict[str, object]] = [
    {"id": 1, "code": "gasoleo_a", "name": "Gasoleo A", "dataset_key": "Precio_x0020_Gasoleo_x0020_A", "order": 10},
    {
        "id": 2,
        "code": "gasoleo_premium",
        "name": "Gasoleo Premium",
        "dataset_key": "Precio_x0020_Gasoleo_x0020_Premium",
        "order": 20,
    },
    {"id": 3, "code": "gasoleo_b", "name": "Gasoleo B", "dataset_key": "Precio_x0020_Gasoleo_x0020_B", "order": 30},
    {
        "id": 4,
        "code": "gasolina_95_e5",
        "name": "Gasolina 95 E5",
        "dataset_key": "Precio_x0020_Gasolina_x0020_95_x0020_E5",
        "order": 40,
    },
    {
        "id": 5,
        "code": "gasolina_95_premium",
        "name": "Gasolina 95 E5 Premium",
        "dataset_key": "Precio_x0020_Gasolina_x0020_95_x0020_E5_x0020_Premium",
        "order": 50,
    },
    {
        "id": 6,
        "code": "gasolina_98_e5",
        "name": "Gasolina 98 E5",
        "dataset_key": "Precio_x0020_Gasolina_x0020_98_x0020_E5",
        "order": 60,
    },
    {
        "id": 7,
        "code": "gasolina_95_e10",
        "name": "Gasolina 95 E10",
        "dataset_key": "Precio_x0020_Gasolina_x0020_95_x0020_E10",
        "order": 70,
    },
    {
        "id": 8,
        "code": "gasolina_98_e10",
        "name": "Gasolina 98 E10",
        "dataset_key": "Precio_x0020_Gasolina_x0020_98_x0020_E10",
        "order": 80,
    },
    {"id": 9, "code": "glp", "name": "GLP", "dataset_key": "Precio_x0020_Gases_x0020_licuados_x0020_del_x0020_petr\u00f3leo", "order": 90},
    {"id": 10, "code": "gnc", "name": "GNC", "dataset_key": "Precio_x0020_Gas_x0020_Natural_x0020_Comprimido", "order": 100},
    {"id": 11, "code": "gnl", "name": "GNL", "dataset_key": "Precio_x0020_Gas_x0020_Natural_x0020_Licuado", "order": 110},
    {"id": 12, "code": "adblue", "name": "AdBlue", "dataset_key": "Precio_x0020_Adblue", "order": 120},
    {
        "id": 13,
        "code": "diesel_renovable",
        "name": "Diesel Renovable",
        "dataset_key": "Precio_x0020_Di\u00e9sel_x0020_Renovable",
        "order": 130,
    },
    {
        "id": 14,
        "code": "gasolina_renovable",
        "name": "Gasolina Renovable",
        "dataset_key": "Precio_x0020_Gasolina_x0020_Renovable",
        "order": 140,
    },
]

FUEL_BY_DATASET_KEY = {item["dataset_key"]: item for item in FUEL_DEFINITIONS}
FUEL_BY_ID = {int(item["id"]): item for item in FUEL_DEFINITIONS}
FUEL_BY_CODE = {str(item["code"]): item for item in FUEL_DEFINITIONS}

SUPPORTED_PRICE_KEYS = tuple(FUEL_BY_DATASET_KEY.keys())

