# import pytest
# from fastapi.testclient import TestClient

# from app.main import app

# pytestmark = pytest.mark.usefixtures("quran_db")

# client = TestClient(app)


# def test_list_surahs():
#     response = client.get("/surahs")
#     assert response.status_code == 200
#     surahs = response.json()
#     assert [s["id"] for s in surahs] == list(range(1, 115))
#     assert sum(s["aya_count"] for s in surahs) == 6236
#     assert surahs[18] == {
#         "id": 19,
#         "name_arabic": "مريم",
#         "name_transliterated": "Maryam",
#         "name_english": "Mary",
#         "revelation_type": "meccan",
#         "aya_count": 98,
#     }
