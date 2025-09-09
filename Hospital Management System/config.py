import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_SUPER_SECRET")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/hospital_db")
