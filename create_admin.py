import os
import django

# Tell the script where your settings are
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

# --- EDIT THESE 3 LINES ---
username = 'alexwilliamson' 
email = 'ackeemwilliamson12@gmail.com'
password = 'Hwyuhmean01' # Make this strong!
# ---------------------------

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"✅ SUCCESS: Superuser {username} created!")
else:
    print(f"ℹ️ NOTICE: Superuser {username} already exists.")
