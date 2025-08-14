from fastapi import FastAPI 
import uvicorn
from typing import Optional
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
os.environ["GOOGLE_API_KEY"] = "AIzaSyCfA8gr6hMzSOcu8CclL4sD2WAwLKCpWd8"

app = FastAPI()

# Initialize Gemini model
gemini_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# Root route
@app.get("/")
def read_root():
    return {"message": "Hello World"}

# Path parameter
@app.get("/hello/{name}")
def greet(name: str):
    return {"message": f"Hello {name}"}

# Query parameter
@app.get("/greet2")
def greet(name: str):
    return {"message": f"Hello {name} from the other side"}

# Query and path parameter
@app.get("/greet3/{name}")
def greet(name: str, age: int):
    return {"message": f"Hello {name} from the other side and you are {age} years old"}

# Default value for query parameter
@app.get("/greet4")
def greet_name(age:int, name:Optional[str]="user"):
    return {"message": f"Hello {name} from the other side and you are {age} years old"}

# Data validation
class BookCreateModel(BaseModel):
    title: str
    author: str

# Simple POST endpoint
@app.post("/create_book2")
def create_book(book_data: BookCreateModel):
    return {"message": f"Hello {book_data.title} and the author is {book_data.author}"}

# POST request (HTML response)
@app.post("/create_book")
def create_book(book_data: BookCreateModel):
    from fastapi.responses import HTMLResponse
    return HTMLResponse(
        content=f"<h1>Book Created</h1><p>Title: {book_data.title}</p><p>Author: {book_data.author}</p>",
    )

# New endpoint for Gemini API interaction
class QueryModel(BaseModel):
    question: str

@app.post("/ask_gemini")
async def ask_gemini(query: QueryModel):
    # Simple query
    response = gemini_model.invoke(query.question)
    return {"response": response.content}

# More advanced LangChain usage
@app.post("/ask_gemini_advanced")
async def ask_gemini_advanced(query: QueryModel):
    # Create a prompt template
    prompt = ChatPromptTemplate.from_template(
        "You are a helpful AI assistant. Answer this question: {question}"
    )
    
    # Create a chain
    chain = prompt | gemini_model | StrOutputParser()
    
    # Invoke the chain
    response = chain.invoke({"question": query.question})
    
    return {"response": response}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)