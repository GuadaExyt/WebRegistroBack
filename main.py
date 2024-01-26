import json
from fastapi import Depends, FastAPI, HTTPException, Header, Path, status
from fastapi import APIRouter
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from google.cloud import datastore
from firebase_admin import credentials, initialize_app, auth
from firebase_admin import storage as firebase_storage
import firebase_admin
from google.cloud import pubsub_v1
from concurrent import futures

client = datastore.Client()
app = FastAPI()

cred = credentials.Certificate("credentials/credentialsfirebase.json")
firebase_admin.initialize_app(cred, {"storageBucket": "myproject-5a445.appspot.com"})
bucket = firebase_storage.bucket()

# TODO(developer)
project_id = "datastore-408009"
topic_id = "topic_uploadfile"

publisher = pubsub_v1.PublisherClient()
# The `topic_path` method creates a fully qualified identifier
# in the form `projects/{project_id}/topics/{topic_id}`
topic_path = publisher.topic_path(project_id, topic_id)

class createRegisterBody(BaseModel):
    name: str
    file_url: str
    # admin: bool = False 

class CreateUserBody(BaseModel):
    email: str
    password: str
    admin: Optional[bool] = False

# DEFINIR LA ESTRUCTURA DEL CUERPO DE LA SOLICITUD PARA EDITAR 
class UserPermissionsUpdate(BaseModel):
    admin: bool

def get_publisher_client():
    publisher = pubsub_v1.PublisherClient()
    return publisher


#FORMULARIO

#FUNCION PARA PROCESAR EL FORMULARIO
def process_form(name, ts, file_url, user_id, done=True):
    #name = request.form["name"]
    newregister = datastore.Entity(client.key("Photo"))
    newregister.update({
        "name": name,
        "time": ts,
        "done": done,
        "file_url": file_url,
        "user_id": user_id,
        # "admin": admin,
        })

    client.put(newregister)
    return "Has sido registrado"

#FUNCION PARA ASIGNAR EL ROL DE ADMIN A USER 
def assign_admin_user(decoded_token):
    try:
        # OBTENER UID DEL TOKEN DECODIFICADO
        uid = decoded_token.get('uid')

        # VERIFICAR SI COINCIDEN LOS UID
        if uid == 'bA5bVViWviQLyAKLelVPIOUFGri2':
            # ESTABLECE ROL DE ADMIN AL UID DETERMINADO
            auth.set_custom_user_claims(uid, {'admin': True})
            print(f"Se ha asignado la función de Admin al usuario con UID: {uid}")
        else:
            auth.set_custom_user_claims(uid, {'admin': False})
            print(f"El usuario con UID: {uid} no tiene permisos de administrador.")
    
    except Exception as e:
        print(f"Error al asignar la función de Admin: {str(e)}")

#VERIFICAR EL TOKEN DEL BACK

@app.post("/api/photo/")
def create_timestamp(message_body: createRegisterBody, authorization: str = Header(...), publisher: pubsub_v1.PublisherClient = Depends(get_publisher_client),):
    try: 
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token.get('uid')
        print("DECODED TOKEN:", decoded_token)

    except Exception as e:
        print(e)
        raise  HTTPException(status_code=401, detail=f"Error en la autenticación")
    
    try:
        current_time = datetime.now()
        file_name = message_body.name
        print(f"Nombre: {message_body.name}, Timestamp: {current_time}, File URL: {message_body.file_url}, User_id: {user_id}")
        process_form(file_name , current_time, message_body.file_url, user_id, done=True)
        
        #MENSAJE
        message_data = {
            "file_url": message_body.file_url,
            "name": message_body.name,
            "time": str(datetime.now()),
            "user_id": user_id,
            "Acciones": "CREATE"
        }

        message_future = publisher.publish(topic_path, data=json.dumps(message_data).encode("utf-8"))
        message_future.result()  
        
        result = {"message": "Registro exitoso"}  
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=f"Error en el proceso: {str(e)}")  # DEVUELVE ERROR
    
    return result
    

