import requests

# 1. The URL of your local Stratix Server
url = "http://127.0.0.1:8000/api/drone-upload/"

# 2. The data the drone is beaming down
data = {
    # ⚠️ IMPORTANT: Change this to the exact 'site_id' string from your database (e.g., 'STX-001')
    "site_id": "STX-MOBY-44",  
    
    # ⚠️ IMPORTANT: Paste the 'stx_...' key you just generated in the Admin Panel
    "api_key": "stx_NrAXf9Uu6KH3zvXos7N87gPM019NwGT2pydSgeO5hpY", 
    
    "category": "Tower Structure"
}

# 3. The photo the drone just took
# Put a random photo named 'test.jpg' in the same folder as this script
try:
    with open("test.jpg", "rb") as image_file:
        files = {"image": image_file}
        print("🚁 Drone is transmitting data to Stratix Command Center...")
        response = requests.post(url, data=data, files=files)

    print("📡 Server Response:", response.status_code)
    print("📝 Details:", response.json())
except FileNotFoundError:
    print("❌ ERROR: Please put a photo named 'test.jpg' in this folder before running!")
