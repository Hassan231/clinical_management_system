# Clinical Management System (Flask)

Complete healthcare management platform built with:
- Flask
- Flask-SQLAlchemy
- SQLite
- HTML/CSS frontend templates

## Implemented Modules

- Doctor management (profile, specialty, qualifications, contact, fee structures)
- Patient registration (demographics, medical history, insurance details)
- Medication master and inventory batches (stock, reorder level, expiry, location, batch)
- Doctor shift scheduling and attendance tracking (planned vs actual in/out)
- Appointment scheduling with check-in/check-out tracking
- Visit records including diagnosis, test results, and clinical findings
- Prescription entry per visit with medicine usage capture
- Billing calculations with service lines and insurance coverage
- Query/report pages for:
  - patients treated by doctor
  - medications prescribed by date range
  - medicines below reorder level
  - medication usage grouped by patient or doctor

## Project Structure

```
clinical_management_system/
  app/
    __init__.py
    models.py
    routes.py
    templates/
    static/
  run.py
  requirements.txt
```

## Run

```powershell
cd E:\clinical_management_system
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Then open:
- http://127.0.0.1:5000

## Notes

- Database tables are auto-created on startup in SQLite file `clinical.db`.
- The app is intentionally organized for easy extension (authentication, role-based access, audit logging, exports).
