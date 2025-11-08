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

# Otros comandos de preparación si es necesario...