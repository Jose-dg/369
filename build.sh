#!/bin/sh

# Actualiza pip
python -m pip install --upgrade pip

# Instala las dependencias
pip install -r requirements.txt

# Ejecuta migraciones
python manage.py migrate

# Asegúrate de que la carpeta 'static' existe
mkdir -p static

# Recolecta archivos estáticos
python manage.py collectstatic --no-input

# Crea el superusuario
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin@mail.com', 'admin@mail.com', '9f63B6E14nWjLPtg2fb0O291MnBuWpUhAZ4')" | python manage.py shell

# Otros comandos de preparación si es necesario...