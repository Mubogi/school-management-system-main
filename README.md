# 🍊 School Management System

A comprehensive Django-based school management system for schools and small institutes. Manage students, teachers, fees, marks, and more.

## 🥏 Technologies Used 
  1. Django (Python)
  2. SQLite/MySQL database  
  3. Bootstrap 5
  4. JavaScript
  5. HTML, CSS
  6. ReportLab (PDF generation)
  7. QR Code generation

## 💡 FEATURES 
  1. Student record management
  2. Teacher/staff record management 
  3. Fee management with payment tracking
  4. Academic marks and assessment
  5. Report card generation (PDF)
  6. Fee clearance certificates (PDF)
  7. Demand letters (PDF)
  8. QR Code for mobile access
  9. Multiple user roles (Admin, Bursar, Secretary, Head Teacher, DOS, Class Teacher, Subject Teacher)
  10. Role-based dashboards
  11. Student fee balances and payment receipts
  12. Class broadsheets
  13. Assessment reports

## ✅ HOW TO USE?

  <b>Pre-requirement</b> : Make sure you have Python and Django installed.<br><br>

 <b>Step-1 :</b> Install Dependencies <br>
   ```
   pip install -r requirements.txt
   ```

 <b>Step-2 :</b> Run Migrations <br>
   ```
   python manage.py migrate
   ```
   <br>

<b>Step-3 :</b> Create Superuser <br>
   ```
   python manage.py createsuperuser
   ```
   <br>

<b>Step-4 :</b> Run the application <br>
   ```
   python manage.py runserver
   ```
   <br>
   Visit the URL shown (usually http://127.0.0.1:8000)

## 🔐 Features

### QR Code Mobile Access
Navigate to `/qr-connect/` to generate a QR code that allows mobile users to easily access the system via their phone's camera.

### PDF Generation
The system generates professional, modern PDF documents including:
- Payment receipts
- Report cards
- Financial statements
- Fee clearance certificates
- Demand letters
- Class broadsheets
- Assessment reports

## ❤️ Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.
