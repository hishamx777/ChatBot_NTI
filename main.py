from fastapi import FastAPI, HTTPException, UploadFile, File
import uvicorn
from typing import Optional, List, Dict
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
import os
import base64
from PyPDF2 import PdfReader
import tempfile

os.environ["GOOGLE_API_KEY"] = "AIzaSyCfA8gr6hMzSOcu8CclL4sD2WAwLKCpWd8"

app = FastAPI()

# Initialize Gemini model
gemini_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

# Store chat histories and CVs (in-memory storage)
chat_histories: Dict[str, List[Dict[str, str]]] = {}
uploaded_cvs: Dict[str, List[Dict[str, str]]] = {}

# Helper function to extract text from PDF
def extract_text_from_pdf(file_path: str) -> str:
    with open(file_path, "rb") as f:
        reader = PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

# Chat Models
class QueryModel(BaseModel):
    question: str
    user_id: str = "default"

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatHistoryRequest(BaseModel):
    user_id: str

# CV Analysis Models
class CVData(BaseModel):
    filename: str
    content: str  # base64 encoded
    filetype: str

class CVAnalysisRequest(BaseModel):
    job_description: str
    ranking_criteria: List[str]
    cvs: List[CVData]

class JobDescription(BaseModel):
    user_id: str
    job_title: str
    job_requirements: str

# Chat Endpoints
@app.post("/chat")
async def chat_with_history(query: QueryModel):
    try:
        # Get or initialize chat history
        if query.user_id not in chat_histories:
            chat_histories[query.user_id] = []
        
        # Add user message to history
        chat_histories[query.user_id].append({"role": "user", "content": query.question})
        
        # Prepare conversation context
        conversation = []
        for msg in chat_histories[query.user_id][-10:]:  # Last 10 messages for context
            if msg["role"] == "user":
                conversation.append(HumanMessage(content=msg["content"]))
            else:
                conversation.append(AIMessage(content=msg["content"]))
        
        # Get response from Gemini
        response = gemini_model.invoke(conversation)
        
        # Add assistant response to history
        chat_histories[query.user_id].append({"role": "assistant", "content": response.content})
        
        return {"response": response.content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat_history/{user_id}")
async def get_chat_history(user_id: str):
    return chat_histories.get(user_id, [])

@app.post("/clear_history")
async def clear_history(request: ChatHistoryRequest):
    if request.user_id in chat_histories:
        chat_histories[request.user_id] = []
    return {"status": "success"}

# CV Analysis Endpoints
@app.post("/upload-cv/")
async def upload_cv(user_id: str, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are allowed")
    
    # Save the uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(await file.read())
        temp_path = temp_file.name
    
    # Extract text
    try:
        cv_text = extract_text_from_pdf(temp_path)
        
        if user_id not in uploaded_cvs:
            uploaded_cvs[user_id] = []
        
        uploaded_cvs[user_id].append({
            "filename": file.filename,
            "content": cv_text
        })
        
        os.unlink(temp_path)  # Delete temp file
        
        return {"message": "CV uploaded successfully", "filename": file.filename}
    except Exception as e:
        os.unlink(temp_path)
        raise HTTPException(500, f"Error processing CV: {str(e)}")

@app.post("/analyze_cvs")
async def analyze_cvs(request: CVAnalysisRequest):
    try:
        decoded_cvs = []
        for cv in request.cvs:
            decoded_content = base64.b64decode(cv.content).decode('utf-8')
            decoded_cvs.append({
                "filename": cv.filename,
                "content": decoded_content
            })
        
        analysis = await evaluate_multiple_cvs(
            decoded_cvs,
            request.job_description,
            request.ranking_criteria
        )
        
        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(500, detail=str(e))

@app.post("/evaluate-cvs/")
async def api_evaluate_cvs(job_desc: JobDescription):
    if job_desc.user_id not in uploaded_cvs or not uploaded_cvs[job_desc.user_id]:
        raise HTTPException(400, "No CVs uploaded for this user")
    
    try:
        evaluation = await evaluate_multiple_cvs(
            uploaded_cvs[job_desc.user_id],
            job_desc.job_title,
            job_desc.job_requirements.split("\n")
        )
        return {"evaluation": evaluation}
    except Exception as e:
        raise HTTPException(500, f"Error evaluating CVs: {str(e)}")

async def evaluate_multiple_cvs(cvs: List[Dict], job_title: str, criteria: List[str]) -> str:
    evaluation_prompt = f"""
    Analyze these CVs for the position of {job_title} with these requirements:
    {chr(10).join(criteria)}
    
    Evaluate each CV and rank them from best to worst fit. Provide detailed analysis for each.
    For each CV, provide:
    1. Strengths related to the job
    2. Weaknesses or missing qualifications
    3. Overall score (1-10)
    4. Recommendation (Strong Yes/Maybe/No)
    
    CVs to analyze:
    """
    
    for i, cv in enumerate(cvs):
        evaluation_prompt += f"\n\nCV {i+1} ({cv['filename']}):\n{cv['content'][:5000]}..."
    
    evaluation_prompt += "\n\nPlease provide your analysis in markdown format with clear headings for each CV."
    
    response = gemini_model.invoke(evaluation_prompt)
    return response.content

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)