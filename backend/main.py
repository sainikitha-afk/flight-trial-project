from fastapi import FastAPI, UploadFile, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import pandas as pd
import io
from auth import hash_password, verify_password, create_access_token, decode_access_token
from datetime import timedelta

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["flight_data_db"]
users_collection = db["users"]
data_collection = db["flight_data_collection"]

# User Registration
@app.post("/register/")
def register_user(email: str, password: str):
    if users_collection.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pw = hash_password(password)
    users_collection.insert_one({"email": email, "password": hashed_pw})
    return {"message": "User registered successfully"}

# User Login
@app.post("/login/")
def login_user(email: str, password: str):
    user = users_collection.find_one({"email": email})
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": email}, expires_delta=timedelta(hours=1))
    return {"access_token": token}

# Auth Dependency
def get_current_user(token: str = Header(...)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]

# Upload endpoint (protected)
@app.post("/upload/")
async def upload_csv(file: UploadFile, user: str = Depends(get_current_user)):
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode()))
    df["uploaded_by"] = user  # link dataset to user
    data = df.to_dict(orient="records")
    data_collection.insert_many(data)
    return {"message": "Data uploaded successfully"}

@app.post("/add-parameter/")
async def add_parameter(
    flight_id: str,
    parameter_name: str,
    parameter_value: str,
    token: str = Header(...)
):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Check if FlightID already exists
    existing_flight = data_collection.find_one({"FlightID": flight_id})

    if existing_flight:
        # If flight exists, update with new parameter
        data_collection.update_one(
            {"FlightID": flight_id},
            {"$set": {parameter_name: parameter_value}}
        )
    else:
        # If flight doesn't exist, create new entry
        new_doc = {
            "FlightID": flight_id,
            parameter_name: parameter_value,
            "uploaded_by": payload["sub"]
        }
        data_collection.insert_one(new_doc)

    return {"message": "Parameter added successfully!"}

@app.get("/test-route/")
def test():
    return {"message": "working"}

@app.get("/get-existing-flights/")
async def get_existing_flights(token: str = Header(...)):
    print("GET /get-existing-flights/ CALLED")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Fetch distinct FlightIDs
    flights = data_collection.distinct("FlightID")
    return {"flights": flights}


