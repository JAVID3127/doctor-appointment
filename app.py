import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from src.config import SECRET_KEY
from src.db import init_db, get_session, ScopedSession
from src.services import HospitalOPDService
from src.models import Doctor, Department, Appointment, AppointmentStatus

def create_app(custom_engine=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY

    # Initialize database
    init_db(custom_engine)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        ScopedSession.remove()

    def get_service():
        session = get_session()
        service = HospitalOPDService(session)
        service.seed_initial_data_if_empty()
        return service

    # ==========================================
    # HTML View Routes
    # ==========================================

    @app.route("/")
    def index():
        service = get_service()
        metrics = service.get_system_metrics()
        doctors = service.get_doctors()
        departments = service.get_departments()
        return render_template("index.html", metrics=metrics, doctors=doctors, departments=departments)

    @app.route("/display")
    def token_display():
        """Waiting Hall Big Screen Digital Token Board."""
        return render_template("token_display.html")

    @app.route("/track")
    def patient_token_tracker():
        """Patient live self-service token tracking portal."""
        return render_template("token_tracker.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Hospital Staff & Doctor authentication portal."""
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "").strip()

            # Predefined demo credentials for clinical roles
            if username == "admin" and password == "admin123":
                session["user"] = {"username": "admin", "role": "Administrator", "name": "Hospital Administrator"}
                return redirect(url_for("index"))
            elif username == "reception" and password == "staff123":
                session["user"] = {"username": "reception", "role": "Receptionist", "name": "OPD Receptionist"}
                return redirect(url_for("patient_booking"))
            elif username.startswith("doctor") and password == "doc123":
                doc_id = 1
                suffix = username.replace("doctor", "").strip()
                if suffix.isdigit():
                    doc_id = int(suffix)
                service = get_service()
                doc = service.get_doctor_by_id(doc_id)
                doc_name = doc.name if doc else f"Doctor {doc_id}"
                session["user"] = {"username": username, "role": "Doctor", "doctor_id": doc_id, "name": doc_name}
                return redirect(url_for("doctor_dashboard", doctor_id=doc_id))
            else:
                return render_template("login.html", error="Invalid credentials. Please use the demo credentials provided below.")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        """Clear user session and redirect home."""
        session.pop("user", None)
        return redirect(url_for("index"))

    @app.route("/doctor/<int:doctor_id>")
    def doctor_dashboard(doctor_id):
        """Doctor consultation room interface."""
        service = get_service()
        doctor = service.get_doctor_by_id(doctor_id)
        if not doctor:
            return render_template("404.html", message=f"Doctor with ID #{doctor_id} not found."), 404
        
        appointments = service.session.query(Appointment).filter(
            Appointment.doctor_id == doctor_id
        ).order_by(Appointment.slot_id).all()
        return render_template("doctor_dashboard.html", doctor=doctor, appointments=appointments)

    @app.route("/book")
    def patient_booking():
        """Patient self-service OPD booking portal."""
        service = get_service()
        departments = service.get_departments()
        doctors = service.get_doctors()
        return render_template("patient_booking.html", departments=departments, doctors=doctors)

    @app.route("/triage")
    def emergency_triage_view():
        """Emergency walk-in triage reception portal."""
        service = get_service()
        departments = service.get_departments()
        return render_template("emergency_triage.html", departments=departments)

    # ==========================================
    # REST API Endpoints
    # ==========================================

    @app.route("/api/metrics", methods=["GET"])
    def api_metrics():
        service = get_service()
        return jsonify(service.get_system_metrics())

    @app.route("/api/departments", methods=["GET"])
    def api_departments():
        service = get_service()
        depts = service.get_departments()
        return jsonify([d.to_dict() for d in depts])

    @app.route("/api/doctors", methods=["GET"])
    def api_doctors():
        service = get_service()
        dept_id = request.args.get("dept_id", type=int)
        doctors = service.get_doctors(dept_id=dept_id)
        return jsonify([d.to_dict() for d in doctors])

    @app.route("/api/doctors/<int:doctor_id>", methods=["GET"])
    def api_doctor_detail(doctor_id):
        service = get_service()
        doctor = service.get_doctor_by_id(doctor_id)
        if not doctor:
            return jsonify({"error": "Doctor not found"}), 404
        return jsonify(doctor.to_dict())

    @app.route("/api/doctors/<int:doctor_id>/slots", methods=["GET"])
    def api_doctor_slots(doctor_id):
        service = get_service()
        slots = service.get_available_slots(doctor_id)
        return jsonify([s.to_dict() for s in slots])

    @app.route("/api/doctors/<int:doctor_id>/appointments", methods=["GET"])
    def api_doctor_appointments(doctor_id):
        service = get_service()
        appts = service.session.query(Appointment).filter(
            Appointment.doctor_id == doctor_id
        ).all()
        return jsonify([a.to_dict() for a in appts])

    @app.route("/api/appointments", methods=["POST"])
    def api_book_appointment():
        service = get_service()
        data = request.get_json() or {}
        required = ["name", "phone", "age", "doctor_id", "slot_id"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        try:
            result = service.book_appointment(
                name=data["name"],
                phone=data["phone"],
                age=int(data["age"]),
                gender=data.get("gender", "Other"),
                doctor_id=int(data["doctor_id"]),
                slot_id=int(data["slot_id"]),
                lead_days=int(data.get("lead_days", 1)),
                sms_sent=bool(data.get("sms_sent", True)),
                email=data.get("email")
            )
            return jsonify({"success": True, "data": result}), 201
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/appointments/<int:appointment_id>/status", methods=["PATCH"])
    def api_update_appointment_status(appointment_id):
        service = get_service()
        data = request.get_json() or {}
        new_status = data.get("status")
        if not new_status:
            return jsonify({"error": "Field 'status' is required"}), 400

        try:
            result = service.update_status(appointment_id, new_status)
            return jsonify({"success": True, "data": result})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/triage", methods=["POST"])
    def api_register_triage():
        service = get_service()
        data = request.get_json() or {}
        required = ["patient_name", "phone", "dept_id"]
        for field in required:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        try:
            result = service.register_emergency_triage(
                patient_name=data["patient_name"],
                phone=data["phone"],
                dept_id=int(data["dept_id"]),
                severity=int(data.get("severity", 1))
            )
            return jsonify({"success": True, "data": result}), 201
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/doctors/<int:doctor_id>/leave", methods=["POST"])
    def api_doctor_leave(doctor_id):
        service = get_service()
        try:
            result = service.trigger_doctor_leave(doctor_id)
            return jsonify({"success": True, "data": result})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @app.route("/api/queue/token-board", methods=["GET"])
    def api_token_board():
        service = get_service()
        board = service.get_waiting_hall_token_board()
        return jsonify({"timestamp": os.getenv("OPD_TIME", "Live"), "board": board})

    @app.route("/api/queue/track", methods=["GET"])
    def api_track_token():
        query = request.args.get("query", "").strip()
        if not query:
            return jsonify({"success": False, "error": "Query string (token or phone) is required"}), 400
        service = get_service()
        results = service.lookup_patient_token(query)
        return jsonify({"success": True, "count": len(results), "results": results})

    # ==========================================
    # Digital E-Prescription Endpoints
    # ==========================================

    @app.route("/prescription/<int:appointment_id>")
    def view_prescription(appointment_id):
        """Renders printable, official hospital E-Prescription slip."""
        service = get_service()
        rx = service.get_prescription(appointment_id)
        if not rx:
            return render_template("404.html", message=f"No prescription has been issued yet for Appointment #{appointment_id}."), 404
        return render_template("prescription_slip.html", rx=rx)

    @app.route("/api/appointments/<int:appointment_id>/prescription", methods=["GET", "POST"])
    def api_prescription_manage(appointment_id):
        service = get_service()
        if request.method == "POST":
            data = request.get_json() or {}
            diagnosis = data.get("diagnosis", "").strip()
            medicines = data.get("medicines", "").strip()
            if not diagnosis or not medicines:
                return jsonify({"success": False, "error": "Both 'diagnosis' and 'medicines' are required."}), 400
            try:
                rx = service.save_prescription(
                    appointment_id=appointment_id,
                    diagnosis=diagnosis,
                    medicines=medicines,
                    advice=data.get("advice"),
                    follow_up_days=int(data.get("follow_up_days", 7))
                )
                return jsonify({"success": True, "data": rx})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 400
        else:
            rx = service.get_prescription(appointment_id)
            if not rx:
                return jsonify({"success": False, "error": "Prescription not found"}), 404
            return jsonify({"success": True, "data": rx})

    # ==========================================
    # Explainable AI (XAI) Endpoints
    # ==========================================

    @app.route("/api/appointments/<int:appointment_id>/xai-explain", methods=["GET"])
    def api_xai_explain(appointment_id):
        service = get_service()
        appt = service.session.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
        if not appt:
            return jsonify({"success": False, "error": "Appointment not found"}), 404
        p = appt.patient
        explanation = service.explain_no_show_risk(
            lead_days=1,
            past_ratio=p.no_show_ratio,
            sms_sent=True,
            age=p.age
        )
        return jsonify({"success": True, "data": explanation})

    # ==========================================
    # AI Symptom-to-Specialty Triage Endpoint
    # ==========================================

    @app.route("/api/ai/symptom-triage", methods=["POST"])
    def api_symptom_triage():
        data = request.get_json() or {}
        symptoms = data.get("symptoms", "").strip()
        if not symptoms:
            return jsonify({"success": False, "error": "Please describe symptoms to analyze."}), 400
        service = get_service()
        result = service.ai_symptom_triage(symptoms)
        return jsonify({"success": True, "data": result})

    # ==========================================
    # Cross-Doctor Workload Rebalance Endpoint
    # ==========================================

    @app.route("/api/departments/<int:dept_id>/rebalance", methods=["POST"])
    def api_rebalance_workload(dept_id):
        service = get_service()
        try:
            result = service.rebalance_department_workload(dept_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    # ==========================================
    # HL7 FHIR v4 Resource Export Endpoint
    # ==========================================

    @app.route("/api/fhir/Appointment/<int:appointment_id>", methods=["GET"])
    def api_fhir_appointment(appointment_id):
        service = get_service()
        try:
            fhir_resource = service.export_fhir_appointment(appointment_id)
            return jsonify(fhir_resource)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 404

    # ==========================================
    # Online ML Retraining Loop Endpoint
    # ==========================================

    @app.route("/api/ml/retrain", methods=["POST"])
    def api_ml_retrain():
        service = get_service()
        try:
            result = service.retrain_ml_model()
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500


    @app.errorhandler(404)
    def handle_404(e):
        return render_template("404.html", message="The requested clinical page or resource could not be found."), 404

    @app.errorhandler(500)
    def handle_500(e):
        return render_template("404.html", message="An internal OPD server error occurred. Please refresh or retry."), 500

    return app

if __name__ == "__main__":
    app = create_app()
    print("=" * 65)
    print("🏥 SMART OPD SCHEDULING SYSTEM - WEB APPLICATION (WEEK 6)")
    print("=" * 65)
    print("🌐 Dashboard Portal:      http://127.0.0.1:5000/")
    print("📺 Waiting Hall Display:  http://127.0.0.1:5000/display")
    print("📅 Patient Booking:       http://127.0.0.1:5000/book")
    print("🚨 Emergency Triage:      http://127.0.0.1:5000/triage")
    print("👨‍⚕️ Doctor OPD Rooms:     http://127.0.0.1:5000/doctor/1")
    print("=" * 65)
    app.run(host="0.0.0.0", port=5000, debug=True)
