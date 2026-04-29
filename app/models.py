# Database models for the Clinical Management System.
# Each class maps to one table in the SQLite database via SQLAlchemy ORM.
# Relationships between models are declared here so SQLAlchemy can handle JOINs automatically.

from datetime import datetime  # Used to set default timestamp values on date/time columns

from . import db  # Import the shared SQLAlchemy instance from app/__init__.py


# ── DOCTOR ────────────────────────────────────────────────────────────────────
class Doctor(db.Model):
    """Represents a doctor registered in the system."""

    __tablename__ = "doctors"  # Explicit table name in the database

    id = db.Column(db.Integer, primary_key=True)  # Auto-incrementing unique identifier
    full_name = db.Column(db.String(120), nullable=False)   # Doctor's full name, required
    specialty = db.Column(db.String(120), nullable=False)   # Medical specialty (e.g. Cardiology)
    department = db.Column(db.String(120), nullable=False)  # Hospital department (e.g. ICU)
    qualifications = db.Column(db.Text, nullable=False)     # Degrees and certifications, required
    phone = db.Column(db.String(40))                        # Optional contact phone number
    email = db.Column(db.String(120))                       # Optional contact email address
    consultation_fee = db.Column(db.Float, nullable=False, default=0.0)  # Fee charged per consultation
    procedure_fee = db.Column(db.Float, nullable=False, default=0.0)     # Fee charged per procedure
    service_rates = db.Column(db.Text, default="")
    # Free-text field for custom service rates, e.g. "X-ray:100, ECG:80"

    # One doctor can have many shifts; deleting a doctor removes all their shifts
    shifts = db.relationship("DoctorShift", back_populates="doctor", cascade="all, delete-orphan")

    # One doctor can have many appointments; deleting a doctor removes all their appointments
    appointments = db.relationship("Appointment", back_populates="doctor", cascade="all, delete-orphan")

    # One doctor can have many visit records; deleting a doctor removes all their visits
    visits = db.relationship("Visit", back_populates="doctor", cascade="all, delete-orphan")


# ── PATIENT ───────────────────────────────────────────────────────────────────
class Patient(db.Model):
    """Represents a patient registered in the clinic."""

    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)   # Patient's full name, required
    age = db.Column(db.Integer, nullable=False)             # Age in years, required
    gender = db.Column(db.String(20), nullable=False)       # Male / Female / Other, required
    phone = db.Column(db.String(40))                        # Optional phone number
    email = db.Column(db.String(120))                       # Optional email address
    address = db.Column(db.Text)                            # Optional home address
    medical_history = db.Column(db.Text)                    # Free-text past medical history
    insurance_provider = db.Column(db.String(120))          # Name of the insurance company
    insurance_policy_number = db.Column(db.String(120))     # Patient's insurance policy number
    insurance_coverage_percent = db.Column(db.Float, default=0.0)
    # Percentage of the bill covered by insurance (0–100); used in billing calculations

    # One patient can have many appointments; deleting a patient removes all their appointments
    appointments = db.relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")

    # One patient can have many visit records; deleting a patient removes all their visits
    visits = db.relationship("Visit", back_populates="patient", cascade="all, delete-orphan")


# ── MEDICATION ────────────────────────────────────────────────────────────────
class Medication(db.Model):
    """Master list of drugs/medications available in the clinic."""

    __tablename__ = "medications"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    # Drug name must be unique across the system to avoid duplicates
    dosage_options = db.Column(db.String(255), nullable=False)  # Available dosages, e.g. "250mg, 500mg"
    side_effects = db.Column(db.Text)                           # Known side effects (optional)
    manufacturer = db.Column(db.String(120))                    # Drug manufacturer name (optional)
    unit_cost = db.Column(db.Float, nullable=False, default=0.0)
    # Cost per unit — used when calculating prescription/billing costs

    # One medication can have many inventory batches; deleting a medication removes all its batches
    inventory_batches = db.relationship("InventoryBatch", back_populates="medication", cascade="all, delete-orphan")

    # One medication can appear in many prescription items
    # No cascade here — prescription history should survive if a medication record is edited
    prescription_items = db.relationship("PrescriptionItem", back_populates="medication")


