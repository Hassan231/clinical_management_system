from datetime import datetime

from . import db


class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(120), nullable=False)
    qualifications = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    consultation_fee = db.Column(db.Float, nullable=False, default=0.0)
    procedure_fee = db.Column(db.Float, nullable=False, default=0.0)
    service_rates = db.Column(db.Text, default="")
    shifts = db.relationship("DoctorShift", back_populates="doctor", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")
    visits = db.relationship("Visit", back_populates="doctor", cascade="all, delete-orphan")


class Patient(db.Model):
    __tablename__ = "patients"
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(40))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    insurance_provider = db.Column(db.String(120))
    insurance_policy_number = db.Column(db.String(120))
    insurance_coverage_percent = db.Column(db.Float, default=0.0)
    appointments = db.relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")
    visits = db.relationship("Visit", back_populates="patient", cascade="all, delete-orphan")


class Medication(db.Model):
    __tablename__ = "medications"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    dosage_options = db.Column(db.String(255), nullable=False)
    side_effects = db.Column(db.Text)
    manufacturer = db.Column(db.String(120))
    unit_cost = db.Column(db.Float, nullable=False, default=0.0)
    inventory_batches = db.relationship("InventoryBatch", back_populates="medication", cascade="all, delete-orphan")
    prescription_items = db.relationship("PrescriptionItem", back_populates="medication")


class InventoryBatch(db.Model):
    __tablename__ = "inventory_batches"
    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey("medications.id"), nullable=False)
    batch_number = db.Column(db.String(60), nullable=False)
    storage_location = db.Column(db.String(120), nullable=False)
    expiration_date = db.Column(db.Date, nullable=False)
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    reorder_level = db.Column(db.Integer, nullable=False, default=0)
    medication = db.relationship("Medication", back_populates="inventory_batches")
    stock_transactions = db.relationship("StockTransaction", back_populates="batch", cascade="all, delete-orphan")


class StockTransaction(db.Model):
    __tablename__ = "stock_transactions"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("inventory_batches.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    batch = db.relationship("InventoryBatch", back_populates="stock_transactions")


class DoctorShift(db.Model):
    __tablename__ = "doctor_shifts"
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    shift_date = db.Column(db.Date, nullable=False)
    planned_in_time = db.Column(db.DateTime, nullable=False)
    planned_out_time = db.Column(db.DateTime, nullable=False)
    actual_in_time = db.Column(db.DateTime)
    actual_out_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="scheduled")
    doctor = db.relationship("Doctor", back_populates="shifts")


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    appointment_datetime = db.Column(db.DateTime, nullable=False)
    reason_for_visit = db.Column(db.Text)
    patient_check_in = db.Column(db.DateTime)
    patient_check_out = db.Column(db.DateTime)
    status = db.Column(db.String(20), default="booked")
    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")
    visit = db.relationship("Visit", back_populates="appointment", uselist=False)


class Visit(db.Model):
    __tablename__ = "visits"
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False, unique=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    reason = db.Column(db.Text, nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    test_results = db.Column(db.Text)
    clinical_findings = db.Column(db.Text)
    notes = db.Column(db.Text)
    appointment = db.relationship("Appointment", back_populates="visit")
    patient = db.relationship("Patient", back_populates="visits")
    doctor = db.relationship("Doctor", back_populates="visits")
    prescriptions = db.relationship("Prescription", back_populates="visit", cascade="all, delete-orphan")
    billed_services = db.relationship("BilledService", back_populates="visit", cascade="all, delete-orphan")


class Prescription(db.Model):
    __tablename__ = "prescriptions"
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("visits.id"), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    special_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    visit = db.relationship("Visit", back_populates="prescriptions")
    items = db.relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")


class PrescriptionItem(db.Model):
    __tablename__ = "prescription_items"
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey("prescriptions.id"), nullable=False)
    medication_id = db.Column(db.Integer, db.ForeignKey("medications.id"), nullable=False)
    dosage_instruction = db.Column(db.String(255), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    frequency = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    prescription = db.relationship("Prescription", back_populates="items")
    medication = db.relationship("Medication", back_populates="prescription_items")


class BilledService(db.Model):
    __tablename__ = "billed_services"
    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("visits.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    service_type = db.Column(db.String(80), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    unit_fee = db.Column(db.Float, nullable=False)
    total_fee = db.Column(db.Float, nullable=False)
    visit = db.relationship("Visit", back_populates="billed_services")
