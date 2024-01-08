from fastapi import Depends, FastAPI, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime
from google.cloud import datastore
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, initialize_app, auth
import firebase_admin
import uuid


client = datastore.Client()
app = FastAPI()

cred = credentials.Certificate("credentials/credentialsfirebase.json")
firebase_admin.initialize_app(cred)

# uid = 'some-uid'
# custom_token = auth.create_custom_token(uid)
# print(f"this is a custom token: {custom_token}")

# TIENE QUE IR DENTRO DE LA FUNCION 
# decoded_token = auth.verify_id_token(idToken)
# uid = decoded_token['uid']

# print(f"This is the decoded token {decoded_token}")

class MessageBody(BaseModel):
    name: str
    file_url: str 
    
#FORMULARIO

#FUNCION PARA PROCESAR EL FORMULARIO
def process_form(name, ts, file_url, done=True):
    #name = request.form["name"]
    timestamp = datastore.Entity(client.key("Photo"))
    timestamp.update({
        "name": name,
        "time": ts,
        "done": done,
        "file_url": file_url
    })

    client.put(timestamp)
    return "Has sido registrado"

#VERIFICAR EL TOKEN DEL BACK

@app.post("/photo/")
def create_timestamp(message_body: MessageBody, authorization: str = Header(...)):
    try: 
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        print(decoded_token)

    except Exception as e:
        print(e)
        raise  HTTPException(status_code=401, detail=f"Error en la autenticación")
    
    try:
        current_time = datetime.now()
        #GENERA NOMBRE ÚNICO USANDO UUID 
        file_name = str(uuid.uuid4()) + '_' + message_body.name
        print(f"Nombre: {message_body.name}, Timestamp: {current_time}, File URL: {message_body.file_url}")
        process_form(file_name , current_time, message_body.file_url, done=True)
        result = {"message": "Registro exitoso"}  
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=f"Error en el proceso: {str(e)}")  # DEVUELVE ERROR
    
    return result

#PERMITIR SOLICITUDES DESDE EL DOMINIO DE MI APLICACIÓN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)