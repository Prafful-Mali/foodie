# FoodieAPI – Recipe Manager

FoodieAPI is a Django REST API for storing, managing, and sharing recipes. Users can keep recipes private or make them public. Admins can manage cuisines and ingredients.

## Features
- JWT-based authentication  
- CRUD for recipes  
- Public/private recipe visibility  
- Role-based permissions (Admin/User)  
- Manage cuisines and ingredients  

## Tech Stack
- Python 3.12  
- Django & DRF  
- PostgreSQL  
- JWT Authentication  
- Dependency management with uv  
---

## Set up using uv

### 1. Clone the repository
```
git clone https://github.com/Prafful-Mali/foodie.git
cd foodie
```

### 2. Install uv (if not installed)
```
pip install uv
```

### 3. Create and sync virtual environment
```
uv venv  
```

### 4. Activate virtual environment
Linux / macOS:  
```
source .venv/bin/activate  
```

Windows:  
```
.venv\Scripts\activate
```

### 5. Sync dependencies
```
uv sync
```

### 6. Configure environment variables
Create a .env file and populate it using the values from env.sample

### 7. Apply migrations
```
python manage.py migrate
```

### 8. Start development server
```
python manage.py runserver
```

App available at: http://127.0.0.1:8000/
