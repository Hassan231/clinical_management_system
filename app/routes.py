# Route handlers for the Clinical Management System.
# All routes are grouped under a single Blueprint named 'main'.
# Each route handles one page/feature and follows the POST-Redirect-GET pattern
# to prevent duplicate form submissions on browser refresh.

from datetime import datetime

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import func  # Used for aggregate SQL functions like SUM() in reports

from . import db
from .models import (
    Appointment,
    BilledService,
    Doctor,
    DoctorShift,
    InventoryBatch,
    Medication,
    Patient,
    Prescription,
    PrescriptionItem,
    StockTransaction,
    Visit,
)

# Create the blueprint; all route URLs and url_for() calls use the "main" namespace
main_bp = Blueprint("main", __name__)


# ── HELPER ────────────────────────────────────────────────────────────────────
def parse_datetime(value):
    """Convert an HTML datetime-local string ('YYYY-MM-DDTHH:MM') to a Python datetime.
    Returns None if the value is empty or not provided."""
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M")


# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@main_bp.route("/")
def index():
    """Home page — shows summary counts for the five main entities."""
    metrics = {
        "doctors": Doctor.query.count(),          # Total doctors registered
        "patients": Patient.query.count(),        # Total patients registered
        "appointments": Appointment.query.count(), # Total appointments booked
        "visits": Visit.query.count(),            # Total visit records created
        "medications": Medication.query.count(),  # Total medications in the master list
    }
    return render_template("index.html", metrics=metrics)


# ── DOCTORS ───────────────────────────────────────────────────────────────────
@main_bp.route("/doctors", methods=["GET", "POST"])
def doctors():
    """List all doctors (GET) or add a new doctor (POST)."""
    if request.method == "POST":
        doctor = Doctor(
            full_name=request.form["full_name"],          # Required: doctor's full name
            specialty=request.form["specialty"],          # Required: medical specialty
            department=request.form["department"],        # Required: hospital department
            qualifications=request.form["qualifications"], # Required: degrees/certifications
            phone=request.form.get("phone"),              # Optional: contact phone
            email=request.form.get("email"),              # Optional: contact email
            consultation_fee=float(request.form["consultation_fee"]),  # Cast string → float
            procedure_fee=float(request.form["procedure_fee"]),        # Cast string → float
            service_rates=request.form.get("service_rates", ""),       # Optional free-text rates
        )
        db.session.add(doctor)   # Stage the new doctor record
        db.session.commit()      # Persist to the database
        return redirect(url_for("main.doctors"))  # PRG: redirect to avoid re-submit on refresh

    # GET: render the page with all doctors sorted alphabetically by name
    return render_template("doctors.html", doctors=Doctor.query.order_by(Doctor.full_name).all())


# ── PATIENTS ──────────────────────────────────────────────────────────────────
@main_bp.route("/patients", methods=["GET", "POST"])
def patients():
    """List all patients (GET) or register a new patient (POST)."""
    if request.method == "POST":
        patient = Patient(
            full_name=request.form["full_name"],   # Required
            age=int(request.form["age"]),          # Cast string → int
            gender=request.form["gender"],         # Required: Male / Female / Other
            phone=request.form.get("phone"),
            email=request.form.get("email"),
            address=request.form.get("address"),
            medical_history=request.form.get("medical_history"),
            insurance_provider=request.form.get("insurance_provider"),
            insurance_policy_number=request.form.get("insurance_policy_number"),
            insurance_coverage_percent=float(request.form.get("insurance_coverage_percent") or 0),
            # 'or 0' handles the case where the field is left blank (empty string → 0)
        )
        db.session.add(patient)
        db.session.commit()
        return redirect(url_for("main.patients"))

    return render_template("patients.html", patients=Patient.query.order_by(Patient.full_name).all())


# ── MEDICATIONS ───────────────────────────────────────────────────────────────
@main_bp.route("/medications", methods=["GET", "POST"])
def medications():
    """List all medications (GET) or add a new medication to the master list (POST)."""
    if request.method == "POST":
        medication = Medication(
            name=request.form["name"],                        # Required: unique drug name
            dosage_options=request.form["dosage_options"],    # Required: available dosages
            side_effects=request.form.get("side_effects"),    # Optional
            manufacturer=request.form.get("manufacturer"),    # Optional
            unit_cost=float(request.form["unit_cost"]),       # Required: cost per unit
        )
        db.session.add(medication)
        db.session.commit()
        return redirect(url_for("main.medications"))

    return render_template("medications.html", medications=Medication.query.order_by(Medication.name).all())


