### 1. Install Libraries
pip3 install -r requirements.txt

### 2. Run Migrations
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py makemigrations dashboard
python3 manage.py migrate dashboard

### 3. Create Admin
python3 manage.py createsuperuser

### 4. Run the application
python3 manage.py runserver

### 5. Access Application (you can use above created admin credentials to login)
Go to URL: http://127.0.0.1:8000

### 6. Access Admin panel to create new users
Go to URL: http://127.0.0.1:8000/admin