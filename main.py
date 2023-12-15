from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from google.cloud import datastore
from http import server

client = datastore.Client()

#FORMULARIO

#FUNCION PARA PROCESAR EL FORMULARIO
def process_form(name, ts):
    #name = request.form["name"]
    timestamp = datastore.Entity(client.key("Timestamp", name))
    timestamp.update({
        "name": name,
        "time": ts,
    })

    client.put(timestamp)
    return "Has sido registrado"

#with client.transaction():
   # key = client.key("Timestamp", "John Doe")
    #timestamp = client.get(key)

   # timestamp["done"] = True
   #timestamp["name"] = "John Doe"
    #timestamp["time"] = f"{datetime.now()}"
    
    #client.put(timestamp)
    #print (f"El cliente {timestamp['name']} ha ingresado a las {datetime.now()}")

app = FastAPI()

class MessageBody(BaseModel):
    name: str

@app.post("/timestamp/")
def create_timestamp(message_body: MessageBody):
    current_time = datetime.now()
    print(f" Nombre: {message_body.name}, Timestamp: {current_time}")
    process_form(message_body.name, current_time)
    return {"name": f"{message_body.name}"}