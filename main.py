from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from datetime import datetime
from google.cloud import datastore
from http import server
from fastapi.middleware.cors import CORSMiddleware

client = datastore.Client()
app = FastAPI()

class MessageBody(BaseModel):
    name: str
    file_url: str 
    
#FORMULARIO

#FUNCION PARA PROCESAR EL FORMULARIO
def process_form(name, ts, file_url, done=True):
    #name = request.form["name"]
    timestamp = datastore.Entity(client.key("Timestamp", name))
    timestamp.update({
        "name": name,
        "time": ts,
        "done": done,
        "file_url": file_url
    })

    client.put(timestamp)
    return "Has sido registrado"

@app.post("/timestamp/")
def create_timestamp(message_body: MessageBody):
    current_time = datetime.now()
    print(f" Nombre: {message_body.name}, Timestamp: {current_time}, File URL: {message_body.file_url}")
    process_form(message_body.name, current_time, message_body.file_url, done=True)
    return {"name": f"{message_body.name}", "file_url": message_body.file_url}

#PERMITIR SOLICITUDES DESDE EL DOMINIO DE MI APLICACIÓN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)


#AÑADIR ARCHIVO NO FUNCIONA 
# class MessageBody(BaseModel):
#     name: str

# class UploadItem(BaseModel):
#     file: bytes
#     filename: str
#     content_type: str

# # Procesamiento del formulario y manejo del archivo
# def process_form(name, ts, file, done=True):
#     timestamp = datastore.Entity(client.key("Timestamp", name))
#     timestamp.update({
#         "name": name,
#         "time": ts,
#         "done": done,
#     })

#     client.put(timestamp)

#     return "Has sido registrado"

# # Ruta POST para recibir datos y archivos
# @app.post("/timestamp/")
# async def create_timestamp(message_body: MessageBody, file: UploadFile = File(...)):
#     try:
#         current_time = datetime.now()
#         print(f"Nombre: {message_body.name}, Timestamp: {current_time}")
#         # Llamar a la función para procesar el formulario y el archivo
#         result = process_form(message_body.name, current_time, file)
#         return result
#     except Exception as e:
#         return {"error": f"Error al procesar la solicitud: {str(e)}"}
