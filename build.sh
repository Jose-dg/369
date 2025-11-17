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
cat <<EOF | python manage.py shell
import os
from django.contrib.auth import get_user_model

User = get_user_model()
email = 'admin@mail.com'
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '9f63B6E14nWjLPtg2fb0O291MnBuWpUhAZ4')

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email, email, password)
    print(f'Superuser {email} created.')
else:
    print(f'Superuser {email} already exists. Skipping creation.')
EOF