# ── INVENTORY BATCH ───────────────────────────────────────────────────────────
class InventoryBatch(db.Model):
    """Tracks a specific physical batch of a medication in stock."""

    __tablename__ = "inventory_batches"

    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey("medications.id"), nullable=False)
    # Foreign key linking this batch to its medication in the master list
    batch_number = db.Column(db.String(60), nullable=False)       # Manufacturer batch/lot number
    storage_location = db.Column(db.String(120), nullable=False)  # Where it is stored (shelf, room, etc.)
    expiration_date = db.Column(db.Date, nullable=False)          # Expiry date for this specific batch
    current_stock = db.Column(db.Integer, nullable=False, default=0)
    # Current number of units available in this batch
    reorder_level = db.Column(db.Integer, nullable=False, default=0)
    # When current_stock drops to or below this number, a restock alert is triggered

    # Back-reference to the parent medication record
    medication = db.relationship("Medication", back_populates="inventory_batches")

    # One batch can have many stock transactions (in/out movements)
    stock_transactions = db.relationship("StockTransaction", back_populates="batch", cascade="all, delete-orphan")


# ── STOCK TRANSACTION ─────────────────────────────────────────────────────────
class StockTransaction(db.Model):
    """Audit log of every stock movement (received or dispensed) for a batch."""

    __tablename__ = "stock_transactions"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("inventory_batches.id"), nullable=False)
    # Which inventory batch this transaction belongs to
    quantity = db.Column(db.Integer, nullable=False)             # Number of units moved
    transaction_type = db.Column(db.String(20), nullable=False)
    # "in"  → stock received (purchase/delivery)
    # "out" → stock dispensed (prescription fulfillment)
    reason = db.Column(db.String(255))                           # Human-readable reason for the movement
    timestamp = db.Column(db.DateTime, default=datetime.utcnow) # Auto-set to UTC time when created

    # Back-reference to the parent inventory batch
    batch = db.relationship("InventoryBatch", back_populates="stock_transactions")


# ── DOCTOR SHIFT ──────────────────────────────────────────────────────────────
class DoctorShift(db.Model):
    """Records a doctor's planned and actual shift times for attendance tracking."""

    __tablename__ = "doctor_shifts"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    # Which doctor this shift belongs to
    shift_date = db.Column(db.Date, nullable=False)              # Calendar date of the shift
    planned_in_time = db.Column(db.DateTime, nullable=False)     # Scheduled start time
    planned_out_time = db.Column(db.DateTime, nullable=False)    # Scheduled end time
    actual_in_time = db.Column(db.DateTime)                      # Real clock-in time (filled later)
    actual_out_time = db.Column(db.DateTime)                     # Real clock-out time (filled later)
    status = db.Column(db.String(20), default="scheduled")
    # Attendance status: scheduled / present / late / absent

    # Back-reference to the doctor record
    doctor = db.relationship("Doctor", back_populates="shifts")


# ── APPOINTMENT ───────────────────────────────────────────────────────────────
class Appointment(db.Model):
    """A scheduled meeting between a patient and a doctor."""

    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    # The patient who booked the appointment
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    # The doctor the appointment is with
    appointment_datetime = db.Column(db.DateTime, nullable=False)  # Scheduled date and time
    reason_for_visit = db.Column(db.Text)                          # Why the patient is coming
    patient_check_in = db.Column(db.DateTime)                      # Actual arrival time at the clinic
    patient_check_out = db.Column(db.DateTime)                     # Actual departure time from the clinic
    status = db.Column(db.String(20), default="booked")
    # Lifecycle status: booked → checked_in → completed / cancelled

    # Back-references to patient and doctor records
    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")

    # One appointment leads to at most one visit record (one-to-one)
    # uselist=False tells SQLAlchemy to return a single object instead of a list
    visit = db.relationship("Visit", back_populates="appointment", uselist=False)


