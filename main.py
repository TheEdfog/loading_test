from fastapi import FastAPI
from pydantic import BaseModel
import random

app = FastAPI()

names = []

class NameRequest(BaseModel):
    name: str

@app.get('/')
def index():
    return {'message': 'Hello World!'}

@app.get(r"/calculate/{name}")
def name_info(name: str):
    info = {
        'name': name,
        'length': len(name),
        'popularity': random.randint(1, 100)
    }
    return info

@app.post(r"/add_name")
def add_name(name_request: NameRequest):
    names.append(name_request.name)
    return {"message": "It worked!"}

@app.get(r"/names")
def get_names():
    return names
