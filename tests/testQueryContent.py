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
    "video_id": 7348693858496122120
}
mock_request_notFound_payload = {
    "video_id": 121333
}



# Mock response for the similarity agent query
mock_similarity_results = [{'id': 38, 'video_summary': 'The video and the audio transcript do not provide enough context for me to provide a summary or description of the content. The text appears to be in Bahasa Melayu, but without additional context, it is not clear what the content of the video is about. If you have specific questions or need information about the content depicted, please provide more details or clarify the context of the video.', 'video_id': '7391011210704981264', 'video_posted_timestamp': '2024-07-13 06:58:27', 'video_source': 'TikTok', 'sub_category': 'race', 'risk_status': 'low', 'similarity_score': 0.7202374}, {'id': 96, 'video_summary': "The video is a short speech delivered in Indonesian, which includes various topics like the significance of being useful to one's nation, the importance of being a useful and helpful youth in every aspect, and the encouragement to serve the nation. There is no direct visual content related to the text but it appears to be a recording of a speaker addressing an audience, possibly at a social or political event based on the context of the speech.", 'video_id': '7360883647089478919', 'video_posted_timestamp': '2024-04-23 02:28:05', 'video_source': 'TikTok', 'sub_category': 'religion', 'risk_status': 'low', 'similarity_score': 0.70440745}, {'id': 83, 'video_summary': 'The video is discussing the history of Islam and its influence on the Malay world, particularly in the context of early Malay traditions and practices. The speaker suggests that Islam was introduced to the Malay world through the Arab traders, but there were already Malay settlements in the region through which these traders passed. The presence of elephants in Malay culture, which were important for both transportation and royal ceremonies, indicates that the Malay peninsula was a center of trade, culture, and power where different cultures met. The speaker points out that even before Islam arrived, Malay culture had a rich mythology and narrative tradition, including stories of figures such as Nabi Ibrahim. She also emphasizes that the introduction of Islam did not lead to a complete transformation of Malay culture and traditions, but rather integrated them into the new religion. It is worth noting that the transcript provided is a translation of the spoken text, so some nuances may be lost in translation.', 'video_id': '7400301206129741064', 'video_posted_timestamp': '2024-08-07 07:48:17', 'video_source': 'TikTok', 'sub_category': 'religion', 'risk_status': 'low', 'similarity_score': 0.6969377}, {'id': 11, 'video_summary': 'The video appears to be from a speech or lecture discussing historical and cultural topics. The speaker mentions that in the past, there were two land masses in the region known as Nusantara: one called Malayu and the other Jawa. These lands were independently studied by people of different backgrounds, including a person who wrote about psychoanalysis and another who wrote about Melek Acipilago and Jawa Acipilago, using the terms Malayu and Jawa.\n\nThe speaker explains that Nusantara consists of various landmasses that are complementary to the mainland, Sumatra. They identify the Malay Peninsula (Mekah) and Jawa as the main landmasses and indicate that Malayu (Sumatra) was the first to accept Islam. The speaker mentions the ancient kingdom of Srivijaya, which was established in about 650 AD, and highlights the fact that the Arabs sent envoys to the kingdom of Srivijaya. The envoys were sent by Umar bin Abdul Aziz and Muawiyah during their respective reigns. The content of the video seems to be a historical explanation, likely of the Malay and Indonesian region, connecting elements of culture and trade with the arrival of Islam.', 'video_id': '7399490358071004433', 'video_posted_timestamp': '2024-08-05 03:21:52', 'video_source': 'TikTok', 'sub_category': 'religion', 'risk_status': 'low', 'similarity_score': 0.6860858}]


@patch("src.metadata")
@patch("src.mega_similarity")
@patch("os.getenv")
def test_query_content(mock_getenv, MockMegaSimilarityAgent, MockMetadataAgent):
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
    mock_metadata_agent_instance.fetch_data.return_value = mock_similarity_results

    # Mock MegaSimilarityAgent
    mock_similarity_agent_instance = MockMegaSimilarityAgent.return_value
    mock_similarity_agent_instance.query.return_value = mock_similarity_results
    # Send POST request to the endpoint
    response = client.post("/query_content", json=mock_request_payload)
    # Assertions
    assert response.status_code == 200  
    assert response.json() == {"matches": mock_similarity_results}


def test_query_content_video_not_found():
    with patch("src.metadata") as MockMetadataAgent:
        mock_metadata_agent_instance = MockMetadataAgent.return_value
        mock_metadata_agent_instance.fetch_data.return_value = []  # No data found

        response = client.post("/query_content", json=mock_request_notFound_payload)
  
        assert response.status_code == 500
        assert response.json() == {"detail": "Content similarity query error: 404: Video ID 121333 not found in the content table."}

# def test_query_profile_internal_server_error():
#     with patch("src.MetadataAgent", side_effect=Exception("Database error")) as MockMetadataAgent:
#         response = client.post("/query_profile", json=mock_request_payload)

#         assert response.status_code == 500
#         assert response.json() == {"detail": "Profile similarity query error: Database error"}
