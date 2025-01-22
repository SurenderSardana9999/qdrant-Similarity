from fastapi import FastAPI, Response,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
from pydantic import BaseModel
from typing import List
from src.metadata import MetadataAgent
from src.mega_similarity import MegaSimilarityAgent
import os
import logging
from enum import Enum

load_dotenv()

# Input models

class requestType(str, Enum):
    video = "video"
    profile = "profile"

class IDRequest(BaseModel):
    video_ids: List[int]
    
class ContentSimilarityRequest(BaseModel):
    video_id: int
    user_handle: str
    searchType:requestType
    
class ProfileSimilarityRequest(BaseModel):
    user_handle: str
     

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    debug=False,
    title="Limpopo",
    summary="To find similar content and profiles",
    description="""
        1) Communicating with the Business Agent to check for any new content.
        2) Vectorizing the new content, transforming it into numerical vectors.
        3) Performing a similarity search using the vectorized content, matching it against user profiles or other content for recommendations or categorization.    """,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root(response: Response) -> dict[str, str]:
    """The function sets response headers for cache control and CORS, and returns a message indicating that
    the Limpopo Agent is ready.

    :param response: The `response` parameter in the `root` function is an object that represents the
    HTTP response that will be sent back to the client. In this case, the code is setting various
    headers on the response object before returning a JSON response with the message "Limpopo is
    Ready!"\n
    :type response: Response
    :return: a dictionary with the key "Limpopo" and the value "Limpopo is Ready!".
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = "0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"

    return {"Limpopo": "Limpopo is Ready!"}

@app.post("/save_collection")
def save_collection(request: IDRequest):
    try:
        metadata_agent = MetadataAgent()
        id_str = ",".join(map(str, request.video_ids))  # Convert list of IDs to a comma-separated string
        
        #Content Query
        content_query = f"""
            SELECT id, video_id,video_summary, video_posted_timestamp, video_source, sub_category, risk_status,video_screenshot_url as picture 
            FROM {os.getenv('DATABASE')}.{os.getenv('CONTENT_TABLE')} 
            WHERE video_id IN ({id_str})
        """
        #Profile Query
        profile_query = f"""
            SELECT a.id, user_handle,a.video_id,
					IFNULL(c.category_name, '') AS topic_category,
                   IFNULL(a.relates_to, '') AS relates_to,
                   IFNULL(a.purpose, '') AS purpose,
                   IFNULL(a.execution_method, '') AS execution_method ,
                   b.creator_photo_link as picture
            FROM {os.getenv('DATABASE')}.{os.getenv('TOPIC_TABLE') } as a 
            join {os.getenv('DATABASE_MKT')}.{os.getenv('BIAS_TABLE') } as b 
            join {os.getenv('DATABASE_MKT')}.{os.getenv('CATEGORY_TABLE') } as c 
            on a.video_id=b.video_id
            and a.category_id=c.id
            WHERE a.video_id IN ({id_str})   
            """ 
        print(profile_query)
        # Process content data    
        content_data = metadata_agent.process(content_query, mode='content')
        
        # Process profile data    
        profile_data = metadata_agent.process(profile_query,mode='profile')
    
        response_message = {
            "content": "Content Data processed successfully" if content_data else "No content data found",
            "profile": "Profile Data processed successfully" if profile_data else "No profile data found",
            "processed_ids": request.video_ids if content_data or profile_data else []
        }
        
        return response_message

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")



@app.post('/query_content')
def query_content(request: ContentSimilarityRequest):
    try:
        metadata_agent = MetadataAgent()
        mega_similarity_agent = MegaSimilarityAgent()
        threshold = float(os.getenv('Threshold'))
        top_k =int(os.getenv('Top_k'))
        content_query=""
        if(request.searchType==requestType.video):
            # SQL query to fetch video_summary for the given video_id
            content_query = f"""
            SELECT video_summary 
            FROM {os.getenv("DATABASE")}.{os.getenv('CONTENT_TABLE')}
            WHERE video_id = {request.video_id}
            """
        elif(request.searchType==requestType.profile):
             content_query = f"""
            SELECT IFNULL(topic_category, '') AS topic_category, 
                   IFNULL(relates_to, '') AS relates_to, 
                   IFNULL(purpose, '') AS purpose, 
                   IFNULL(execution_method, '') AS execution_method
            FROM {os.getenv('DATABASE')}.{os.getenv('CONTENT_TABLE')} 
            WHERE user_handle = '{request.user_handle}'
            order by id desc limit 1 
            """

        # Fetch video_summary
        content_data = metadata_agent.fetch_data(content_query)
        if not content_data:
            if(request.searchType==requestType.video):
                raise HTTPException(status_code=404, detail=f"Video ID {request.video_id} not found in the content table.")
            elif(request.searchType==requestType.profile):
                raise HTTPException(status_code=404, detail=f"User Name {request.user_handle} not found in the profile table.")

        
        if(request.searchType==requestType.video):
            # Extract video_summary for embedding generation
            video_summary = content_data[0]["video_summary"]
            logging.info({'Video Summary': video_summary})

        elif(request.searchType==requestType.profile):
                # Extract themes for embedding generation
            themes = " ".join([
                content_data[-1]["topic_category"],
                content_data[-1]["relates_to"],
                content_data[-1]["purpose"],
                content_data[-1]["execution_method"]
            ]).strip()
            logging.info({'Themes': themes})         
        # Perform similarity query
        results = mega_similarity_agent.query(
                query_text=video_summary if request.searchType==requestType.video else themes,
                collection_name=os.getenv("CONTENT_COLLECTION_NAME") if request.searchType=="video" else os.getenv("PROFILE_COLLECTION_NAME"),
                threshold=threshold,
                top_k=top_k,
                input_video_id=request.video_id,
                user_handle=request.user_handle, 
            )          

        return {"matches": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content similarity query error: {str(e)}")
    
#@app.post('/query_profile')
def __query_profile(request: ProfileSimilarityRequest):
    try:
        metadata_agent = MetadataAgent()
        mega_similarity_agent = MegaSimilarityAgent()
        threshold = float(os.getenv('Threshold'))
        top_k =int(os.getenv('Top_k'))
        
        # SQL query to fetch theme_main, theme_1, theme_2, theme_3, theme_4 for the given user_handle
        profile_query = f"""
            SELECT IFNULL(topic_category, '') AS topic_category, 
                   IFNULL(relates_to, '') AS relates_to, 
                   IFNULL(purpose, '') AS purpose, 
                   IFNULL(execution_method, '') AS execution_method
            FROM {os.getenv('DATABASE')}.{os.getenv('CONTENT_TABLE')} 
            WHERE user_handle = '{request.user_handle}'
            order by id desc limit 1 
            """
        # Fetch profile data
        profile_data = metadata_agent.fetch_data(profile_query)
        if not profile_data:
            raise HTTPException(status_code=404, detail=f"User Name {request.user_handle} not found in the profile table.")
        
        # Extract themes for embedding generation
        themes = " ".join([
            profile_data[-1]["topic_category"],
            profile_data[-1]["relates_to"],
            profile_data[-1]["purpose"],
            profile_data[-1]["execution_method"]
        ])

        logging.info({'Themes': themes})
        
        # Perform similarity query
        results = mega_similarity_agent.query(
            query_text=themes,
            collection_name=os.getenv("PROFILE_COLLECTION_NAME"),
            threshold=threshold,
            top_k=top_k,
            user_handle=request.user_handle
        )

        return {"matches": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile similarity query error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)