# ── INVENTORY ─────────────────────────────────────────────────────────────────
@main_bp.route("/inventory", methods=["GET", "POST"])
def inventory():
    """List all stock batches (GET) or add a new inventory batch (POST).
    Adding a batch automatically creates an initial 'in' stock transaction."""
    meds = Medication.query.order_by(Medication.name).all()  # Needed for the medication dropdown

    if request.method == "POST":
        batch = InventoryBatch(
            medication_id=int(request.form["medication_id"]),  # Which medication this batch is for
            batch_number=request.form["batch_number"],         # Manufacturer batch/lot number
            storage_location=request.form["storage_location"], # Where it will be stored
            expiration_date=datetime.strptime(request.form["expiration_date"], "%Y-%m-%d").date(),
            # Parse the HTML date input string into a Python date object
            current_stock=int(request.form["current_stock"]),  # Initial units received
            reorder_level=int(request.form["reorder_level"]),  # Threshold for restock alerts
        )
        db.session.add(batch)
        db.session.flush()
        # flush() sends the INSERT to the DB and assigns batch.id WITHOUT committing the transaction.
        # This is needed so we can reference batch.id in the StockTransaction below.

        # Automatically log the initial stock receipt as a stock transaction
        db.session.add(
            StockTransaction(
                batch_id=batch.id,
                quantity=batch.current_stock,
                transaction_type="in",           # "in" = stock received
                reason="Initial stock received",
            )
        )
        db.session.commit()  # Commit both the batch and the transaction together
        return redirect(url_for("main.inventory"))

    # Find all batches where stock has fallen to or below the reorder threshold
    below_reorder = InventoryBatch.query.filter(
        InventoryBatch.current_stock <= InventoryBatch.reorder_level
    ).all()

    return render_template(
        "inventory.html",
        medications=meds,
        batches=InventoryBatch.query.order_by(InventoryBatch.expiration_date).all(),
        # Sort batches by expiry date so the soonest-to-expire appear first
        below_reorder=below_reorder,
    )


# ── SHIFTS ────────────────────────────────────────────────────────────────────
@main_bp.route("/shifts", methods=["GET", "POST"])
def shifts():
    """List all doctor shifts (GET) or log a new shift record (POST)."""
    doctors = Doctor.query.order_by(Doctor.full_name).all()  # Needed for the doctor dropdown

    if request.method == "POST":
        shift = DoctorShift(
            doctor_id=int(request.form["doctor_id"]),
            shift_date=datetime.strptime(request.form["shift_date"], "%Y-%m-%d").date(),
            # Parse the HTML date input into a Python date object
            planned_in_time=parse_datetime(request.form["planned_in_time"]),   # Scheduled start
            planned_out_time=parse_datetime(request.form["planned_out_time"]), # Scheduled end
            actual_in_time=parse_datetime(request.form.get("actual_in_time")),   # Real clock-in (optional)
            actual_out_time=parse_datetime(request.form.get("actual_out_time")), # Real clock-out (optional)
            status=request.form.get("status", "scheduled"),  # Default to 'scheduled' if not provided
        )
        db.session.add(shift)
        db.session.commit()
        return redirect(url_for("main.shifts"))

    # GET: show all shifts sorted by date descending (most recent first)
    return render_template(
        "shifts.html",
        doctors=doctors,
        shifts=DoctorShift.query.order_by(DoctorShift.shift_date.desc()).all(),
    )


# ── APPOINTMENTS ──────────────────────────────────────────────────────────────
@main_bp.route("/appointments", methods=["GET", "POST"])
def appointments():
    """List all appointments (GET) or book a new appointment (POST)."""
    doctors = Doctor.query.order_by(Doctor.full_name).all()   # For the doctor dropdown
    patients = Patient.query.order_by(Patient.full_name).all() # For the patient dropdown

    if request.method == "POST":
        appt = Appointment(
            patient_id=int(request.form["patient_id"]),
            doctor_id=int(request.form["doctor_id"]),
            appointment_datetime=parse_datetime(request.form["appointment_datetime"]),
            reason_for_visit=request.form.get("reason_for_visit"),
            patient_check_in=parse_datetime(request.form.get("patient_check_in")),   # Optional
            patient_check_out=parse_datetime(request.form.get("patient_check_out")), # Optional
            status=request.form.get("status", "booked"),  # Default status is 'booked'
        )
        db.session.add(appt)
        db.session.commit()
        return redirect(url_for("main.appointments"))

    return render_template(
        "appointments.html",
        doctors=doctors,
        patients=patients,
        # Show most recent appointments first
        appointments=Appointment.query.order_by(Appointment.appointment_datetime.desc()).all(),
    )


