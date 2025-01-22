import pytest
from unittest.mock import patch, MagicMock

import os,sys
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_path)

import main
from main import app

from fastapi.testclient import TestClient
#from fastapi import HTTPException
#import os

client = TestClient(app)

# Mock data for the request
mock_request_payload = {
    "user_handle": "melayubersatu1"
}
mock_request_notFound_payload = {
    "user_handle": "test_user"
}

# Mock response for the database query
mock_profile_data = [
    {
        "theme_main": "Malaysian Politics",
        "theme_1": "",
        "theme_2": "",
        "theme_3": "Malaysian Politics",
        "theme_4": "Malaysian Politics"
    }
]

# Mock response for the similarity agent query
mock_similarity_results = [{'id': 1874, 'user_handle': 'beritapertiwi', 'topic_category': 'Politics', 'relates_to': 'Racism', 'purpose': 'Discrimination', 'execution_method': 'Speech', 'similarity_score': 0.8632616}, {'id': 50, 'user_handle': 'suhaizan_kayat', 'topic_category': 'Social Issues', 'relates_to': 'Racism', 'purpose': 'Discrimination', 'execution_method': 'Speech', 'similarity_score': 0.8219864}, {'id': 4, 'user_handle': 'haizolawang', 'topic_category': 'Social Justice', 'relates_to': 'Racism', 'purpose': 'Discrimination', 'execution_method': 'Verbal', 'similarity_score': 0.78814125}, {'id': 224, 'user_handle': 'mayaloy27', 'topic_category': 'Others', 'relates_to': 'Racism', 'purpose': 'Discrimination', 'execution_method': 'Conversation', 'similarity_score': 0.7731454}, {'id': 38, 'user_handle': 'alexander9377vdd', 'topic_category': 'Social Issues', 'relates_to': 'Racism', 'purpose': 'Discrimination', 'execution_method': 'Verbal', 'similarity_score': 0.76872987}]


@patch("src.metadata")
@patch("src.mega_similarity")
@patch("os.getenv")
def test_query_profile(mock_getenv, MockMegaSimilarityAgent, MockMetadataAgent):
    # Mock environment variables
    mock_getenv.side_effect = lambda key: {
        "Threshold": "0.5",
        "Top_k": "5",
        "DATABASE": "mcmc_business_agent",
        "CONTENT_TABLE": "ba_content_data_asset",
        "PROFILE_COLLECTION_NAME": "dev.limpopo.profile_collection",
        "EMBEDDING_MODEL_URL":"http://195.242.13.111:9001/embedPromt",
        "EMBEDDING_MODEL_NAME":"nomic-ai/nomic-embed-text-v1:search_query",
        "CONTENT_COLLECTION_NAME":"dev.limpopo.content_collection",
        "PROFILE_COLLECTION_NAME":"dev.limpopo.profile_collection",
        "QDRANT_HOST":"http://52.187.106.203:6333",
        "QDRANT_API_KEY":"userdata2024",
        "USERDB":"AdaDB",
        "PASSWORD":"Admin@2024",
        "HOST":"20.184.17.187"
    }.get(key)

    # Mock MetadataAgent
    mock_metadata_agent_instance = MockMetadataAgent.return_value
    mock_metadata_agent_instance.fetch_data.return_value = mock_profile_data

    # Mock MegaSimilarityAgent
    mock_similarity_agent_instance = MockMegaSimilarityAgent.return_value
    mock_similarity_agent_instance.query.return_value = mock_similarity_results
    # Send POST request to the endpoint
    response = client.post("/query_profile", json=mock_request_payload)
    
    # Assertions
    assert response.status_code == 200
   
    assert response.json() == {"matches": mock_similarity_results}

    

def test_query_profile_user_not_found():
    with patch("src.metadata") as MockMetadataAgent:
        mock_metadata_agent_instance = MockMetadataAgent.return_value
        mock_metadata_agent_instance.fetch_data.return_value = []  # No data found

        response = client.post("/query_profile", json=mock_request_notFound_payload)

        assert response.status_code == 500
        assert response.json() == {"detail": "Profile similarity query error: 404: User Name test_user not found in the profile table."}

# def test_query_profile_internal_server_error():
#     with patch("src.MetadataAgent", side_effect=Exception("Database error")) as MockMetadataAgent:
#         response = client.post("/query_profile", json=mock_request_payload)

#         assert response.status_code == 500
#         assert response.json() == {"detail": "Profile similarity query error: Database error"}
