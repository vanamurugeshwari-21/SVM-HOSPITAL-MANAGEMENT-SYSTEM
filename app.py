from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
DB = "hospital.db"
def query(sql, params=(), one=False):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.commit()
    con.close()
    return (rows[0] if rows else None) if one else rows
def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT)""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS doctors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        specialty TEXT,
        email TEXT UNIQUE,
        password TEXT)""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        age INTEGER,
        gender TEXT,
        height REAL,
        weight REAL)""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor_id INTEGER,
        date TEXT,
        time TEXT,
        status TEXT DEFAULT 'Pending')""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS prescriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        doctor_name TEXT,
        patient_name TEXT,
        age INTEGER,
        height REAL,
        weight REAL,
        medicines TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    con.commit()
    con.close()


# ------------------ SEED ADMIN ------------------
def seed_admin():
    if query("SELECT * FROM admins"):
        return
    query(
        "INSERT INTO admins (username,password) VALUES (?,?)",
        ("svanam", "admin@2110")
    )


# ------------------ SEED DOCTORS ------------------
doctors = [
    ("Dr. John Anderson","Cardiology","john@gmail.com","svmhospital123"),
    ("Dr. Emma Wilson","Neurology","emma@gmail.com","svmhospital123"),
    ("Dr. Michael Roberts","Orthopedics","michael@gmail.com","svmhospital123"),
    ("Dr. Olivia Johnson","Dermatology","olivia@gmail.com","svmhospital123"),
    ("Dr. William Smith","Pediatrics","william@gmail.com","svmhospital123"),
    ("Dr. Sophia Brown","Gynecology","sophia@gmail.com","svmhospital123"),
    ("Dr. James Davis","Oncology","james@gmail.com","svmhospital123"),
    ("Dr. Isabella Martinez","Psychiatry","isabella@gmail.com","svmhospital123"),
    ("Dr. Benjamin Lee","Radiology","benjamin@gmail.com","svmhospital123"),
    ("Dr. Mia Taylor","Gastroenterology","mia@gmail.com","svmhospital123")
]

def seed_doctors():
    if query("SELECT * FROM doctors"):
        return
    for d in doctors:
        query(
            "INSERT INTO doctors (name,specialty,email,password) VALUES (?,?,?,?)",
            d
        )


# ------------------ INIT ------------------
init_db()
seed_admin()
seed_doctors()


# ------------------ PATIENTS ------------------
@app.route("/patients", methods=["GET", "POST"])
def patients():
    if request.method == "POST":
        data = request.json

        exists = query(
            "SELECT * FROM patients WHERE email=?",
            (data.get("email"),),
            one=True
        )

        if exists:
            return jsonify({"error": "Patient with this email already exists"}), 409

        query("""
            INSERT INTO patients(name,email,age,gender,height,weight)
            VALUES(?,?,?,?,?,?)
        """, (
            data.get("name"),
            data.get("email"),
            data.get("age"),
            data.get("gender"),
            data.get("height"),
            data.get("weight")
        ))

        return jsonify({"msg": "Patient saved"}), 201

    return jsonify([dict(r) for r in query("SELECT * FROM patients")])


# ------------------ APPOINTMENTS ------------------
@app.route("/appointments", methods=["GET", "POST"])
def appointments():
    if request.method == "POST":
        d = request.json
        query("""
            INSERT INTO appointments(patient_id,doctor_id,date,time,status)
            VALUES(?,?,?,?,?)
        """, (
            d["patient_id"],
            d["doctor_id"],
            d["date"],
            d["time"],
            "Pending"
        ))
        return jsonify({"msg": "Appointment booked"}), 201

    email = request.args.get("email")
    doctor = request.args.get("doctor")

    if email:
        rows = query("""
            SELECT a.id, d.name AS doctor,
                   a.date, a.time, a.status
            FROM appointments a
            JOIN patients p ON a.patient_id=p.id
            JOIN doctors d ON a.doctor_id=d.id
            WHERE p.email=?
        """, (email,))
        return jsonify([dict(r) for r in rows])

    if doctor:
        rows = query("""
            SELECT a.id, p.id AS patient_id,
                   p.name AS patient,
                   a.date, a.time, a.status
            FROM appointments a
            JOIN patients p ON a.patient_id=p.id
            JOIN doctors d ON a.doctor_id=d.id
            WHERE d.name=?
        """, (doctor,))
        return jsonify([dict(r) for r in rows])

    rows = query("""
        SELECT a.id, p.name AS patient,
               d.name AS doctor,
               a.date, a.time, a.status
        FROM appointments a
        JOIN patients p ON a.patient_id=p.id
        JOIN doctors d ON a.doctor_id=d.id
    """)
    return jsonify([dict(r) for r in rows])


# --------- APPROVE / REJECT ----------
@app.route("/appointments/<int:id>/status", methods=["PUT"])
def update_status(id):
    status = request.json.get("status")

    if status not in ["Approved", "Rejected"]:
        return jsonify({"error": "Invalid status"}), 400

    query(
        "UPDATE appointments SET status=? WHERE id=?",
        (status, id)
    )
    return jsonify({"msg": "Status updated"})


# ------------------ PRESCRIPTIONS ------------------
@app.route("/prescriptions", methods=["GET", "POST"])
def prescriptions():
    if request.method == "POST":
        d = request.json
        query("""
            INSERT INTO prescriptions
            (doctor_name, patient_name, age, height, weight, medicines)
            VALUES (?,?,?,?,?,?)
        """, (
            d["doctorName"],
            d["patientName"],
            d.get("age"),
            d.get("height"),
            d.get("weight"),
            d["medicines"]
        ))
        return jsonify({"msg": "Prescription saved"}), 201

    return jsonify([
        dict(r) for r in query(
            "SELECT * FROM prescriptions ORDER BY created_at DESC"
        )
    ])


# ------------------ LOGIN ------------------
@app.route("/login", methods=["POST"])
def login():
    d = request.json

    admin = query(
        "SELECT * FROM admins WHERE username=? AND password=?",
        (d["username"], d["password"]),
        one=True
    )
    if admin:
        return jsonify({"role": "admin", "username": admin["username"]})

    doctor = query(
        "SELECT * FROM doctors WHERE email=? AND password=?",
        (d["username"], d["password"]),
        one=True
    )
    if doctor:
        return jsonify({
            "role": "doctor",
            "doctorName": doctor["name"],
            "specialty": doctor["specialty"]
        })

    return jsonify({"message": "Invalid login"}), 401


# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True, port=8000)
