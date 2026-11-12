import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.samples.sample_generator import generate_samples
from app.config import SAMPLES_DIR

@pytest.fixture(scope="session")
def client():
    # Ensure samples exist
    generate_samples(SAMPLES_DIR)
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="session")
def sample_kml_bytes():
    kml_path = SAMPLES_DIR / "sample_survey.kml"
    if not kml_path.exists():
        generate_samples(SAMPLES_DIR)
    return kml_path.read_bytes()

@pytest.fixture(scope="session")
def sample_shp_zip_bytes():
    shp_path = SAMPLES_DIR / "sample_shapefile.zip"
    if not shp_path.exists():
        generate_samples(SAMPLES_DIR)
    return shp_path.read_bytes()