# ── VISIT ─────────────────────────────────────────────────────────────────────
class Visit(db.Model):
    """The clinical record created when a patient is seen by a doctor.
    Always linked to exactly one appointment (one-to-one via unique FK)."""

    __tablename__ = "visits"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey("appointments.id"), nullable=False, unique=True)
    # unique=True enforces the one-to-one constraint: each appointment can only produce one visit
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)  # Auto-stamped to UTC when created
    reason = db.Column(db.Text, nullable=False)                   # Reason documented at visit time
    diagnosis = db.Column(db.Text, nullable=False)                # Doctor's diagnosis
    test_results = db.Column(db.Text)                             # Lab or imaging results (optional)
    clinical_findings = db.Column(db.Text)                        # Physical examination findings (optional)
    notes = db.Column(db.Text)                                    # Free-text clinical notes (optional)

    # Back-references to related records
    appointment = db.relationship("Appointment", back_populates="visit")
    patient = db.relationship("Patient", back_populates="visits")
    doctor = db.relationship("Doctor", back_populates="visits")

    # One visit can have many prescriptions; deleting a visit removes all its prescriptions
    prescriptions = db.relationship("Prescription", back_populates="visit", cascade="all, delete-orphan")

    # One visit can have many billed services; deleting a visit removes all its billing lines
    billed_services = db.relationship("BilledService", back_populates="visit", cascade="all, delete-orphan")


# ── PRESCRIPTION ──────────────────────────────────────────────────────────────
class Prescription(db.Model):
    """A prescription issued during a visit. Contains one or more medication items."""

    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("visits.id"), nullable=False)
    # The visit during which this prescription was issued
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    # Denormalized for fast patient-level queries without joining through visits
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    # Denormalized for fast doctor-level queries without joining through visits
    special_notes = db.Column(db.Text)                            # Extra instructions for the pharmacist
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Auto-timestamp when prescription is created

    # Back-reference to the parent visit
    visit = db.relationship("Visit", back_populates="prescriptions")

    # One prescription can have many line items (one per medication)
    items = db.relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")


# ── PRESCRIPTION ITEM ─────────────────────────────────────────────────────────
class PrescriptionItem(db.Model):
    """A single medication line within a prescription."""

    __tablename__ = "prescription_items"

    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey("prescriptions.id"), nullable=False)
    # Which prescription this item belongs to
    medication_id = db.Column(db.Integer, db.ForeignKey("medications.id"), nullable=False)
    # Which medication is being prescribed
    dosage_instruction = db.Column(db.String(255), nullable=False)
    # How to take it, e.g. "Take 1 tablet after meals"
    duration_days = db.Column(db.Integer, nullable=False)   # How many days the course lasts
    frequency = db.Column(db.String(80), nullable=False)    # How often, e.g. "twice daily"
    quantity = db.Column(db.Integer, nullable=False)        # Total units to dispense from stock

    # Back-references to parent prescription and medication
    prescription = db.relationship("Prescription", back_populates="items")
    medication = db.relationship("Medication", back_populates="prescription_items")


# ── BILLED SERVICE ────────────────────────────────────────────────────────────
class BilledService(db.Model):
    """A single line item on a visit's bill (consultation, procedure, lab, etc.)."""

    __tablename__ = "billed_services"

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("visits.id"), nullable=False)
    # The visit this charge belongs to
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    # The doctor who performed the service
    service_type = db.Column(db.String(80), nullable=False)
    # Category of service: consultation / procedure / lab / other
    quantity = db.Column(db.Float, nullable=False, default=1.0)  # Number of units of the service
    unit_fee = db.Column(db.Float, nullable=False)               # Price per unit
    total_fee = db.Column(db.Float, nullable=False)
    # Pre-calculated total (quantity × unit_fee) stored for fast retrieval without re-computing

    # Back-reference to the parent visit
    visit = db.relationship("Visit", back_populates="billed_services")
