import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os,sys
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_path)

from main import app  # Assuming your FastAPI app is in a file named main.py
from src.metadata import MetadataAgent  # Import the MetadataAgent class

# Create a test client for the FastAPI app
client = TestClient(app)

@pytest.fixture
def mock_metadata_agent():
    with patch("main.MetadataAgent") as MockAgent:
        mock_instance = MockAgent.return_value
        yield mock_instance


def test_save_collection_success(mock_metadata_agent):
    # Mock the behavior of process for content and profile
    mock_metadata_agent.process.side_effect = [True, True]  # Mocked results for content and profile

    # Request payload
    request_payload = {
        "ids": [1,2,3,4,5]
    }

    # Make the POST request to the API
    response = client.post("/save_collection", json=request_payload)

    # Assertions
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["content"] == "Content Data processed successfully"
    assert response_data["profile"] == "Profile Data processed successfully"
    assert response_data["processed_ids"] == [1,2,3,4,5]


def test_save_collection_no_data(mock_metadata_agent):
    # Mock the behavior of process to return no data
    mock_metadata_agent.process.side_effect = [False, False]  # Mocked no results for content and profile

    # Request payload
    request_payload = {
        "ids": [1873]
    }

    # Make the POST request to the API
    response = client.post("/save_collection", json=request_payload)

    # Assertions
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["content"] == "No content data found"
    assert response_data["profile"] == "No profile data found"
    assert response_data["processed_ids"] == []

def test_save_collection_exception(mock_metadata_agent):
    # Mock the behavior of process to raise an exception
    mock_metadata_agent.process.side_effect = Exception("Mocked database error")

    # Request payload
    request_payload = {
        "ids": [1, 2, 3]
    }

    # Make the POST request to the API
    response = client.post("/save_collection", json=request_payload)
    
    # Assertions
    assert response.status_code == 500
    response_data = response.json()
    assert "Database error" in response_data["detail"]