#✨ feat: añadir método GET /photo
@app.get("/api/photo/")
def get_user_photos(authorization: str = Header(...)):
    try: 
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token.get('uid')
        user_email = decoded_token.get('email') 
        print("ID de usuario:", user_id)
        # assign_admin_user(user_id) 

        print(decoded_token)
    except Exception as e:
        print(e)
        raise  HTTPException(status_code=401, detail=f"Error en la autenticación")
    
    try: 
        query = client.query(kind="Photo")
        query.add_filter("user_id", "=", user_id)
        # print("query IMPRESO:", query) 
        
        photos = list(query.fetch())
        user_photo_info = []
        for photo in photos:
            photo_info = {
                "id": str(photo.key.id),
                "file_url": photo["file_url"],
                "name": photo["name"],
                "time": photo["time"],
            }
            user_photo_info.append(photo_info)

        #ORDENAR LAS FOTOS
        user_photo_info = sorted(user_photo_info, key=lambda x: x["time"], reverse=True)
        print("Información de las fotos del usuario:", user_photo_info)
        return {"user_photos": user_photo_info}

    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=f"Error en la consulta: {str(e)}")
    
#✨ feat: añadir método DELETE /photo/:id
@app.delete("/api/photo/{photo_id}")
async def delete_photo(
    photo_id: str = Path(..., title="ID de la foto a eliminar"),
    authorization: str = Header(...),
):
    try:
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token.get("uid")
        print("ID de usuario:", user_id)

    except Exception as e:
        print(e)
        raise HTTPException(status_code=401, detail="Error en la autenticación")

    #RECUPERAR ENTIDAD CORRESPONDIENTE AL ID DATASTORE
    key = client.key("Photo", int(photo_id))
    photo_entity = client.get(key)

    # VERIFICAR SI EXISTE LA ENTIDAD Y SI SU USUARIO ES CORRESPONDIENTE 
    if not photo_entity or photo_entity["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Foto no encontrada o no autorizada")

    file_url = photo_entity.get("file_url")
    name = photo_entity.get("name")
    time = photo_entity.get("time").isoformat() 
    try:
        # ELIMINA EL REGISTRO EN DATASTORE
        client.delete(key)
        # MENSAJE PARA PUB/SUB
        message_data = {
             "file_url": file_url,
            "name": name,
            "time": time,
            "user_id": user_id,
            "Acciones": "DELETE"
        }

        # PUBLICAR MENSAJE
        topic_path = publisher.topic_path(project_id, topic_id)
        message_future = publisher.publish(topic_path, data=json.dumps(message_data).encode("utf-8"))
        message_future.result()  

        result = {"message": "Eliminación exitosa en Datastore"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error en el proceso de eliminación en Datastore: {str(e)}")

    return result

# ✨ feat: añadir endpoint GET /user —> para obtener todos los usuarios de nuestra app
@app.get("/api/user", response_model=dict)
def get_all_users(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        # ACTUALIZAMOS LÓGICA
        # assign_admin_user(decoded_token)
        # VERIFICAR SI EL USER CUMPLE EL ROL DE ADMIN
        admin_claim = decoded_token.get('admin')
        if admin_claim is None or not admin_claim:
            print("Usuario sin permisos de administrador")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene permisos de administrador."
            )

        # OBTENER TODOS LOS USUARIOS
        all_users = auth.list_users()

        # INFORMACIÓN DEL USUARIO
        user_list = []
        for user in all_users.users:
            # OBTENER EL VALOR DE ADMIN
            custom_claims = user.custom_claims or {}
            admin_value = custom_claims.get('admin')

            user_info = {
                'uid': user.uid,
                'email': user.email,
                'admin': admin_value,
                'disabled': user.disabled
            }
            user_list.append(user_info)

        return {"users": user_list}

    except auth.InvalidIdTokenError as e:
        print(f"Error en la autenticación: {e}")
        raise HTTPException(status_code=401, detail="Token de identificación no válido")

    except HTTPException as he:
        raise he  # (*Re-lanzar la excepción HTTPException directamente*)

    except Exception as e:
        print(f"Error desconocido: {e}")
        raise HTTPException(status_code=401, detail="Error en la autenticación")
    
# ✨ feat: añadir endpoint POST /user —> para crear un nuevo usuario
@app.post("/api/user", response_model=dict)
def create_user(user_body: CreateUserBody, authorization: str = Header(...)):
    try:
        # TOKEN DE AUTORIZACIÓN
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        admin_claim = decoded_token.get('admin')

        # SI EL USUARIO TIENE PERMISOS DE ADMINISTRAODR
        if admin_claim is None or not admin_claim:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene permisos de administrador."
            )

        # CREAR NUEVO USUARIO EN FIREBASE
        new_user = auth.create_user(
            email=user_body.email,
            password=user_body.password,
        )
        # ESTABLECER VALOR DE ADMIN DESPUÉS DE CREAR USUARIO
        auth.set_custom_user_claims(new_user.uid, {'admin': user_body.admin})

        # INFORMACIÓN DEL USUARIO NUEVO
        user_info = {
            'uid': new_user.uid,
            'email': new_user.email,
            'admin': user_body.admin
        }
        return {"user": user_info}

    except auth.InvalidIdTokenError as e:
        # ERROR DE TOKEN DE IDENTIFICACIÓN
        print(f"Error en la autenticación: {e}")
        raise HTTPException(status_code=401, detail="Token de identificación no válido")
    # MANEJO DE ERRORES 
    except HTTPException as he:
        print(f"Error HTTP: {he.detail}")
        raise he

    except Exception as e:
        print(f"Error desconocido: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la creación del usuario: {str(e)}")

