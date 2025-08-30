# main.py
from fastapi import FastAPI, HTTPException, Header, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from auth import hash_password, verify_password, create_access_token, decode_access_token
from datetime import timedelta
import csv
from io import StringIO
import contextlib
import io
import re


app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB
client = MongoClient("mongodb://localhost:27017/")
db = client["flight_data_db"]
users_collection = db["users"]
data_collection = db["flight_data"]

# Index: FlightID is globally unique
data_collection.create_index([("FlightID", ASCENDING)], unique=True)

# Schemas
class UserData(BaseModel):
    email: str
    password: str

# ---------- AUTH ----------
@app.post("/register/")
def register_user(user: UserData):
    # ✅ Check if email ends with @gov.in
    if not user.email.endswith("@gov.in"):
        raise HTTPException(status_code=400, detail="Only @gov.in emails are allowed")

    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    users_collection.insert_one({
        "email": user.email,
        "password": hash_password(user.password)
    })
    return {"message": "User registered successfully"}

@app.post("/login/")
def login_user(user: UserData):
    existing = users_collection.find_one({"email": user.email})
    if not existing or not verify_password(user.password, existing["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(hours=1))
    return {"access_token": token}

# ---------- UPLOAD (strict schema + FlightID rule) ----------
REQUIRED_UPLOAD_COLS = [
    "FlightID","Speed","Altitude","BrakeTemp","Current_A","Voltage_V","FuelFlow","Pressure_Pa","Temp_C"
]

@app.post("/upload/")
async def upload_csv(file: UploadFile = File(...), email: str = Form(...)):
    contents = await file.read()
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 CSV")

    reader = csv.DictReader(StringIO(decoded))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty.")

    missing = [c for c in REQUIRED_UPLOAD_COLS if c not in reader.fieldnames]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(missing)}")

    username = email.split("@")[0]

    # validate FlightIDs + detect duplicates in file
    flight_ids = []
    bad_ids = []
    for r in rows:
        fid = (r.get("FlightID") or "").strip()
        if not fid or not fid.endswith(f"_{username}"):
            bad_ids.append(fid or "<EMPTY>")
        else:
            flight_ids.append(fid)

    if bad_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                f"FlightID must end with _{username}. "
                f"Fix these: {', '.join(sorted(set(bad_ids)))}"
            )
        )

    dupes_in_file = sorted({fid for fid in flight_ids if flight_ids.count(fid) > 1})
    if dupes_in_file:
        raise HTTPException(
            status_code=400,
            detail=f"Duplicate FlightID(s) within the same file: {', '.join(dupes_in_file)}"
        )

    unique_ids = sorted(set(flight_ids))

    # global uniqueness check
    for fid in unique_ids:
        if data_collection.find_one({"FlightID": fid}):
            raise HTTPException(
                status_code=400,
                detail=f"FlightID '{fid}' already exists. Pick another like F999_{username}"
            )

    # insert rows
    docs = []
    for r in rows:
        r["uploaded_by"] = email
        docs.append(r)

    try:
        data_collection.insert_many(docs, ordered=True)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Duplicate FlightID detected during insert. Use a new ID.")

    return {"message": "CSV uploaded.", "flight_ids": unique_ids}

# ---------- OPTIONAL: create empty flight doc ----------
@app.post("/create-flight/")
def create_flight(flight_id: str = Form(...), email: str = Form(...)):
    if data_collection.find_one({"FlightID": flight_id}):
        raise HTTPException(status_code=400, detail="Flight ID already exists.")
    data_collection.insert_one({"FlightID": flight_id, "uploaded_by": email})
    return {"message": "New Flight ID created"}

# ---------- SIMPLE PARAMETER CRUD (no catalog) ----------
@app.post("/add-parameter/")
async def add_parameter(
    flight_id: str = Form(...),
    parameter_name: str = Form(...),
    parameter_value: str = Form(...),
    email: str = Form(...)
):
    q = {"FlightID": flight_id, "uploaded_by": email}
    flight = data_collection.find_one(q)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight ID not found for this user")

    if parameter_name in flight:
        raise HTTPException(status_code=400, detail="Parameter already exists for this flight")

    data_collection.update_one(q, {"$set": {parameter_name: parameter_value}})
    return {"message": "Parameter added successfully"}

