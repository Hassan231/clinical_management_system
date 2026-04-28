from datetime import datetime

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import func

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

main_bp = Blueprint("main", __name__)


def parse_datetime(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M")


@main_bp.route("/")
def index():
    metrics = {
        "doctors": Doctor.query.count(),
        "patients": Patient.query.count(),
        "appointments": Appointment.query.count(),
        "visits": Visit.query.count(),
        "medications": Medication.query.count(),
    }
    return render_template("index.html", metrics=metrics)


@main_bp.route("/doctors", methods=["GET", "POST"])
def doctors():
    if request.method == "POST":
        doctor = Doctor(
            full_name=request.form["full_name"],
            specialty=request.form["specialty"],
            department=request.form["department"],
            qualifications=request.form["qualifications"],
            phone=request.form.get("phone"),
            email=request.form.get("email"),
            consultation_fee=float(request.form["consultation_fee"]),
            procedure_fee=float(request.form["procedure_fee"]),
            service_rates=request.form.get("service_rates", ""),
        )
        db.session.add(doctor)
        db.session.commit()
        return redirect(url_for("main.doctors"))
    return render_template("doctors.html", doctors=Doctor.query.order_by(Doctor.full_name).all())


@main_bp.route("/patients", methods=["GET", "POST"])
def patients():
    if request.method == "POST":
        patient = Patient(
            full_name=request.form["full_name"],
            age=int(request.form["age"]),
            gender=request.form["gender"],
            phone=request.form.get("phone"),
            email=request.form.get("email"),
            address=request.form.get("address"),
            medical_history=request.form.get("medical_history"),
            insurance_provider=request.form.get("insurance_provider"),
            insurance_policy_number=request.form.get("insurance_policy_number"),
            insurance_coverage_percent=float(request.form.get("insurance_coverage_percent") or 0),
        )
        db.session.add(patient)
        db.session.commit()
        return redirect(url_for("main.patients"))
    return render_template("patients.html", patients=Patient.query.order_by(Patient.full_name).all())


@main_bp.route("/medications", methods=["GET", "POST"])
def medications():
    if request.method == "POST":
        medication = Medication(
            name=request.form["name"],
            dosage_options=request.form["dosage_options"],
            side_effects=request.form.get("side_effects"),
            manufacturer=request.form.get("manufacturer"),
            unit_cost=float(request.form["unit_cost"]),
        )
        db.session.add(medication)
        db.session.commit()
        return redirect(url_for("main.medications"))
    return render_template("medications.html", medications=Medication.query.order_by(Medication.name).all())


@main_bp.route("/inventory", methods=["GET", "POST"])
def inventory():
    meds = Medication.query.order_by(Medication.name).all()
    if request.method == "POST":
        batch = InventoryBatch(
            medication_id=int(request.form["medication_id"]),
            batch_number=request.form["batch_number"],
            storage_location=request.form["storage_location"],
            expiration_date=datetime.strptime(request.form["expiration_date"], "%Y-%m-%d").date(),
            current_stock=int(request.form["current_stock"]),
            reorder_level=int(request.form["reorder_level"]),
        )
        db.session.add(batch)
        db.session.flush()
        db.session.add(
            StockTransaction(
                batch_id=batch.id,
                quantity=batch.current_stock,
                transaction_type="in",
                reason="Initial stock received",
            )
        )
        db.session.commit()
        return redirect(url_for("main.inventory"))
    below_reorder = InventoryBatch.query.filter(InventoryBatch.current_stock <= InventoryBatch.reorder_level).all()
    return render_template(
        "inventory.html",
        medications=meds,
        batches=InventoryBatch.query.order_by(InventoryBatch.expiration_date).all(),
        below_reorder=below_reorder,
    )


@main_bp.route("/shifts", methods=["GET", "POST"])
def shifts():
    doctors = Doctor.query.order_by(Doctor.full_name).all()
    if request.method == "POST":
        shift = DoctorShift(
            doctor_id=int(request.form["doctor_id"]),
            shift_date=datetime.strptime(request.form["shift_date"], "%Y-%m-%d").date(),
            planned_in_time=parse_datetime(request.form["planned_in_time"]),
            planned_out_time=parse_datetime(request.form["planned_out_time"]),
            actual_in_time=parse_datetime(request.form.get("actual_in_time")),
            actual_out_time=parse_datetime(request.form.get("actual_out_time")),
            status=request.form.get("status", "scheduled"),
        )
        db.session.add(shift)
        db.session.commit()
        return redirect(url_for("main.shifts"))
    return render_template("shifts.html", doctors=doctors, shifts=DoctorShift.query.order_by(DoctorShift.shift_date.desc()).all())


@main_bp.route("/appointments", methods=["GET", "POST"])
def appointments():
    doctors = Doctor.query.order_by(Doctor.full_name).all()
    patients = Patient.query.order_by(Patient.full_name).all()
    if request.method == "POST":
        appt = Appointment(
            patient_id=int(request.form["patient_id"]),
            doctor_id=int(request.form["doctor_id"]),
            appointment_datetime=parse_datetime(request.form["appointment_datetime"]),
            reason_for_visit=request.form.get("reason_for_visit"),
            patient_check_in=parse_datetime(request.form.get("patient_check_in")),
            patient_check_out=parse_datetime(request.form.get("patient_check_out")),
            status=request.form.get("status", "booked"),
        )
        db.session.add(appt)
        db.session.commit()
        return redirect(url_for("main.appointments"))
    return render_template(
        "appointments.html",
        doctors=doctors,
        patients=patients,
        appointments=Appointment.query.order_by(Appointment.appointment_datetime.desc()).all(),
    )


@main_bp.route("/visits", methods=["GET", "POST"])
def visits():
    appointments = Appointment.query.order_by(Appointment.appointment_datetime.desc()).all()
    if request.method == "POST":
        appointment = Appointment.query.get_or_404(int(request.form["appointment_id"]))
        visit = Visit(
            appointment_id=appointment.id,
            patient_id=appointment.patient_id,
            doctor_id=appointment.doctor_id,
            visit_date=datetime.utcnow(),
            reason=request.form["reason"],
            diagnosis=request.form["diagnosis"],
            test_results=request.form.get("test_results"),
            clinical_findings=request.form.get("clinical_findings"),
            notes=request.form.get("notes"),
        )
        db.session.add(visit)
        db.session.commit()
        return redirect(url_for("main.visits"))
    return render_template("visits.html", appointments=appointments, visits=Visit.query.order_by(Visit.visit_date.desc()).all())


@main_bp.route("/prescriptions", methods=["GET", "POST"])
def prescriptions():
    visits = Visit.query.order_by(Visit.visit_date.desc()).all()
    medications = Medication.query.order_by(Medication.name).all()
    if request.method == "POST":
        item_qty = int(request.form["quantity"])
        prescription = Prescription(
            visit_id=int(request.form["visit_id"]),
            patient_id=int(request.form["patient_id"]),
            doctor_id=int(request.form["doctor_id"]),
            special_notes=request.form.get("special_notes"),
        )
        db.session.add(prescription)
        db.session.flush()
        item = PrescriptionItem(
            prescription_id=prescription.id,
            medication_id=int(request.form["medication_id"]),
            dosage_instruction=request.form["dosage_instruction"],
            duration_days=int(request.form["duration_days"]),
            frequency=request.form["frequency"],
            quantity=item_qty,
        )
        db.session.add(item)

        batch = (
            InventoryBatch.query.filter_by(medication_id=item.medication_id)
            .order_by(InventoryBatch.expiration_date.asc())
            .first()
        )
        if batch and batch.current_stock >= item_qty:
            batch.current_stock -= item_qty
            db.session.add(
                StockTransaction(
                    batch_id=batch.id,
                    quantity=item_qty,
                    transaction_type="out",
                    reason=f"Dispensed for prescription {prescription.id}",
                )
            )
        db.session.commit()
        return redirect(url_for("main.prescriptions"))
    return render_template("prescriptions.html", visits=visits, medications=medications, prescriptions=Prescription.query.order_by(Prescription.created_at.desc()).all())


@main_bp.route("/billing", methods=["GET", "POST"])
def billing():
    visits = Visit.query.order_by(Visit.visit_date.desc()).all()
    if request.method == "POST":
        visit_id = int(request.form["visit_id"])
        doctor_id = int(request.form["doctor_id"])
        service_type = request.form["service_type"]
        quantity = float(request.form["quantity"])
        unit_fee = float(request.form["unit_fee"])
        billed_service = BilledService(
            visit_id=visit_id,
            doctor_id=doctor_id,
            service_type=service_type,
            quantity=quantity,
            unit_fee=unit_fee,
            total_fee=quantity * unit_fee,
        )
        db.session.add(billed_service)
        db.session.commit()
        return redirect(url_for("main.billing"))

    selected_visit_id = request.args.get("visit_id", type=int)
    selected_visit = Visit.query.get(selected_visit_id) if selected_visit_id else None
    services = BilledService.query.filter_by(visit_id=selected_visit_id).all() if selected_visit_id else []
    gross = sum(s.total_fee for s in services)
    coverage = selected_visit.patient.insurance_coverage_percent if selected_visit else 0.0
    insurance_amount = gross * (coverage / 100.0)
    payable = gross - insurance_amount
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


@main_bp.route("/reports")
def reports():
    doctor_id = request.args.get("doctor_id", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    usage_group = request.args.get("usage_group", "patient")

    patients_by_doctor = []
    if doctor_id:
        patients_by_doctor = (
            db.session.query(Patient)
            .join(Visit, Visit.patient_id == Patient.id)
            .filter(Visit.doctor_id == doctor_id)
            .distinct()
            .all()
        )

    med_query = (
        db.session.query(
            Prescription.created_at,
            Patient.full_name.label("patient_name"),
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
        med_query = med_query.filter(Prescription.created_at >= datetime.strptime(start_date_str, "%Y-%m-%d"))
    if end_date_str:
        med_query = med_query.filter(Prescription.created_at <= datetime.strptime(end_date_str, "%Y-%m-%d"))
    meds_by_date = med_query.order_by(Prescription.created_at.desc()).all()

    below_reorder = InventoryBatch.query.filter(InventoryBatch.current_stock <= InventoryBatch.reorder_level).all()

    usage_rows = []
    if usage_group == "doctor":
        usage_rows = (
            db.session.query(
                Doctor.full_name.label("entity_name"),
                Medication.name.label("medication_name"),
                func.sum(PrescriptionItem.quantity).label("total_qty"),
            )
            .join(Prescription, Prescription.doctor_id == Doctor.id)
            .join(PrescriptionItem, PrescriptionItem.prescription_id == Prescription.id)
            .join(Medication, Medication.id == PrescriptionItem.medication_id)
            .group_by(Doctor.full_name, Medication.name)
            .all()
        )
    else:
        usage_rows = (
            db.session.query(
                Patient.full_name.label("entity_name"),
                Medication.name.label("medication_name"),
                func.sum(PrescriptionItem.quantity).label("total_qty"),
            )
            .join(Prescription, Prescription.patient_id == Patient.id)
            .join(PrescriptionItem, PrescriptionItem.prescription_id == Prescription.id)
            .join(Medication, Medication.id == PrescriptionItem.medication_id)
            .group_by(Patient.full_name, Medication.name)
            .all()
        )

    return render_template(
        "reports.html",
        doctors=Doctor.query.order_by(Doctor.full_name).all(),
        patients_by_doctor=patients_by_doctor,
        meds_by_date=meds_by_date,
        below_reorder=below_reorder,
        usage_rows=usage_rows,
        usage_group=usage_group,
    )
