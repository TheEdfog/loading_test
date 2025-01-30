from fastapi import FastAPI
import random

app = FastAPI()

@app.get('/')
def index():
    return {'Hello World!'}

@app.get(r"/calculate/{name}")
def name_info(name):
    name = str(name)
    info = {
        'name': name,
        'length': len(name),
        'popularity': random.randint(1, 100)
    }

    return info