# ✨ feat: añadir endpoint DELETE /user/{uid} —> para deshabilitar un usuario en cuestión
    
@app.delete("/api/user/{uid}", response_model=dict)
def disable_user(uid: str, authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        admin_claim = decoded_token.get('admin')

        if admin_claim is None or not admin_claim:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene permisos de administrador."
            )

        # DESHABILITAR USUARIO CON Firebase Authentication
        auth.update_user(uid, disabled=True)

        return {"message": f"Usuario con UID {uid} deshabilitado correctamente"}

    except auth.InvalidIdTokenError as e:
        print(f"Error en la autenticación: {e}")
        raise HTTPException(status_code=401, detail="Token de identificación no válido")

    except HTTPException as he:
        print(f"Error HTTP: {he.detail}")
        raise he

    except Exception as e:
        print(f"Error desconocido: {e}")
        raise HTTPException(status_code=500, detail=f"Error al deshabilitar el usuario: {str(e)}")

 # ✨ feat: añadir endpoint PUT /user/{uid} —> para editar los permisos de un usuario
@app.put("/api/user/{uid}", response_model=dict)
def edit_user_permissions(
    uid: str,
    user_update: UserPermissionsUpdate,
    authorization: str = Header(..., description="Token de autenticación con permisos de administrador")
):
    try:
        decoded_token = auth.verify_id_token(authorization.replace("Bearer ", ""))
        admin_claim = decoded_token.get('admin')
        if admin_claim is None or not admin_claim:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene permisos de administrador."
            )

        # EDITAR PERMISOS DE USUARIO CON Firebase Authentication
        auth.set_custom_user_claims(uid, {'admin': user_update.admin})

        return {"message": f"Permisos del usuario con UID {uid} editados correctamente"}

    except auth.InvalidIdTokenError as e:
        print(f"Error en la autenticación: {e}")
        raise HTTPException(status_code=401, detail="Token de identificación no válido")

    except HTTPException as he:
        print(f"Error HTTP: {he.detail}")
        raise he

    except Exception as e:
        print(f"Error desconocido: {e}")
        raise HTTPException(status_code=500, detail=f"Error al editar los permisos del usuario: {str(e)}")
       
#PERMITIR SOLICITUDES DESDE EL DOMINIO DE MI APLICACIÓN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)