# ── VISITS ────────────────────────────────────────────────────────────────────
@main_bp.route("/visits", methods=["GET", "POST"])
def visits():
    """List all visit records (GET) or create a new visit record from an appointment (POST)."""
    appointments = Appointment.query.order_by(Appointment.appointment_datetime.desc()).all()

    if request.method == "POST":
        # Fetch the appointment or return a 404 error if it doesn't exist
        appointment = Appointment.query.get_or_404(int(request.form["appointment_id"]))

        visit = Visit(
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,  # Copy patient from the linked appointment
            doctor_id=appointment.doctor_id,    # Copy doctor from the linked appointment
            visit_date=datetime.utcnow(),        # Stamp the visit with the current UTC time
            reason=request.form["reason"],
            diagnosis=request.form["diagnosis"],
            test_results=request.form.get("test_results"),
            clinical_findings=request.form.get("clinical_findings"),
            notes=request.form.get("notes"),
        )
        db.session.add(visit)
        db.session.commit()
        return redirect(url_for("main.visits"))

    return render_template(
        "visits.html",
        appointments=appointments,
        visits=Visit.query.order_by(Visit.visit_date.desc()).all(),
    )


# ── PRESCRIPTIONS ─────────────────────────────────────────────────────────────
@main_bp.route("/prescriptions", methods=["GET", "POST"])
def prescriptions():
    """List all prescriptions (GET) or create a new prescription with stock deduction (POST)."""
    visits = Visit.query.order_by(Visit.visit_date.desc()).all()
    medications = Medication.query.order_by(Medication.name).all()

    if request.method == "POST":
        item_qty = int(request.form["quantity"])  # Units to dispense — used for both item and stock

        # Create the parent prescription record
        prescription = Prescription(
            visit_id=int(request.form["visit_id"]),
            patient_id=int(request.form["patient_id"]),
            doctor_id=int(request.form["doctor_id"]),
            special_notes=request.form.get("special_notes"),
        )
        db.session.add(prescription)
        db.session.flush()
        # flush() assigns prescription.id so it can be referenced in PrescriptionItem below

        # Create the medication line item linked to the prescription
        item = PrescriptionItem(
            prescription_id=prescription.id,
            medication_id=int(request.form["medication_id"]),
            dosage_instruction=request.form["dosage_instruction"],
            duration_days=int(request.form["duration_days"]),
            frequency=request.form["frequency"],
            quantity=item_qty,
        )
        db.session.add(item)

        # FIFO stock deduction: use the batch with the earliest expiry date first
        # This ensures oldest stock is consumed before newer stock (reduces waste)
        batch = (
            InventoryBatch.query.filter_by(medication_id=item.medication_id)
            .order_by(InventoryBatch.expiration_date.asc())  # Earliest expiry first
            .first()
        )
        if batch and batch.current_stock >= item_qty:
            # Only deduct if a batch exists and has enough stock to cover the prescription
            batch.current_stock -= item_qty  # Reduce the stock count in the batch

            # Log the stock movement as an "out" transaction for audit purposes
            db.session.add(
                StockTransaction(
                    batch_id=batch.id,
                    quantity=item_qty,
                    transaction_type="out",  # "out" = stock dispensed
                    reason=f"Dispensed for prescription {prescription.id}",
                )
            )

        db.session.commit()  # Commit prescription, item, and stock changes together
        return redirect(url_for("main.prescriptions"))

    return render_template(
        "prescriptions.html",
        visits=visits,
        medications=medications,
        prescriptions=Prescription.query.order_by(Prescription.created_at.desc()).all(),
    )


# ── BILLING ───────────────────────────────────────────────────────────────────
@main_bp.route("/billing", methods=["GET", "POST"])
def billing():
    """Add a billed service to a visit (POST) or view the bill summary for a visit (GET)."""
    visits = Visit.query.order_by(Visit.visit_date.desc()).all()

    if request.method == "POST":
        visit_id = int(request.form["visit_id"])
        doctor_id = int(request.form["doctor_id"])
        service_type = request.form["service_type"]   # consultation / procedure / lab / other
        quantity = float(request.form["quantity"])
        unit_fee = float(request.form["unit_fee"])

        billed_service = BilledService(
            visit_id=visit_id,
            doctor_id=doctor_id,
            service_type=service_type,
            quantity=quantity,
            unit_fee=unit_fee,
            total_fee=quantity * unit_fee,  # Pre-calculate and store total for fast retrieval
        )
        db.session.add(billed_service)
        db.session.commit()
        return redirect(url_for("main.billing"))

    # GET: optionally calculate the full bill for a specific visit via ?visit_id=X
    selected_visit_id = request.args.get("visit_id", type=int)  # Read visit_id from query string
    selected_visit = Visit.query.get(selected_visit_id) if selected_visit_id else None
    services = BilledService.query.filter_by(visit_id=selected_visit_id).all() if selected_visit_id else []

    gross = sum(s.total_fee for s in services)  # Sum all service line totals for this visit
    coverage = selected_visit.patient.insurance_coverage_percent if selected_visit else 0.0
    # Get the patient's insurance coverage percentage (0–100)
    insurance_amount = gross * (coverage / 100.0)  # Amount the insurance company covers
    payable = gross - insurance_amount              # Amount the patient must pay out of pocket

    return render_template(
        "billing.html",
        visits=visits,
        selected_visit=selected_visit,
        services=services,
        gross=gross,
        coverage=coverage,
        insurance_amount=insurance_amount,
        payable=payable,
    )