@app.put("/update-parameter/")
async def update_parameter(
    flight_id: str = Form(...),
    parameter_name: str = Form(...),
    new_value: str = Form(...),
    email: str = Form(...)
):
    q = {"FlightID": flight_id, "uploaded_by": email}
    flight = data_collection.find_one(q)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight ID not found for this user")

    if parameter_name not in flight:
        raise HTTPException(status_code=404, detail="Parameter not found on this flight")

    data_collection.update_one(q, {"$set": {parameter_name: new_value}})
    return {"message": "Parameter updated successfully"}

@app.delete("/delete-parameter/")
def delete_parameter(
    flight_id: str = Form(...),
    parameter_name: str = Form(...),
    email: str = Form(...)
):
    q = {"FlightID": flight_id, "uploaded_by": email}
    flight = data_collection.find_one(q)
    if not flight or parameter_name not in flight:
        raise HTTPException(status_code=404, detail="Parameter not found")

    data_collection.update_one(q, {"$unset": {parameter_name: ""}})
    return {"message": "Parameter deleted successfully"}

# ---------- QUERIES ----------
@app.get("/get-all-flight-ids/")
def get_all_flight_ids(token: str = Header(...)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    ids = data_collection.distinct("FlightID", {"uploaded_by": payload["sub"]})
    return {"flight_ids": ids}

@app.get("/get-existing-flights/")
def list_user_flight_ids(token: str = Header(...)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    flights = data_collection.find({"uploaded_by": payload["sub"]})
    flight_ids = list({f["FlightID"] for f in flights})
    return {"flights": flight_ids}

@app.get("/get-flight/{flight_id}")
def get_flight_data(flight_id: str, token: str = Header(...)):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    flight = data_collection.find_one({"FlightID": flight_id, "uploaded_by": payload["sub"]})
    if not flight:
        raise HTTPException(status_code=404, detail="Flight data not found")
    flight["_id"] = str(flight["_id"])
    return {"data": flight}

# ---------- CODE EXEC ----------
@app.post("/execute-code/")
async def execute_code(request: Request, token: str = Header(...)):
    body = await request.json()
    code = body.get("code") or ""
    flight_ids = body.get("flight_ids") or []

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    email = payload["sub"]

    flight_data_list = []
    for fid in flight_ids:
        flight = data_collection.find_one({"FlightID": fid, "uploaded_by": email})
        if flight:
            flight.pop("_id", None)
            flight.pop("uploaded_by", None)
            flight_data_list.append(flight)

    def print_table(rows, columns=None):
        if not isinstance(rows, list) or not rows:
            print("(no data)")
            return
        if columns is None:
            keys = set()
            for r in rows:
                keys.update(r.keys())
            columns = ["FlightID"] + sorted([k for k in keys if k != "FlightID"])
        # compute widths
        w = {c: len(c) for c in columns}
        for r in rows:
            for c in columns:
                w[c] = max(w[c], len(str(r.get(c, ""))))
        # header
        line = " | ".join(c.ljust(w[c]) for c in columns)
        print(line)
        print("-" * len(line))
        # rows
        for r in rows:
            print(" | ".join(str(r.get(c, "")).ljust(w[c]) for c in columns))


    safe_globals = {
    "__builtins__": {
        "print": print, "len": len, "sum": sum, "max": max, "min": min,
        "range": range, "sorted": sorted, "int": int, "float": float,
        "str": str, "isinstance": isinstance,
        "round": round,            # ✅ add this
        "abs": abs,                # (optional but handy)
        "any": any, "all": all,    # (optional)
        "enumerate": enumerate,    # (optional)
        }
        }
    
    local_vars = {"data": flight_data_list, "print_table": print_table}
    output_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(output_buffer):
            exec(code, safe_globals, local_vars)
    except Exception as e:
        return {"output": f"❌ Error:\n{str(e)}"}

    return {"output": output_buffer.getvalue() or "✅ Code ran successfully."}
