#!/usr/bin/env python3
"""
Data seeding script for HMS Flask MongoDB Bootstrap
Run this script to populate the database with sample data
"""

import os
import sys
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from pymongo import MongoClient
from bson import ObjectId

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Database connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/hospital_db")
client = MongoClient(MONGO_URI)
db = client.hospital_db

def seed_doctors():
    """Seed sample doctors"""
    doctors = [
        {
            "full_name": "Dr. Smith",
            "email": "dr.smith@medconnect.com",
            "phone": "555-0101",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "Cardiologist",
            "photo_url": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        },
        {
            "full_name": "Dr. Johnson",
            "email": "dr.johnson@medconnect.com",
            "phone": "555-0102",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "General Physician",
            "photo_url": "https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        },
        {
            "full_name": "Dr. Williams",
            "email": "dr.williams@medconnect.com",
            "phone": "555-0103",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "Dermatologist",
            "photo_url": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        },
        {
            "full_name": "Dr. Brown",
            "email": "dr.brown@medconnect.com",
            "phone": "555-0104",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "Orthopedist",
            "photo_url": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        },
        {
            "full_name": "Dr. Davis",
            "email": "dr.davis@medconnect.com",
            "phone": "555-0105",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "Neurologist",
            "photo_url": "https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        },
        {
            "full_name": "Dr. Wilson",
            "email": "dr.wilson@medconnect.com",
            "phone": "555-0106",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "Pediatrician",
            "photo_url": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        },
        {
            "full_name": "Dr. Garcia",
            "email": "dr.garcia@medconnect.com",
            "phone": "555-0107",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "Gynecologist",
            "photo_url": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        },
        {
            "full_name": "Dr. Lee",
            "email": "dr.lee@medconnect.com",
            "phone": "555-0108",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "Psychiatrist",
            "photo_url": "https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        },
        {
            "full_name": "Dr. Taylor",
            "email": "dr.taylor@medconnect.com",
            "phone": "555-0109",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "Ophthalmologist",
            "photo_url": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        },
        {
            "full_name": "Dr. Anderson",
            "email": "dr.anderson@medconnect.com",
            "phone": "555-0110",
            "password": generate_password_hash("123456"),
            "role": "DOCTOR",
            "specialization": "ENT Specialist",
            "photo_url": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=150&h=150&fit=crop&crop=face",
            "created_at": datetime.utcnow()
        }
    ]
    
    for doctor in doctors:
        existing = db.users.find_one({"email": doctor["email"]})
        if not existing:
            db.users.insert_one(doctor)
            print(f"Added doctor: {doctor['full_name']}")
        else:
            print(f"Doctor already exists: {doctor['full_name']}")

def seed_patients():
    """Seed sample patients"""
    patients = [
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@email.com",
            "phone": "555-1001",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Male",
            "age": 35,
            "address": "123 Main St, City, State 12345",
            "insurance_id": "INS001",
            "created_at": datetime.utcnow()
        },
        {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@email.com",
            "phone": "555-1002",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Female",
            "age": 28,
            "address": "456 Oak Ave, City, State 12345",
            "insurance_id": "INS002",
            "created_at": datetime.utcnow()
        },
        {
            "first_name": "Michael",
            "last_name": "Johnson",
            "email": "michael.johnson@email.com",
            "phone": "555-1003",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Male",
            "age": 42,
            "address": "789 Pine Rd, City, State 12345",
            "insurance_id": "INS003",
            "created_at": datetime.utcnow()
        },
        {
            "first_name": "Sarah",
            "last_name": "Williams",
            "email": "sarah.williams@email.com",
            "phone": "555-1004",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Female",
            "age": 31,
            "address": "321 Elm St, City, State 12345",
            "insurance_id": "INS004",
            "created_at": datetime.utcnow()
        },
        {
            "first_name": "David",
            "last_name": "Brown",
            "email": "david.brown@email.com",
            "phone": "555-1005",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Male",
            "age": 55,
            "address": "654 Maple Dr, City, State 12345",
            "insurance_id": "INS005",
            "created_at": datetime.utcnow()
        },
        {
            "first_name": "Emily",
            "last_name": "Davis",
            "email": "emily.davis@email.com",
            "phone": "555-1006",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Female",
            "age": 24,
            "address": "987 Cedar Ln, City, State 12345",
            "insurance_id": "INS006",
            "created_at": datetime.utcnow()
        },
        {
            "first_name": "Robert",
            "last_name": "Wilson",
            "email": "robert.wilson@email.com",
            "phone": "555-1007",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Male",
            "age": 38,
            "address": "147 Birch St, City, State 12345",
            "insurance_id": "INS007",
            "created_at": datetime.utcnow()
        },
        {
            "first_name": "Lisa",
            "last_name": "Garcia",
            "email": "lisa.garcia@email.com",
            "phone": "555-1008",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Female",
            "age": 29,
            "address": "258 Spruce Ave, City, State 12345",
            "insurance_id": "INS008",
            "created_at": datetime.utcnow()
        },
        {
            "first_name": "James",
            "last_name": "Lee",
            "email": "james.lee@email.com",
            "phone": "555-1009",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Male",
            "age": 47,
            "address": "369 Willow Rd, City, State 12345",
            "insurance_id": "INS009",
            "created_at": datetime.utcnow()
        },
        {
            "first_name": "Maria",
            "last_name": "Taylor",
            "email": "maria.taylor@email.com",
            "phone": "555-1010",
            "password": generate_password_hash("123"),
            "role": "PATIENT",
            "gender": "Female",
            "age": 33,
            "address": "741 Poplar Dr, City, State 12345",
            "insurance_id": "INS010",
            "created_at": datetime.utcnow()
        }
    ]
    
    for patient in patients:
        existing = db.users.find_one({"email": patient["email"]})
        if not existing:
            db.users.insert_one(patient)
            print(f"Added patient: {patient['first_name']} {patient['last_name']}")
        else:
            print(f"Patient already exists: {patient['first_name']} {patient['last_name']}")

def seed_inventory():
    """Seed sample inventory"""
    inventory_items = [
        {
            "sku": "MED001",
            "name": "Paracetamol 500mg",
            "category": "MEDICINE",
            "stock_qty": 100,
            "unit_cost": 0.50,
            "unit_price": 2.00,
            "low_stock_threshold": 10,
            "expiry_date": "2025-12-31",
            "supplier": "PharmaCorp",
            "is_drug": True,
            "created_at": datetime.utcnow()
        },
        {
            "sku": "MED002",
            "name": "Ibuprofen 400mg",
            "category": "MEDICINE",
            "stock_qty": 75,
            "unit_cost": 0.75,
            "unit_price": 3.00,
            "low_stock_threshold": 10,
            "expiry_date": "2025-11-30",
            "supplier": "MedSupply Inc",
            "is_drug": True,
            "created_at": datetime.utcnow()
        },
        {
            "sku": "MED003",
            "name": "Amoxicillin 250mg",
            "category": "MEDICINE",
            "stock_qty": 50,
            "unit_cost": 1.20,
            "unit_price": 5.00,
            "low_stock_threshold": 5,
            "expiry_date": "2025-10-15",
            "supplier": "AntibioTech",
            "is_drug": True,
            "created_at": datetime.utcnow()
        },
        {
            "sku": "MED004",
            "name": "Insulin Pen",
            "category": "MEDICINE",
            "stock_qty": 25,
            "unit_cost": 15.00,
            "unit_price": 45.00,
            "low_stock_threshold": 3,
            "expiry_date": "2025-09-20",
            "supplier": "DiabetiCare",
            "is_drug": True,
            "created_at": datetime.utcnow()
        },
        {
            "sku": "MED005",
            "name": "Blood Pressure Monitor",
            "category": "EQUIPMENT",
            "stock_qty": 15,
            "unit_cost": 25.00,
            "unit_price": 75.00,
            "low_stock_threshold": 2,
            "expiry_date": None,
            "supplier": "MediTech Solutions",
            "is_drug": False,
            "created_at": datetime.utcnow()
        },
        {
            "sku": "MED006",
            "name": "Gauze Pads",
            "category": "SUPPLIES",
            "stock_qty": 200,
            "unit_cost": 0.25,
            "unit_price": 1.00,
            "low_stock_threshold": 20,
            "expiry_date": "2026-01-01",
            "supplier": "SupplyMed",
            "is_drug": False,
            "created_at": datetime.utcnow()
        },
        {
            "sku": "MED007",
            "name": "COVID-19 Vaccine",
            "category": "VACCINE",
            "stock_qty": 30,
            "unit_cost": 8.00,
            "unit_price": 25.00,
            "low_stock_threshold": 5,
            "expiry_date": "2025-08-30",
            "supplier": "VaxCorp",
            "is_drug": False,
            "created_at": datetime.utcnow()
        },
        {
            "sku": "MED008",
            "name": "Glucose Test Strips",
            "category": "DIAGNOSTIC",
            "stock_qty": 100,
            "unit_cost": 0.80,
            "unit_price": 3.50,
            "low_stock_threshold": 15,
            "expiry_date": "2025-12-15",
            "supplier": "DiabetiCare",
            "is_drug": False,
            "created_at": datetime.utcnow()
        }
    ]
    
    for item in inventory_items:
        existing = db.inventory.find_one({"sku": item["sku"]})
        if not existing:
            db.inventory.insert_one(item)
            print(f"Added inventory item: {item['name']}")
        else:
            print(f"Inventory item already exists: {item['name']}")

def seed_appointments():
    """Seed sample appointments"""
    doctors = list(db.users.find({"role": "DOCTOR"}))
    patients = list(db.users.find({"role": "PATIENT"}))
    
    if not doctors or not patients:
        print("No doctors or patients found. Please seed them first.")
        return
    
    appointments = []
    for i in range(20):
        doctor = doctors[i % len(doctors)]
        patient = patients[i % len(patients)]
        
        appointment_date = datetime.utcnow() + timedelta(days=i-10)
        
        # Handle different patient name formats
        if 'first_name' in patient and 'last_name' in patient:
            patient_name = f"{patient['first_name']} {patient['last_name']}"
        else:
            patient_name = patient.get('full_name', 'Unknown Patient')
        
        appointment = {
            "patient_id": patient["_id"],
            "patient_email": patient["email"],
            "patient_name": patient_name,
            "doctor_name": doctor["full_name"],
            "date": appointment_date.strftime("%Y-%m-%d"),
            "time": f"{9 + (i % 8):02d}:00",
            "notes": f"Regular consultation for {patient_name}",
            "status": "CONFIRMED" if i < 15 else "REQUESTED",
            "created_at": datetime.utcnow()
        }
        appointments.append(appointment)
    
    for appointment in appointments:
        db.appointments.insert_one(appointment)
        print(f"Added appointment: {appointment['patient_name']} with {appointment['doctor_name']}")

def seed_lab_tests():
    """Seed sample lab tests"""
    patients = list(db.users.find({"role": "PATIENT"}))
    
    if not patients:
        print("No patients found. Please seed them first.")
        return
    
    lab_tests = [
        "Blood Test", "Urine Analysis", "X-Ray", "MRI Scan", "CT Scan", 
        "ECG", "Ultrasound", "Biopsy", "Culture Test", "Glucose Test"
    ]
    
    for i in range(15):
        patient = patients[i % len(patients)]
        
        # Handle different patient name formats
        if 'first_name' in patient and 'last_name' in patient:
            patient_name = f"{patient['first_name']} {patient['last_name']}"
        else:
            patient_name = patient.get('full_name', 'Unknown Patient')
        
        lab_test = {
            "patient_id": patient["_id"],
            "patient_name": patient_name,
            "patient_email": patient["email"],
            "test_name": lab_tests[i % len(lab_tests)],
            "test_date": (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d"),
            "status": "COMPLETED" if i < 10 else "PENDING",
            "results": f"Normal results for {lab_tests[i % len(lab_tests)]}" if i < 10 else None,
            "created_at": datetime.utcnow()
        }
        db.lab_tests.insert_one(lab_test)
        print(f"Added lab test: {lab_test['test_name']} for {lab_test['patient_name']}")

def main():
    """Main seeding function"""
    print("Starting database seeding...")
    
    print("\n1. Seeding doctors...")
    seed_doctors()
    
    print("\n2. Seeding patients...")
    seed_patients()
    
    print("\n3. Seeding inventory...")
    seed_inventory()
    
    print("\n4. Seeding appointments...")
    seed_appointments()
    
    print("\n5. Seeding lab tests...")
    seed_lab_tests()
    
    print("\nDatabase seeding completed successfully!")
    print("\nLogin credentials:")
    print("Doctors: Use email addresses with password '123456'")
    print("Patients: Use email addresses with password '123'")
    print("Admin: Create manually through registration")

if __name__ == "__main__":
    main()
