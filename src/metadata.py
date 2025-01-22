import mysql.connector
import requests
from datetime import datetime
import ast
import os
import json
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct,Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
import logging

#model = SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)


load_dotenv()

class MetadataAgent:
    def __init__(self):
        """
        Initialize the MetadataAgent class.
        """
        self.qdrant_client = QdrantClient(url=os.getenv('QDRANT_HOST'), api_key=os.getenv('QDRANT_API_KEY'))
        self.embedding_url = os.getenv('EMBEDDING_MODEL_URL')
        self.embedding_model_name = os.getenv('EMBEDDING_MODEL_NAME')
        
    def fetch_data(self, query):
        """
        Fetch data from MySQL.

        :param query: SQL query to execute.
        :return: List of rows as dictionaries.
        """
        # Establish connection with unpacked configuration
        conn = mysql.connector.connect(
            host=os.getenv("HOST"),
            user=os.getenv("USERDB"),
            password=os.getenv("PASSWORD"),
            database=os.getenv("DATABASE")
        )
        cursor = conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]  # Get column names
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not data:
            logging.info("No records found for the given query.")
            return None
        
        # Convert tuples to dictionaries
        data_dict = [dict(zip(columns, row)) for row in data]
        
        return data_dict
    
    def generate_embedding(self, text):
        """
        Generate embedding for a given text using customized embedding model.

        :param text: Text to embed.
        :return: List representing the embedding vector.
        """
        # embed_text = [f'search_query: {text}']
        # embedded_text = model.encode(embed_text)
        
        # embedded_text = embedded_text.flatten()

        embed_text = requests.get(self.embedding_url, params={"promt": text, "model_name":self.embedding_model_name})
        embedded_text = ast.literal_eval(embed_text.content.decode("utf-8"))
        
        return embedded_text
    
    def convert_timestamp(self, timestamp):
        """
        Convert a timestamp to a string format.
        
        :param timestamp: The timestamp to convert.
        :return: Formatted string.
        """
        try:
            # If the timestamp is in datetime object, convert it to string
            formatted_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            return formatted_timestamp
        except ValueError:
            # If the timestamp cannot be parsed, return it as is
            return timestamp
    
    def upsertion(self, data, mode):
        """
        Upsert data into Qdrant.

        :param data: List of dictionaries containing the data.
        """
        
        for row in data:
            logging.info(f"Processing video_id: {row['video_id']} for mode: {mode}")  # Log the ID

            if 'video_posted_timestamp' in row:
                row['video_posted_timestamp'] = self.convert_timestamp(row['video_posted_timestamp'])

            if mode == 'content':
            # Generate embedding for the 'video_summary' column
                embedding = self.generate_embedding(row['video_summary'])
                collection_name = os.getenv("CONTENT_COLLECTION_NAME")
                
            elif mode == 'profile':
                # Combine theme fields into a single string for embedding
                themes = " ".join([
                    row.get("topic_category", ""),
                    row.get("relates_to", ""),
                    row.get("purpose", ""),
                    row.get("execution_method", ""),
                ])
                embedding = self.generate_embedding(themes)
                collection_name = os.getenv("PROFILE_COLLECTION_NAME")

                

            if(mode == 'content' or(mode == 'profile' and self._isVideoCatExist(row)==False)):
                # Prepare the payload
                payload = {k: v for k, v in row.items()}

                #Add the point to the list
                point = PointStruct(
                        id=row['id'],
                        vector=embedding,
                        payload=payload
                )

                # Upsert points into the Qdrant collection
                self.qdrant_client.upsert(
                    collection_name=collection_name,
                    points=[point]
                )
            
                logging.info(f"Upserted video_id: {row['video_id']} for mode: {mode}")  # Log the ID that was just upserted
            else:
                logging.info(f"Already exist for Upserted video_id: {row['video_id']} for mode: {mode}") 
        logging.info(f"Upsertion completed for all provided IDs in mode: {mode}")

        
    def process(self, query, mode):
        """
        Complete process: fetch data, generate embeddings, and upsert into Vector Database.

        :param query: SQL query to fetch data.
        :param mode: Determines the type of data (content or profile).
        """
        logging.info(f"Fetching data from MySQL for mode: {mode}")
        data = self.fetch_data(query)
        if data:
            logging.info(f"Fetched {len(data)} rows for mode: {mode}. Generating embeddings and upserting to Vector Database...")
            self.upsertion(data, mode)
            logging.info(f"Process completed successfully for mode: {mode}!")
            return True  # Data was processed successfully
        else:
            logging.info("No data fetched.")
            return False  # No data fetched

    def _isVideoCatExist(self,row):
        video_id=row['video_id']
        topic_category=row['topic_category']

        logging.info(f"inside _isVideoCatExist _isVideoCatExist check for {row['video_id']}  and {row['topic_category']} ")
        
        themes = " ".join([
            row.get("topic_category", ""),
                        row.get("relates_to", ""),
                        row.get("purpose", ""),
                        row.get("execution_method", ""),
                    ])

        collection_name = os.getenv("PROFILE_COLLECTION_NAME")
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="video_id",
                    match=MatchValue(value=video_id)
                ),
                FieldCondition(
                    key="topic_category",
                    match=MatchValue(value=topic_category)
                )
            ]
        )

        results=self.qdrant_client.search(
            collection_name=collection_name,
            query_vector=self.generate_embedding(themes), 
            query_filter=query_filter,
            limit=10  
        )
        return len(results)>0
    