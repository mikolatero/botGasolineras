from __future__ import annotations

from app.integrations.postal_code_api import PostalCodeResolution
from app.repositories.stations import StationsRepository
from app.services.search_service import SearchFilters, SearchService
from app.services.sync_service import SyncService


class FakeDatasetClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def fetch_dataset(self) -> dict:
        return self.payload


class FakePostalCodeClient:
    def __init__(self, resolutions: dict[str, str | None]) -> None:
        self.enabled = True
        self.batch_size = 100
        self.resolutions = resolutions

    async def resolve_postal_codes(self, stations):
        return {
            station_id: PostalCodeResolution(postal_code=self.resolutions.get(station_id), checked=True)
            for station_id, _, _ in stations
        }


def _payload_with_wrong_postal_code() -> dict:
    return {
        "Fecha": "27/03/2026 08:30",
        "ListaEESSPrecio": [
            {
                "IDEESS": "55555",
                "C.P.": "30520",
                "Dirección": "CALLE ECUADOR 4-6 POLIGONO INDUSTRIAL OESTE, 4",
                "Horario": "L-V: 06:30-21:30; S: 07:00-15:00",
                "Latitud": "37,972000",
                "Localidad": "Alcantarilla",
                "Longitud_x0020__x0028_WGS84_x0029_": "-1,230000",
                "Margen": "D",
                "Municipio": "Alcantarilla",
                "Provincia": "Murcia",
                "Remisión": "dm",
                "Rótulo": "CENTRO DIESEL COMBUSTIBLES MURCIANOS",
                "Tipo_x0020_Venta": "P",
                "IDMunicipio": "13",
                "IDProvincia": "30",
                "IDCCAA": "14",
                "Precio_x0020_Gasoleo_x0020_A": "1,399",
            }
        ],
    }


async def test_sync_keeps_official_postal_code_and_uses_resolved_one_for_search(session_factory) -> None:
    async with session_factory() as session:
        service = SyncService(
            session=session,
            client=FakeDatasetClient(_payload_with_wrong_postal_code()),
            postal_code_client=FakePostalCodeClient({"55555": "30820"}),
        )
        result = await service.run_sync()
        assert result["postal_codes_resolved"] == 1
        assert result["postal_codes_corrected"] == 1

    async with session_factory() as session:
        station = await StationsRepository(session).get_by_ideess("55555")
        assert station is not None
        assert station.postal_code == "30520"
        assert station.postal_code_resolved == "30820"
        assert station.effective_postal_code == "30820"

    async with session_factory() as session:
        service = SearchService(StationsRepository(session))
        stations, total = await service.search(SearchFilters(postal_code="30820"), page=1, page_size=10)
        assert total == 1
        assert len(stations) == 1
        assert stations[0].ideess == "55555"

    async with session_factory() as session:
        service = SearchService(StationsRepository(session))
        stations, total = await service.search(SearchFilters(postal_code="30520"), page=1, page_size=10)
        assert total == 0
        assert stations == []