# ── REPORTS ───────────────────────────────────────────────────────────────────
@main_bp.route("/reports")
def reports():
    """Operational queries page — four analytical reports driven by query-string filters."""

    # Read optional filter parameters from the URL query string
    doctor_id = request.args.get("doctor_id", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    usage_group = request.args.get("usage_group", "patient")  # Default grouping is by patient

    # ── Report 1: All distinct patients seen by a specific doctor ──────────────
    patients_by_doctor = []
    if doctor_id:
        patients_by_doctor = (
            db.session.query(Patient)
            .join(Visit, Visit.patient_id == Patient.id)
            .filter(Visit.doctor_id == doctor_id)
            .distinct()  # Avoid duplicates if a patient had multiple visits with the same doctor
            .all()
        )

    # ── Report 2: Medications prescribed within an optional date range ─────────
    # Joins 5 tables to produce human-readable names instead of raw IDs
    med_query = (
        db.session.query(
            Prescription.created_at,
            Patient.full_name.label("patient_name"),    # Label for use in the template
            Doctor.full_name.label("doctor_name"),
            Medication.name.label("medication_name"),
            PrescriptionItem.quantity,
        )
        .join(PrescriptionItem, PrescriptionItem.prescription_id == Prescription.id)
        .join(Medication, Medication.id == PrescriptionItem.medication_id)
        .join(Patient, Patient.id == Prescription.patient_id)
        .join(Doctor, Doctor.id == Prescription.doctor_id)
    )
    if start_date_str:
        # Filter to prescriptions created on or after the start date
        med_query = med_query.filter(Prescription.created_at >= datetime.strptime(start_date_str, "%Y-%m-%d"))
    if end_date_str:
        # Filter to prescriptions created on or before the end date
        med_query = med_query.filter(Prescription.created_at <= datetime.strptime(end_date_str, "%Y-%m-%d"))
    meds_by_date = med_query.order_by(Prescription.created_at.desc()).all()

    # ── Report 3: Inventory batches below their reorder threshold ──────────────
    below_reorder = InventoryBatch.query.filter(
        InventoryBatch.current_stock <= InventoryBatch.reorder_level
    ).all()

    # ── Report 4: Total medication usage grouped by patient or doctor ──────────
    usage_rows = []
    if usage_group == "doctor":
        # Aggregate total quantity dispensed per doctor per medication
        usage_rows = (
            db.session.query(
                Doctor.full_name.label("entity_name"),
                Medication.name.label("medication_name"),
                func.sum(PrescriptionItem.quantity).label("total_qty"),  # SQL SUM()
            )
            .join(Prescription, Prescription.doctor_id == Doctor.id)
            .join(PrescriptionItem, PrescriptionItem.prescription_id == Prescription.id)
            .join(Medication, Medication.id == PrescriptionItem.medication_id)
            .group_by(Doctor.full_name, Medication.name)
            .all()
        )
    else:
        # Default: aggregate total quantity dispensed per patient per medication
        usage_rows = (
            db.session.query(
                Patient.full_name.label("entity_name"),
                Medication.name.label("medication_name"),
                func.sum(PrescriptionItem.quantity).label("total_qty"),  # SQL SUM()
            )
            .join(Prescription, Prescription.patient_id == Patient.id)
            .join(PrescriptionItem, PrescriptionItem.prescription_id == Prescription.id)
            .join(Medication, Medication.id == PrescriptionItem.medication_id)
            .group_by(Patient.full_name, Medication.name)
            .all()
        )

    return render_template(
        "reports.html",
        doctors=Doctor.query.order_by(Doctor.full_name).all(),  # For the doctor filter dropdown
        patients_by_doctor=patients_by_doctor,
        meds_by_date=meds_by_date,
        below_reorder=below_reorder,
        usage_rows=usage_rows,
        usage_group=usage_group,  # Passed back so the template can mark the active selection
    )
