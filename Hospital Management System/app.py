from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from bson import ObjectId
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from config import Config

ROLES = ["ADMIN", "DOCTOR", "BILLING", "PATIENT"]

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    mongo = PyMongo(app)

    # ---- Helpers ----
    def current_user():
        uid = session.get("user_id")
        if not uid: return None
        return mongo.db.users.find_one({"_id": ObjectId(uid)})

    @app.context_processor
    def inject_user():
        return dict(current_role=session.get("role"), current_user=current_user())

    def login_required(view):
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please login.", "warning")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        wrapper.__name__ = view.__name__
        return wrapper

    def role_required(*roles):
        def decorator(view):
            def wrapper(*args, **kwargs):
                u = current_user()
                if not u or u.get("role") not in roles:
                    flash("Insufficient permissions.", "danger")
                    return redirect(url_for("index"))
                return view(*args, **kwargs)
            wrapper.__name__ = view.__name__
            return wrapper
        return decorator

    # ---- Landing / Home ----
    @app.route("/")
    def index():
        return render_template("index.html")

    # ---- Auth ----
    @app.route("/register", defaults={"fixed_role": None}, methods=["GET", "POST"])
    @app.route("/register/<fixed_role>", methods=["GET", "POST"])
    def register(fixed_role):
        fixed_role = fixed_role.upper() if fixed_role and fixed_role in ROLES else None

        if request.method == "POST":
            full_name = request.form["full_name"].strip()
            email = request.form["email"].strip().lower()
            phone = request.form["phone"].strip()
            password = request.form["password"]
            confirm_password = request.form["confirm_password"]
            role = request.form.get("role", "PATIENT")
            if role not in ROLES:
                role = "PATIENT"

            # Password confirmation check
            if password != confirm_password:
                flash("Passwords do not match.", "danger")
                return redirect(request.url)

            # Check if email already exists
            if mongo.db.users.find_one({"email": email}):
                flash("Email already registered.", "danger")
                return redirect(request.url)

            # Hash password and insert user
            hashed = generate_password_hash(password)

            # Generate a Patient ID if registering as patient
            patient_id_value = None
            if role == "PATIENT":
                # Strategy: count existing patients to create a sequential PID like PID0001
                existing_patients = mongo.db.users.count_documents({"role": "PATIENT", "patient_id": {"$exists": True}})
                seq = existing_patients + 1
                patient_id_value = f"PID{seq:04d}"

            mongo.db.users.insert_one({
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "password": hashed,
                "role": role,
                "patient_id": patient_id_value,
                "created_at": datetime.utcnow()
            })

            flash("Account created successfully. Please login.", "success")
            return redirect(url_for("login"))

        return render_template("register.html", roles=ROLES, fixed_role=fixed_role)
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form["email"].strip().lower()
            password = request.form["password"]

            # Check if user exists
            user = mongo.db.users.find_one({"email": email})
            if not user:
                flash("No user found with this email.", "danger")
                return redirect(url_for("login"))

            # Password check
            if not check_password_hash(user["password"], password):
                flash("Invalid password.", "danger")
                return redirect(url_for("login"))

            # Login success → create session
            session["user_id"] = str(user["_id"])
            session["role"] = user["role"]
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))

        return render_template("login.html", roles=ROLES)


    @app.route("/logout")
    def logout():
        session.clear()
        flash("Logged out.", "info")
        return redirect(url_for("index"))

    # ---- Dashboard ----
    @app.route("/dashboard")
    @login_required
    def dashboard():
        user_role = session.get("role")
        
        if user_role == "PATIENT":
            # Patient-specific dashboard
            user = current_user()
            patient_appointments = list(mongo.db.appointments.find({"patient_email": user["email"]}).sort("_id", -1).limit(5))
            patient_invoices = list(mongo.db.invoices.find({"patient_email": user["email"]}).sort("_id", -1).limit(5))
            patient_complaints = list(mongo.db.complaints.find({"patient_email": user["email"]}).sort("_id", -1).limit(5))
            return render_template("patient_dashboard.html", appointments=patient_appointments, invoices=patient_invoices, complaints=patient_complaints)
        
        # Admin/Doctor/Billing dashboard
        pcount = mongo.db.patients.count_documents({})
        invcount = mongo.db.invoices.count_documents({})
        clcount = mongo.db.claims.count_documents({})
        appointments = []
        
        if user_role == "DOCTOR":
            # Enhanced doctor dashboard
            user = current_user()
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("login"))
            
            doctor_name = user.get("full_name", "Unknown Doctor")
            
            # Get doctor's appointments (include requested appointments addressed to this doctor)
            doctor_appointments = list(mongo.db.appointments.find({
                "doctor_name": {"$regex": f"^{doctor_name}$", "$options": "i"}
            }).sort("_id", -1))
            
            # Get doctor's patients
            doctor_patients = list(mongo.db.appointments.find({
                "doctor_name": {"$regex": f"^{doctor_name}$", "$options": "i"}
            }).distinct("patient_name"))
            
            # Get regular OPD patients (patients with multiple appointments)
            patient_appointment_counts = {}
            for appointment in doctor_appointments:
                patient = appointment.get("patient_name", "Unknown")
                patient_appointment_counts[patient] = patient_appointment_counts.get(patient, 0) + 1
            
            regular_opd_patients = [patient for patient, count in patient_appointment_counts.items() if count > 1]
            
            # Get surgeries (if any)
            try:
                doctor_surgeries = list(mongo.db.surgeries.find({"doctor_name": doctor_name}))
            except:
                doctor_surgeries = []
            
            # Get patient gender distribution
            patient_genders = {}
            for appointment in doctor_appointments:
                patient_name = appointment.get("patient_name", "Unknown")
                # Get patient gender from users collection
                patient_user = mongo.db.users.find_one({"$or": [
                    {"full_name": patient_name},
                    {"$expr": {"$eq": [{"$concat": ["$first_name", " ", "$last_name"]}, patient_name]}}
                ]})
                if patient_user:
                    gender = patient_user.get("gender", "Unknown")
                    patient_genders[gender] = patient_genders.get(gender, 0) + 1
            
            # Get lab tests for doctor's patients
            try:
                lab_tests = list(mongo.db.lab_tests.find({"patient_name": {"$in": doctor_patients}}).sort("_id", -1))
            except:
                lab_tests = []
            
            # Calculate statistics
            total_appointments = len(doctor_appointments)
            total_patients = len(doctor_patients)
            total_surgeries = len(doctor_surgeries)
            total_operations = total_surgeries  # Assuming surgeries are operations
            
            # Ensure doctor has required fields
            if not user.get("photo_url"):
                user["photo_url"] = "https://via.placeholder.com/150"
            if not user.get("specialization"):
                user["specialization"] = "General Physician"
            
            return render_template("doctor_dashboard.html", 
                                 doctor=user,
                                 appointments=doctor_appointments[:10],
                                 total_appointments=total_appointments,
                                 total_patients=total_patients,
                                 regular_opd_patients=len(regular_opd_patients),
                                 total_surgeries=total_surgeries,
                                 total_operations=total_operations,
                                 patient_genders=patient_genders,
                                 lab_tests=lab_tests[:10])
        
        elif user_role == "ADMIN":
            # Enhanced admin dashboard with comprehensive statistics
            staff_count = mongo.db.users.count_documents({"role": {"$in": ["DOCTOR", "BILLING"]}})
            
            # Check if collections exist before querying
            try:
                surgery_count = mongo.db.surgeries.count_documents({})
            except:
                surgery_count = 0
                
            try:
                room_count = mongo.db.rooms.count_documents({})
            except:
                room_count = 0
                
            try:
                available_rooms = mongo.db.rooms.count_documents({"status": "AVAILABLE"})
            except:
                available_rooms = 0
                
            try:
                complaints_count = mongo.db.complaints.count_documents({})
            except:
                complaints_count = 0
                
            try:
                pending_complaints = mongo.db.complaints.count_documents({"status": "PENDING"})
            except:
                pending_complaints = 0
            
            # Patient statistics for charts (predefined sample data)
            # Using current last 7 days for labels, but fixed counts for values
            predefined_patient_counts = [5, 8, 6, 10, 7, 9, 12]
            predefined_recovery_counts = [2, 3, 1, 4, 2, 5, 3]
            patient_stats = []
            recovery_stats = []
            for i in range(7):  # Last 7 days
                date = datetime.utcnow() - timedelta(days=6-i)
                label = date.strftime("%Y-%m-%d")
                patient_stats.append({
                    "date": label,
                    "count": predefined_patient_counts[i]
                })
                recovery_stats.append({
                    "date": label,
                    "count": predefined_recovery_counts[i]
                })
            
            # Recent complaints
            try:
                recent_complaints = list(mongo.db.complaints.find().sort("_id", -1).limit(5))
            except:
                recent_complaints = []
            
            # Recent surgeries
            try:
                recent_surgeries = list(mongo.db.surgeries.find().sort("_id", -1).limit(5))
            except:
                recent_surgeries = []
            
            # Room status
            try:
                room_status = list(mongo.db.rooms.find())
            except:
                room_status = []
            
            return render_template("admin_dashboard.html", 
                                 pcount=pcount, 
                                 invcount=invcount, 
                                 clcount=clcount,
                                 staff_count=staff_count,
                                 surgery_count=surgery_count,
                                 room_count=room_count,
                                 available_rooms=available_rooms,
                                 complaints_count=complaints_count,
                                 pending_complaints=pending_complaints,
                                 patient_stats=patient_stats,
                                 recovery_stats=recovery_stats,
                                 recent_complaints=recent_complaints,
                                 recent_surgeries=recent_surgeries,
                                 room_status=room_status)
        
        elif user_role == "BILLING":
            # Enhanced billing dashboard
            try:
                inventory_items = list(mongo.db.inventory.find().sort("_id", -1).limit(10))
            except:
                inventory_items = []
            
            try:
                recent_purchases = list(mongo.db.patient_purchases.find().sort("_id", -1).limit(10))
            except:
                recent_purchases = []
            
            try:
                pending_claims = list(mongo.db.claims.find({"status": "SUBMITTED"}).sort("_id", -1).limit(5))
            except:
                pending_claims = []
            
            # Calculate billing statistics
            total_revenue = sum(inv.get("total", 0) for inv in mongo.db.invoices.find())
            pending_amount = sum(inv.get("total", 0) for inv in mongo.db.invoices.find({"status": "PENDING"}))
            paid_amount = sum(inv.get("total", 0) for inv in mongo.db.invoices.find({"status": "PAID"}))
            
            return render_template("billing_dashboard.html", 
                                 pcount=pcount, 
                                 invcount=invcount, 
                                 clcount=clcount,
                                 inventory_items=inventory_items,
                                 recent_purchases=recent_purchases,
                                 pending_claims=pending_claims,
                                 total_revenue=total_revenue,
                                 pending_amount=pending_amount,
                                 paid_amount=paid_amount)
        
        # Default dashboard for other roles
        return render_template("dashboard.html", pcount=pcount, invcount=invcount, clcount=clcount, appointments=appointments)

    # ---- Patients ----
    @app.route("/patients", methods=["GET","POST"])
    @login_required
    def patients():
        if request.method == "POST":
            if session.get("role") not in ["ADMIN","BILLING"]:
                flash("Only Billing/Admin can add patients.", "danger")
                return redirect(url_for("patients"))
            data = {
                "first_name": request.form.get("first_name","").strip(),
                "last_name": request.form.get("last_name","").strip(),
                "gender": request.form.get("gender"),
                "age": int(request.form.get("age", 0) or 0),
                "phone": request.form.get("phone"),
                "email": request.form.get("pemail"),
                "address": request.form.get("address"),
                "insurance_id": request.form.get("insurance_id"),
                "created_at": datetime.utcnow(),
            }
            mongo.db.patients.insert_one(data)
            flash("Patient added.", "success")
            return redirect(url_for("patients"))
        # Get patients from both collections (legacy patients and users with PATIENT role)
        plist = list(mongo.db.patients.find().sort("_id",-1))
        patient_users = list(mongo.db.users.find({"role": "PATIENT"}).sort("_id",-1))
        
        # Convert patient users to the same format as legacy patients
        for user in patient_users:
            patient_data = {
                "_id": user["_id"],
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "email": user.get("email", ""),
                "phone": user.get("phone", ""),
                "address": user.get("address", ""),
                "date_of_birth": user.get("date_of_birth", ""),
                "gender": user.get("gender", ""),
                "emergency_contact": user.get("emergency_contact", "")
            }
            plist.append(patient_data)
        
        return render_template("patients.html", patients=plist)

    # ---- Appointments ----
    @app.route("/appointments", methods=["GET","POST"])
    @login_required
    def appointments():
        if request.method == "POST":
            if session.get("role") not in ["ADMIN","DOCTOR"]:
                flash("Only Doctor/Admin can create appointments.", "danger")
                return redirect(url_for("appointments"))
            patient = mongo.db.patients.find_one({"_id": ObjectId(request.form["patient_id"])})
            data = {
                "patient_id": ObjectId(request.form["patient_id"]),
                "patient_email": patient.get("email", "") if patient else "",
                "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip() if patient else "",
                "doctor_name": request.form["doctor_name"],
                "date": request.form["date"],
                "time": request.form["time"],
                "notes": request.form.get("notes",""),
                "created_at": datetime.utcnow()
            }
            mongo.db.appointments.insert_one(data)
            flash("Appointment created.", "success")
            return redirect(url_for("appointments"))
        # Get patients from both collections (legacy patients and users with PATIENT role)
        plist = list(mongo.db.patients.find())
        patient_users = list(mongo.db.users.find({"role": "PATIENT"}))
        
        # Convert patient users to the same format as legacy patients
        for user in patient_users:
            patient_data = {
                "_id": user["_id"],
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "email": user.get("email", ""),
                "phone": user.get("phone", ""),
                "address": user.get("address", ""),
                "date_of_birth": user.get("date_of_birth", ""),
                "gender": user.get("gender", ""),
                "emergency_contact": user.get("emergency_contact", "")
            }
            plist.append(patient_data)
        
        alist = list(mongo.db.appointments.find().sort("_id",-1))
        
        # Get current user for doctor info
        current_user_data = current_user()
        
        return render_template("appointments.html", patients=plist, appointments=alist, doctor=current_user_data)

    # ---- Inventory ----
    @app.route("/inventory", methods=["GET","POST"])
    @login_required
    def inventory():
        if request.method == "POST":
            if session.get("role") not in ["ADMIN","BILLING"]:
                flash("Only Billing/Admin can add items.", "danger")
                return redirect(url_for("inventory"))
            data = {
                "sku": request.form["sku"].strip(),
                "name": request.form["name"].strip(),
                "stock_qty": int(request.form.get("stock_qty",0) or 0),
                "unit_cost": float(request.form.get("unit_cost",0) or 0),
                "unit_price": float(request.form.get("unit_price",0) or 0),
                "low_stock_threshold": int(request.form.get("low_stock_threshold",5) or 5),
                "is_drug": True if request.form.get("is_drug")=="on" else False,
                "created_at": datetime.utcnow()
            }
            if mongo.db.inventory.find_one({"sku": data["sku"]}):
                flash("SKU already exists.", "danger")
            else:
                mongo.db.inventory.insert_one(data)
                flash("Item added.", "success")
            return redirect(url_for("inventory"))
        ilist = list(mongo.db.inventory.find().sort("_id",-1))
        return render_template("inventory.html", items=ilist)

    # ---- Billing / Invoices ----
    def compute_totals(items, discount=0.0, tax=0.0, insurance_deduction=0.0):
        subtotal = sum(float(i["quantity"]) * float(i["unit_price"]) for i in items)
        total = max(0.0, subtotal - float(discount) - float(insurance_deduction))
        total = total + float(tax)
        return subtotal, total

    @app.route("/billing", methods=["GET","POST"])
    @login_required
    def billing():
        if request.method == "POST":
            if session.get("role") not in ["ADMIN","BILLING"]:
                flash("Only Billing/Admin can generate invoices.", "danger")
                return redirect(url_for("billing"))
            patient_id = ObjectId(request.form["patient_id"])
            # Try to find patient in both collections
            patient = mongo.db.patients.find_one({"_id": patient_id})
            if not patient:
                patient = mongo.db.users.find_one({"_id": patient_id, "role": "PATIENT"})
            items = []
            rows = int(request.form.get("rows","1"))
            for i in range(rows):
                itype = request.form.get(f"item_type_{i}","").strip() or "OTHER"
                desc = request.form.get(f"description_{i}","").strip()
                qty = float(request.form.get(f"quantity_{i}","1") or 1)
                price = float(request.form.get(f"unit_price_{i}","0") or 0)
                items.append({"item_type": itype, "description": desc, "quantity": qty, "unit_price": price, "total_price": qty*price})

            discount = float(request.form.get("discount",0) or 0)
            tax = float(request.form.get("tax",0) or 0)
            # Auto-apply insurance deduction from latest claim for this patient if not provided
            if request.form.get("insurance_deduction") and float(request.form.get("insurance_deduction",0) or 0) > 0:
                insurance_deduction = float(request.form.get("insurance_deduction",0) or 0)
                applied_policy_number = None
            else:
                latest_claim_cursor = mongo.db.claims.find({"patient_id": patient_id, "status": {"$in": ["APPROVED", "SUBMITTED", "PENDING"]}}).sort("submitted_at", -1).limit(1)
                latest_claim = next(latest_claim_cursor, None)
                insurance_deduction = float(latest_claim.get("claim_amount", 0) or 0) if latest_claim else 0.0
                applied_policy_number = latest_claim.get("policy_number") if latest_claim else None
            subtotal, total = compute_totals(items, discount, tax, insurance_deduction)

            # Determine patient ID string for display (from users.patient_id or legacy patients._id)
            pid_str = None
            if patient:
                pid_str = patient.get("patient_id")
                if not pid_str:
                    # fallback to stringified ObjectId
                    pid_str = str(patient.get("_id", ""))

            inv = {
                "patient_id": patient_id,
                "patient_id_str": pid_str,
                "patient_email": patient.get("email", "") if patient else "",
                "patient_name": f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip() if patient and (patient.get('first_name') or patient.get('last_name')) else (patient.get('full_name', '') if patient else ""),
                "treating_doctor": request.form.get("treating_doctor", ""),
                "disease": request.form.get("disease", ""),
                "treatment_date": request.form.get("treatment_date", ""),
                "date": datetime.utcnow(),
                "items": items,
                "subtotal": subtotal,
                "discount": discount,
                "tax": tax,
                "insurance_deduction": insurance_deduction,
                "insurance_policy_number": applied_policy_number,
                "total": total,
                "status": "PENDING",
            }
            res = mongo.db.invoices.insert_one(inv)
            flash(f"Invoice #{res.inserted_id} created.", "success")
            return redirect(url_for("invoice_view", invoice_id=str(res.inserted_id)))

        # Get patients from both collections (legacy patients and users with PATIENT role)
        plist = list(mongo.db.patients.find())
        patient_users = list(mongo.db.users.find({"role": "PATIENT"}))
        
        # Convert patient users to the same format as legacy patients
        for user in patient_users:
            patient_data = {
                "_id": user["_id"],
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "email": user.get("email", ""),
                "phone": user.get("phone", ""),
                "address": user.get("address", ""),
                "date_of_birth": user.get("date_of_birth", ""),
                "gender": user.get("gender", ""),
                "emergency_contact": user.get("emergency_contact", "")
            }
            plist.append(patient_data)
        
        return render_template("billing.html", patients=plist)

    @app.route("/invoice/<invoice_id>")
    @login_required
    def invoice_view(invoice_id):
        inv = mongo.db.invoices.find_one({"_id": ObjectId(invoice_id)})
        if not inv:
            flash("Invoice not found.", "danger")
            return redirect(url_for("billing"))
        # Try to find patient in both collections
        patient = mongo.db.patients.find_one({"_id": inv["patient_id"]})
        if not patient:
            patient = mongo.db.users.find_one({"_id": inv["patient_id"], "role": "PATIENT"})

        # Find any claim linked to this patient (patient-centric claims)
        claim = mongo.db.claims.find_one({"patient_id": inv["patient_id"]})
        return render_template("invoice_view.html", inv=inv, patient=patient, claim=claim)

    @app.route("/invoice/<invoice_id>/pay", methods=["POST"])
    @login_required
    @role_required("ADMIN","BILLING")
    def invoice_pay(invoice_id):
        mongo.db.invoices.update_one({"_id": ObjectId(invoice_id)}, {"$set": {"status": "PAID"}})
        flash("Invoice marked as PAID.", "success")
        return redirect(url_for("invoice_view", invoice_id=invoice_id))

    @app.route("/invoice/<invoice_id>/pdf")
    @login_required
    def invoice_pdf(invoice_id):
        inv = mongo.db.invoices.find_one({"_id": ObjectId(invoice_id)})
        if not inv:
            flash("Invoice not found.", "danger")
            return redirect(url_for("billing"))
        # Try to find patient in both collections
        patient = mongo.db.patients.find_one({"_id": inv["patient_id"]})
        if not patient:
            patient = mongo.db.users.find_one({"_id": inv["patient_id"], "role": "PATIENT"})

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4
        
        # Header Section
        c.setFillColorRGB(0.1, 0.3, 0.6)  # Dark blue background
        c.rect(0, h-80, w, 80, fill=True, stroke=False)
        
        # Hospital Name and Logo Area
        c.setFillColorRGB(1, 1, 1)  # White text
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(w/2, h-35, "MedConnect Hospital")
        
        c.setFont("Helvetica", 12)
        c.drawCentredString(w/2, h-55, "Advanced Medical Care & Treatment")
        c.drawCentredString(w/2, h-70, "123 Healthcare Avenue, Medical City, MC 12345 | Phone: (555) 123-4567")
        
        # Invoice Title (centered)
        y = h - 120
        c.setFillColorRGB(0, 0, 0)  # Black text
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(w/2, y, "INVOICE")
        
        # Invoice Details Box
        y -= 30
        c.setStrokeColorRGB(0.7, 0.7, 0.7)
        c.setLineWidth(1)
        c.rect(50, y-80, w-100, 80, fill=False, stroke=True)
        
        # Invoice Info
        c.setFont("Helvetica-Bold", 12)
        c.drawString(60, y-20, f"Invoice ID: {str(inv['_id'])}")
        # Guard against non-datetime 'date' values
        inv_date = inv.get('date')
        if isinstance(inv_date, str):
            # Attempt to parse ISO string
            try:
                from datetime import datetime as _dt
                inv_date = _dt.fromisoformat(inv_date)
            except Exception:
                inv_date = None
        
        if not isinstance(inv_date, datetime):
            inv_date = datetime.utcnow()
        
        c.drawString(60, y-35, f"Invoice Date: {inv_date.strftime('%B %d, %Y')}")
        
        # Patient Information Section
        y -= 100
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "PATIENT INFORMATION")
        
        y -= 25
        c.setFont("Helvetica", 11)
        
        # Handle different patient name formats
        if patient and (patient.get('first_name') or patient.get('last_name')):
            patient_name = f"{patient.get('first_name','')} {patient.get('last_name','')}".strip()
        else:
            patient_name = patient.get('full_name', 'Unknown Patient') if patient else 'Unknown Patient'
        
        c.drawString(50, y, f"Name: {patient_name}")
        y -= 15
        # Prefer human-friendly patient_id if present; fallback to ObjectId
        pid_display = (patient.get('patient_id') if patient else None) or inv.get('patient_id_str') or (str(patient['_id']) if patient else 'N/A')
        c.drawString(50, y, f"Patient ID: {pid_display}")
        y -= 15
        c.drawString(50, y, f"Email: {patient.get('email', 'N/A') if patient else 'N/A'}")
        y -= 15
        c.drawString(50, y, f"Phone: {patient.get('phone', 'N/A') if patient else 'N/A'}")
        y -= 15
        c.drawString(50, y, f"Address: {patient.get('address', 'N/A') if patient else 'N/A'}")

        # Insurance Claim Information Section (if exists) - patient-centric
        if claim := mongo.db.claims.find_one({"patient_id": inv.get("patient_id")}, sort=[("submitted_at", -1)]):
            y -= 40
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y, "INSURANCE CLAIM")
            y -= 20
            c.setFont("Helvetica", 11)
            c.drawString(50, y, f"Insurer: {claim.get('insurer', 'N/A')}")
            y -= 15
            c.drawString(50, y, f"Policy #: {claim.get('policy_number', 'N/A')}")
            y -= 15
            c.drawString(50, y, f"Status: {claim.get('status', 'SUBMITTED')}")
            if claim.get('eob_notes'):
                y -= 15
                c.drawString(50, y, f"EOB Notes: {claim.get('eob_notes')[:80]}")
        
        # Medical Information Section
        y -= 40
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "MEDICAL INFORMATION")
        
        y -= 25
        # Table header
        c.setFillColorRGB(0.9, 0.9, 0.9)
        c.rect(50, y-20, w-100, 20, fill=True, stroke=True)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(60, y-15, "Item Type")
        c.drawString(150, y-15, "Description")
        c.drawString(350, y-15, "Qty")
        c.drawString(400, y-15, "Unit Price")
        c.drawString(480, y-15, "Total")
        
        # Items
        y -= 30
        c.setFont("Helvetica", 9)
        for it in inv["items"]:
            if y < 100:  # New page if needed
                c.showPage()
                y = h - 50
                # Redraw table header
                c.setFillColorRGB(0.9, 0.9, 0.9)
                c.rect(50, y-20, w-100, 20, fill=True, stroke=True)
                c.setFillColorRGB(0, 0, 0)
                c.setFont("Helvetica-Bold", 10)
                c.drawString(60, y-15, "Item Type")
                c.drawString(150, y-15, "Description")
                c.drawString(350, y-15, "Qty")
                c.drawString(400, y-15, "Unit Price")
                c.drawString(480, y-15, "Total")
                y -= 30
                c.setFont("Helvetica", 9)
            
            c.rect(50, y-15, w-100, 15, fill=False, stroke=True)
            c.drawString(60, y-10, it['item_type'])
            c.drawString(150, y-10, it['description'][:30] + "..." if len(it['description']) > 30 else it['description'])
            c.drawString(350, y-10, str(it['quantity']))
            c.drawString(400, y-10, f"${it['unit_price']:.2f}")
            c.drawString(480, y-10, f"${it['total_price']:.2f}")
            y -= 20
        
        # Financial Summary
        y -= 30
        c.setFont("Helvetica-Bold", 12)
        c.drawString(400, y, "FINANCIAL SUMMARY")
        y -= 20
        c.setFont("Helvetica", 11)
        # Safely read numeric fields
        _subtotal = float(inv.get('subtotal', 0) or 0)
        _discount = float(inv.get('discount', 0) or 0)
        _ins_deduction = float(inv.get('insurance_deduction', 0) or 0)
        _tax = float(inv.get('tax', 0) or 0)
        _total = float(inv.get('total', (_subtotal - _discount - _ins_deduction + _tax)) or 0)
        
        c.drawString(400, y, f"Subtotal: ${_subtotal:.2f}")
        y -= 15
        c.drawString(400, y, f"Discount: -${_discount:.2f}")
        y -= 15
        c.drawString(400, y, f"Insurance Deduction: -${_ins_deduction:.2f}")
        y -= 15
        c.drawString(400, y, f"Tax: ${_tax:.2f}")
        y -= 20
        c.setFont("Helvetica-Bold", 14)
        c.setFillColorRGB(0.1, 0.3, 0.6)
        c.drawString(400, y, f"TOTAL: ${_total:.2f}")
        
        # Footer
        y = 80
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica", 9)
        c.drawCentredString(w/2, y, "Thank you for choosing MedConnect Hospital for your healthcare needs.")
        c.drawCentredString(w/2, y-15, "For any billing inquiries, please contact our billing department at (555) 123-4567")
        c.drawCentredString(w/2, y-30, "This invoice is generated electronically and is valid without signature.")
        
        c.showPage()
        c.save()
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"MedConnect_Invoice_{invoice_id}.pdf")

    # ---- Claims ----
    @app.route("/claims", methods=["GET","POST"])
    @login_required
    def claims():
        if request.method == "POST":
            if session.get("role") not in ["ADMIN","BILLING"]:
                flash("Only Billing/Admin can submit claims.", "danger")
                return redirect(url_for("claims"))
            # Link claim to Patient (not Invoice)
            patient_oid = ObjectId(request.form["patient_id"])
            # Fetch patient from either collection
            patient = mongo.db.patients.find_one({"_id": patient_oid})
            if not patient:
                patient = mongo.db.users.find_one({"_id": patient_oid, "role": "PATIENT"})
            # Derive display fields
            patient_id_str = (patient.get("patient_id") if patient else None) or str(patient_oid)
            data = {
                "patient_id": patient_oid,
                "patient_id_str": patient_id_str,
                "insurer": request.form["insurer"],
                "policy_number": request.form.get("policy_number",""),
                "claim_amount": float(request.form.get("claim_amount", 0) or 0),
                "diagnosis_code": request.form.get("diagnosis_code",""),
                "treatment_description": request.form.get("treatment_description",""),
                "submitted_at": datetime.utcnow(),
                "status": "SUBMITTED",
                "eob_notes": request.form.get("eob_notes", "")
            }
            mongo.db.claims.insert_one(data)
            flash("Claim submitted.", "success")
            return redirect(url_for("claims"))
        # Provide patients list to the form
        plist = list(mongo.db.patients.find())
        patient_users = list(mongo.db.users.find({"role": "PATIENT"}))
        for user in patient_users:
            patient_data = {
                "_id": user["_id"],
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "full_name": user.get("full_name", ""),
                "email": user.get("email", ""),
                "phone": user.get("phone", ""),
                "address": user.get("address", ""),
                "patient_id": user.get("patient_id")
            }
            plist.append(patient_data)
        clist = list(mongo.db.claims.find().sort("_id",-1))
        return render_template("claims.html", claims=clist, patients=plist)

    @app.route("/claims/<claim_id>/update", methods=["POST"])
    @login_required
    @role_required("ADMIN","BILLING")
    def claim_update(claim_id):
        status = request.form.get("status","SUBMITTED")
        eob_notes = request.form.get("eob_notes","")
        mongo.db.claims.update_one({"_id": ObjectId(claim_id)}, {"$set": {"status": status, "eob_notes": eob_notes}})
        flash("Claim updated.", "success")
        return redirect(url_for("claims"))

    # ---- Reports ----
    @app.route("/reports")
    @login_required
    def reports():
        since = datetime.utcnow() - timedelta(days=1)
        daily = list(mongo.db.invoices.find({"date": {"$gte": since}}))
        paid_total = sum(i.get("total",0) for i in daily if i.get("status") in ["PAID","PARTIAL"])
        pending = list(mongo.db.invoices.find({"status": {"$ne": "PAID"}}))
        return render_template("reports.html", daily_count=len(daily), paid_total=paid_total, pending_count=len(pending), pending_ids=[str(i["_id"]) for i in pending])

    # ---- Patient-specific routes ----
    @app.route("/patient/appointments", methods=["GET", "POST"])
    @login_required
    @role_required("PATIENT")
    def patient_appointments():
        user = current_user()
        if request.method == "POST":
            # Patient can request appointments
            # Normalize patient's full name (e.g., "Mary Taylor") for consistent doctor visibility
            patient_full_name = (
                user.get("full_name")
                or (f"{user.get('first_name','')} {user.get('last_name','')}".strip() if (user.get('first_name') or user.get('last_name')) else None)
                or (user.get("email", "").split("@")[0] if user.get("email") else None)
                or user.get("username")
                or "Unknown Patient"
            )
            patient_full_name = str(patient_full_name).replace(".", " ").replace("_", " ").strip().title()
            
            data = {
                "patient_email": user.get("email", ""),
                "patient_name": patient_full_name,
                "doctor_name": request.form.get("doctor_name", ""),
                "preferred_date": request.form.get("preferred_date", ""),
                "preferred_time": request.form.get("preferred_time", ""),
                "reason": request.form.get("reason", ""),
                "status": "REQUESTED",
                "created_at": datetime.utcnow()
            }
            mongo.db.appointments.insert_one(data)
            flash("Appointment request submitted successfully.", "success")
            return redirect(url_for("patient_appointments"))
        
        # Get patient's appointments
        appointments = list(mongo.db.appointments.find({"patient_email": user["email"]}).sort("_id", -1))
        return render_template("patient_appointments.html", appointments=appointments)

    @app.route("/patient/appointment-history")
    @login_required
    @role_required("PATIENT")
    def patient_appointment_history():
        user = current_user()
        appointments = list(mongo.db.appointments.find({"patient_email": user["email"]}).sort("_id", -1))
        return render_template("patient_appointment_history.html", appointments=appointments)

    @app.route("/patient/receipts")
    @login_required
    @role_required("PATIENT")
    def patient_receipts():
        user = current_user()
        invoices = list(mongo.db.invoices.find({"patient_email": user["email"]}).sort("_id", -1))
        return render_template("patient_receipts.html", invoices=invoices)

    @app.route("/patient/complaints", methods=["POST"])
    @login_required
    @role_required("PATIENT")
    def patient_complaint_new():
        user = current_user()
        # Normalize patient name similar to appointments
        patient_full_name = (
            user.get("full_name")
            or (f"{user.get('first_name','')} {user.get('last_name','')}".strip() if (user.get('first_name') or user.get('last_name')) else None)
            or (user.get("email", "").split("@")[0] if user.get("email") else None)
            or user.get("username")
            or "Unknown Patient"
        )
        patient_full_name = str(patient_full_name).replace(".", " ").replace("_", " ").strip().title()

        data = {
            "patient_name": patient_full_name,
            "patient_email": user.get("email", ""),
            "subject": request.form.get("subject", ""),
            "description": request.form.get("description", ""),
            "priority": request.form.get("priority", "MEDIUM"),
            "status": "PENDING",
            "created_at": datetime.utcnow()
        }
        mongo.db.complaints.insert_one(data)
        flash("Complaint submitted.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/patient/medical-history")
    @login_required
    @role_required("PATIENT")
    def patient_medical_history():
        user = current_user()
        # Get medical records (appointments, diagnoses, treatments)
        appointments = list(mongo.db.appointments.find({"patient_email": user["email"]}).sort("_id", -1))
        # For now, we'll use appointments as medical history
        # In a real system, you'd have a separate medical_records collection
        return render_template("patient_medical_history.html", appointments=appointments)

    @app.route("/patient/personal-details", methods=["GET", "POST"])
    @login_required
    @role_required("PATIENT")
    def patient_personal_details():
        user = current_user()
        if request.method == "POST":
            # Update patient details
            update_data = {
                "full_name": request.form.get("full_name", user["full_name"]),
                "phone": request.form.get("phone", user.get("phone", "")),
                "address": request.form.get("address", user.get("address", "")),
                "emergency_contact": request.form.get("emergency_contact", user.get("emergency_contact", "")),
                "emergency_phone": request.form.get("emergency_phone", user.get("emergency_phone", "")),
                "medical_conditions": request.form.get("medical_conditions", user.get("medical_conditions", "")),
                "medications": request.form.get("medications", user.get("medications", "")),
                "allergies": request.form.get("allergies", user.get("allergies", ""))
            }
            mongo.db.users.update_one({"_id": user["_id"]}, {"$set": update_data})
            flash("Personal details updated successfully.", "success")
            return redirect(url_for("patient_personal_details"))
        
        return render_template("patient_personal_details.html", user=user)

    @app.route("/patient/reports")
    @login_required
    @role_required("PATIENT")
    def patient_reports():
        user = current_user()
        # Get patient's reports (invoices, appointments summary)
        invoices = list(mongo.db.invoices.find({"patient_email": user["email"]}))
        appointments = list(mongo.db.appointments.find({"patient_email": user["email"]}))
        
        # Calculate summary statistics
        total_invoices = len(invoices)
        total_amount = sum(inv.get("total", 0) for inv in invoices)
        paid_amount = sum(inv.get("total", 0) for inv in invoices if inv.get("status") == "PAID")
        pending_amount = total_amount - paid_amount
        total_appointments = len(appointments)
        
        return render_template("patient_reports.html", 
                             total_invoices=total_invoices,
                             total_amount=total_amount,
                             paid_amount=paid_amount,
                             pending_amount=pending_amount,
                             total_appointments=total_appointments,
                             invoices=invoices,
                             appointments=appointments)

    # ---- Admin-specific routes ----
    @app.route("/admin/complaints", methods=["GET", "POST"])
    @login_required
    @role_required("ADMIN")
    def admin_complaints():
        if request.method == "POST":
            data = {
                "patient_name": request.form.get("patient_name", ""),
                "patient_email": request.form.get("patient_email", ""),
                "subject": request.form.get("subject", ""),
                "description": request.form.get("description", ""),
                "priority": request.form.get("priority", "MEDIUM"),
                "status": "PENDING",
                "created_at": datetime.utcnow()
            }
            mongo.db.complaints.insert_one(data)
            flash("Complaint recorded successfully.", "success")
            return redirect(url_for("admin_complaints"))
        
        try:
            complaints = list(mongo.db.complaints.find().sort("_id", -1))
        except:
            complaints = []
        return render_template("admin_complaints.html", complaints=complaints)

    @app.route("/admin/complaints/<complaint_id>/update", methods=["POST"])
    @login_required
    @role_required("ADMIN")
    def update_complaint(complaint_id):
        status = request.form.get("status", "PENDING")
        response = request.form.get("response", "")
        mongo.db.complaints.update_one(
            {"_id": ObjectId(complaint_id)}, 
            {"$set": {"status": status, "response": response, "updated_at": datetime.utcnow()}}
        )
        flash("Complaint updated successfully.", "success")
        return redirect(url_for("admin_complaints"))

    @app.route("/admin/surgeries", methods=["GET", "POST"])
    @login_required
    @role_required("ADMIN")
    def admin_surgeries():
        if request.method == "POST":
            data = {
                "patient_name": request.form.get("patient_name", ""),
                "patient_id": request.form.get("patient_id", ""),
                "surgery_type": request.form.get("surgery_type", ""),
                "doctor_name": request.form.get("doctor_name", ""),
                "scheduled_date": request.form.get("scheduled_date", ""),
                "scheduled_time": request.form.get("scheduled_time", ""),
                "room_number": request.form.get("room_number", ""),
                "status": "SCHEDULED",
                "notes": request.form.get("notes", ""),
                "created_at": datetime.utcnow()
            }
            mongo.db.surgeries.insert_one(data)
            flash("Surgery scheduled successfully.", "success")
            return redirect(url_for("admin_surgeries"))
        
        try:
            surgeries = list(mongo.db.surgeries.find().sort("_id", -1))
        except:
            surgeries = []
        patients = list(mongo.db.patients.find())
        try:
            rooms = list(mongo.db.rooms.find())
        except:
            rooms = []
        return render_template("admin_surgeries.html", surgeries=surgeries, patients=patients, rooms=rooms)

    @app.route("/admin/rooms", methods=["GET", "POST"])
    @login_required
    @role_required("ADMIN")
    def admin_rooms():
        if request.method == "POST":
            data = {
                "room_number": request.form.get("room_number", ""),
                "room_type": request.form.get("room_type", ""),
                "capacity": int(request.form.get("capacity", 1)),
                "status": request.form.get("status", "AVAILABLE"),
                "equipment": request.form.get("equipment", ""),
                "notes": request.form.get("notes", ""),
                "created_at": datetime.utcnow()
            }
            mongo.db.rooms.insert_one(data)
            flash("Room added successfully.", "success")
            return redirect(url_for("admin_rooms"))
        
        try:
            rooms = list(mongo.db.rooms.find().sort("room_number", 1))
        except:
            rooms = []
        return render_template("admin_rooms.html", rooms=rooms)

    @app.route("/admin/rooms/<room_id>/update", methods=["POST"])
    @login_required
    @role_required("ADMIN")
    def update_room(room_id):
        status = request.form.get("status", "AVAILABLE")
        notes = request.form.get("notes", "")
        mongo.db.rooms.update_one(
            {"_id": ObjectId(room_id)}, 
            {"$set": {"status": status, "notes": notes, "updated_at": datetime.utcnow()}}
        )
        flash("Room status updated successfully.", "success")
        return redirect(url_for("admin_rooms"))

    # ---- Billing-specific routes ----
    @app.route("/billing/patient-purchases", methods=["GET", "POST"])
    @login_required
    @role_required("BILLING", "ADMIN")
    def patient_purchases():
        if request.method == "POST":
            data = {
                "patient_id": ObjectId(request.form["patient_id"]),
                "patient_name": request.form["patient_name"],
                "inventory_items": [],
                "total_cost": 0,
                "purchase_date": datetime.utcnow(),
                "status": "COMPLETED"
            }
            
            # Process inventory items
            item_count = int(request.form.get("item_count", 1))
            total_cost = 0
            for i in range(item_count):
                item_id = request.form.get(f"item_id_{i}")
                quantity = int(request.form.get(f"quantity_{i}", 1))
                if item_id and quantity > 0:
                    item = mongo.db.inventory.find_one({"_id": ObjectId(item_id)})
                    if item:
                        item_cost = item["unit_price"] * quantity
                        data["inventory_items"].append({
                            "item_id": item_id,
                            "item_name": item["name"],
                            "sku": item["sku"],
                            "quantity": quantity,
                            "unit_price": item["unit_price"],
                            "total_price": item_cost
                        })
                        total_cost += item_cost
                        
                        # Update inventory stock
                        mongo.db.inventory.update_one(
                            {"_id": ObjectId(item_id)},
                            {"$inc": {"stock_qty": -quantity}}
                        )
            
            data["total_cost"] = total_cost
            mongo.db.patient_purchases.insert_one(data)
            flash("Purchase recorded successfully.", "success")
            return redirect(url_for("patient_purchases"))
        
        try:
            purchases = list(mongo.db.patient_purchases.find().sort("_id", -1))
        except:
            purchases = []
        patients = list(mongo.db.patients.find())
        inventory_items = list(mongo.db.inventory.find())
        return render_template("patient_purchases.html", purchases=purchases, patients=patients, inventory_items=inventory_items)

    @app.route("/billing/inventory-management", methods=["GET", "POST"])
    @login_required
    @role_required("BILLING", "ADMIN")
    def inventory_management():
        if request.method == "POST":
            data = {
                "sku": request.form["sku"].strip(),
                "name": request.form["name"].strip(),
                "category": request.form.get("category", "MEDICINE"),
                "stock_qty": int(request.form.get("stock_qty", 0) or 0),
                "unit_cost": float(request.form.get("unit_cost", 0) or 0),
                "unit_price": float(request.form.get("unit_price", 0) or 0),
                "low_stock_threshold": int(request.form.get("low_stock_threshold", 5) or 5),
                "expiry_date": request.form.get("expiry_date"),
                "supplier": request.form.get("supplier", ""),
                "is_drug": True if request.form.get("is_drug") == "on" else False,
                "created_at": datetime.utcnow()
            }
            
            if mongo.db.inventory.find_one({"sku": data["sku"]}):
                flash("SKU already exists.", "danger")
            else:
                mongo.db.inventory.insert_one(data)
                flash("Medicine added to inventory.", "success")
            return redirect(url_for("inventory_management"))
        
        try:
            inventory_items = list(mongo.db.inventory.find().sort("_id", -1))
        except:
            inventory_items = []
        return render_template("inventory_management.html", inventory_items=inventory_items)

    return app

app = create_app()
