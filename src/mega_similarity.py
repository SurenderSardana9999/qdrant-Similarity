from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import os
import ast
import requests
import logging

# model = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)


class MegaSimilarityAgent:
    def __init__(self):
        self.qdrant_client = QdrantClient(url=os.getenv('QDRANT_HOST'), api_key=os.getenv('QDRANT_API_KEY'))
        self.embedding_url = os.getenv('EMBEDDING_MODEL_URL')
        self.embedding_model_name = os.getenv('EMBEDDING_MODEL_NAME')

    def generate_embedding(self, text):
        """
        Generate embedding for a given text using the embedding model.

        :param text: Text to embed.
        :return: List representing the embedding vector.
        """
        
        # embed_text = [f'search_query: {text}']
        # embedded_text = model.encode(embed_text)
        
        # embedded_text = embedded_text.flatten()

        embed_text = requests.get(self.embedding_url, params={"promt": text, "model_name":self.embedding_model_name})
        embedded_text = ast.literal_eval(embed_text.content.decode("utf-8"))
        
        return embedded_text
    
    def query(self, query_text, collection_name, threshold, top_k, input_video_id=None, user_handle=None):
        """
        Perform a similarity search on the specified collection.

        :param query_text: The query text for which to find similar vectors.
        :param collection_name: The name of the collection to search in.
        :param threshold: Minimum similarity score for results.
        :param top_k: Number of top results to retrieve.
        :return: List of matching payloads.
        """
        try:
            # Generate query embedding
            embedding = self.generate_embedding(query_text)
            
            # Perform search in Qdrant
            search_results = self.qdrant_client.search(
                collection_name=collection_name,
                query_vector=embedding,
                limit=top_k,
                with_payload=True
            )
            
            # Log matches with scores
            for result in search_results:
                match_id = result.payload.get('id', 'Unknown')
                score = result.score
                logging.info(f"Match ID: {match_id}, Score: {score}")

            if input_video_id:
                 # Filter results based on conditions and extract payloads
                matches = [
                    {**result.payload, 'similarity_score':result.score} for result in search_results
                    if result.score >= threshold and result.payload.get('video_id') != str(input_video_id)
                ]
                            
            else:
                matches = [
                    {**result.payload, 'similarity_score':result.score} for result in search_results
                    if result.score >= threshold and result.payload.get('user_handle') != user_handle
                ]
                
            return matches
        
        
        except Exception as e:
            logging.error(f"Error during similarity search: {str(e)}")
            raise

