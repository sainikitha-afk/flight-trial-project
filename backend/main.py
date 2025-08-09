from fastapi import FastAPI, HTTPException, Header, File, UploadFile, Form
import csv
from io import StringIO
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel
from auth import hash_password, verify_password, create_access_token, decode_access_token
from datetime import timedelta
from fastapi import Request
import sys
import contextlib
import io

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["flight_data_db"]
users_collection = db["users"]
data_collection = db["flight_data"]

# Pydantic model for body data
class UserData(BaseModel):
    email: str
    password: str

class ParameterInput(BaseModel):
    FlightID: str
    parameter_name: str
    parameter_value: str

# Register route
@app.post("/register/")
def register_user(user: UserData):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = hash_password(user.password)
    users_collection.insert_one({"email": user.email, "password": hashed_pw})
    return {"message": "User registered successfully"}

# Login route
@app.post("/login/")
def login_user(user: UserData):
    existing = users_collection.find_one({"email": user.email})
    if not existing or not verify_password(user.password, existing["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))
    return {"access_token": token}

from fastapi import UploadFile, File, Form, HTTPException
from typing import List
import csv
from io import StringIO

@app.post("/upload/")
async def upload_csv(file: UploadFile = File(...), email: str = Form(...)):
    contents = await file.read()
    decoded = contents.decode("utf-8")
    reader = csv.DictReader(StringIO(decoded))

    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty.")

    # 🔍 Extract FlightID from the first row (assuming it's consistent across rows)
    flight_id = rows[0].get("FlightID")
    if not flight_id:
        raise HTTPException(status_code=400, detail="FlightID column missing in CSV.")

    # 🔒 Check if this FlightID already exists in DB (regardless of user)
    existing = db["flight_data"].find_one({"FlightID": flight_id})
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Flight ID '{flight_id}' already exists. Please use a unique name like 'F001_username' or 'TRIAL_F001'."
        )

    # ✅ Insert rows with uploaded_by info
    for row in rows:
        row['uploaded_by'] = email
        db["flight_data"].insert_one(row)

    return {"message": f"CSV for Flight ID '{flight_id}' uploaded successfully."}

@app.post("/create-flight/")
def create_flight(flight_id: str = Form(...), email: str = Form(...)):
    # Check if flight_id already exists in the DB (regardless of who uploaded it)
    existing = db["flight_data"].find_one({"FlightID": flight_id})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Flight ID already exists. Please use a unique name. You can follow a format like FLT001_YourName or FLT001_2025"
        )

    db["flight_data"].insert_one({
        "FlightID": flight_id,
        "uploaded_by": email
    })

    return {"message": "New Flight ID created"}

@app.post("/add-parameter/")
async def add_parameter(
    flight_id: str = Form(...),
    parameter_name: str = Form(...),
    parameter_value: str = Form(...),
    email: str = Form(...)
):
    # Check if the flight exists
    flight = db["flight_data"].find_one({"FlightID": flight_id, "uploaded_by": email})
    
    if not flight:
        raise HTTPException(status_code=404, detail="Flight ID not found for this user")

    # Check for duplicate parameter
    if parameter_name in flight:
        raise HTTPException(status_code=400, detail="Parameter already exists for this flight")

    # Update the document with new parameter
    db["flight_data"].update_one(
        {"FlightID": flight_id, "uploaded_by": email},
        {"$set": {parameter_name: parameter_value}}
    )

    return {"message": "Parameter added successfully"}

@app.put("/update-parameter/")
async def update_parameter(
    flight_id: str = Form(...),
    parameter_name: str = Form(...),
    new_value: str = Form(...),
    email: str = Form(...)
):
    query = {"FlightID": flight_id, "uploaded_by": email}
    update_result = db["flight_data"].update_one(query, {"$set": {parameter_name: new_value}})

    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Parameter or Flight ID not found")

    return {"message": "Parameter updated successfully"}

@app.delete("/delete-parameter/")
def delete_parameter(
    flight_id: str = Form(...),
    parameter_name: str = Form(...),
    email: str = Form(...)
):
    query = {"FlightID": flight_id, "uploaded_by": email}
    flight = db["flight_data"].find_one(query)

    if not flight or parameter_name not in flight:
        raise HTTPException(status_code=404, detail="Parameter not found")

    db["flight_data"].update_one(query, {"$unset": {parameter_name: ""}})
    return {"message": "Parameter deleted successfully"}


@app.get("/get-all-flight-ids/")
def get_all_flight_ids(token: str = Header(...)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    flight_ids = db["flight_data"].distinct("FlightID", {"uploaded_by": payload["sub"]})
    return {"flight_ids": flight_ids}

@app.get("/get-existing-flights/")
def list_user_flight_ids(token: str = Header(...)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    flights = db["flight_data"].find({"uploaded_by": payload["sub"]})
    flight_ids = list({f["FlightID"] for f in flights})  # using set to remove duplicates

    return {"flights": flight_ids}

# Get list of user flight IDs
@app.get("/get-flight/{flight_id}")
def get_flight_data(flight_id: str, token: str = Header(...)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    flight = db["flight_data"].find_one({
        "FlightID": flight_id,
        "uploaded_by": payload["sub"]
    })

    if not flight:
        raise HTTPException(status_code=404, detail="Flight data not found")

    flight["_id"] = str(flight["_id"])  # Convert ObjectId to string
    return {"data": flight}

@app.post("/execute-code/")
async def execute_code(request: Request, token: str = Header(...)):
    body = await request.json()
    code = body.get("code")
    flight_ids = body.get("flight_ids")  # ✅ this is now a list

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    email = payload["sub"]

    flight_data_list = []
    for fid in flight_ids:
        flight = db["flight_data"].find_one({"FlightID": fid, "uploaded_by": email})
        if flight:
            flight.pop("_id", None)
            flight.pop("uploaded_by", None)
            flight_data_list.append(flight)
    
    safe_globals = {
        "__builtins__": {
            "print": print,
            "len": len,
            "sum": sum,
            "max": max,
            "min": min,
            "range": range,
            "sorted": sorted,
            "int": int,
            "float": float,
            "str": str,
            "isinstance": isinstance,
        }
    }

    local_vars = {"data": flight_data_list}  # 🧠 now data is a list of dicts
    output_buffer = io.StringIO()

    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, safe_globals, local_vars)
    except Exception as e:
        return {"output": f"❌ Error:\n{str(e)}"}

    return {"output": output_buffer.getvalue() or "✅ Code ran successfully."}


