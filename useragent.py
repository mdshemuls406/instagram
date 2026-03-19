import random
import os
import string

# ----------- BRANDS -----------
brands = {
    "1": ("Samsung", ["SM-G991B","SM-G996B","SM-G998B","SM-A515F","SM-A525F","SM-A715F"]),
    "2": ("Xiaomi", ["Mi 10","Mi 11","Redmi Note 10","Redmi Note 11","POCO X3"]),
    "3": ("Realme", ["RMX1911","RMX1971","RMX2185","RMX3085"]),
    "4": ("Oppo", ["CPH1909","CPH2083","CPH2145"]),
    "5": ("Vivo", ["V2027","V2036","V2050"]),
    "6": ("Huawei", ["ANE-LX1","VOG-L29","ELE-L29"]),
    "7": ("OnePlus", ["ONEPLUS A6000","ONEPLUS A6010"]),
    "8": ("Google Pixel", ["Pixel 5","Pixel 6","Pixel 7"]),
    "9": ("Motorola", ["Moto G7","Moto G8","Moto G9"]),
    "10": ("Nokia", ["Nokia 5","Nokia 6","Nokia 7"]),
    "11": ("Sony", ["Xperia XZ","Xperia 1","Xperia 5"]),
    "12": ("Asus", ["ROG Phone","ROG Phone 2"]),
    "13": ("Lenovo", ["Lenovo K10","Lenovo Z5"]),
    "14": ("Tecno", ["TECNO KA7","TECNO KC8"]),
    "15": ("Infinix", ["X650","X655"]),
    "16": ("Itel", ["itel A25","itel A48"]),
    "17": ("ZTE", ["ZTE Blade A5"]),
    "18": ("LG", ["LG-H870","LG-K40"]),
    "19": ("HTC", ["HTC U11","HTC U12"]),
    "20": ("BlackBerry", ["BBB100-1","Key2"]),
    "21": ("iPhone", [
        "iPhone; CPU iPhone OS 14_0 like Mac OS X",
        "iPhone; CPU iPhone OS 15_0 like Mac OS X",
        "iPhone; CPU iPhone OS 16_0 like Mac OS X"
    ])
}

# ----------- RANDOM FUNCTIONS -----------

def random_build():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def random_device_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

def random_dpi():
    return random.choice(["320dpi","420dpi","480dpi","560dpi"])

def random_resolution():
    return random.choice(["720x1280","1080x1920","1080x2400","1440x3200"])

def random_android():
    return random.choice(["9","10","11","12","13","14"])

def random_chrome():
    return f"{random.randint(100,125)}.0.{random.randint(1000,5000)}.{random.randint(10,150)}"

def random_instagram_version():
    return f"{random.randint(200,300)}.0.0.{random.randint(10,100)}.{random.randint(50,150)}"

def random_facebook_version():
    return f"{random.randint(300,450)}.0.0.{random.randint(10,100)}.{random.randint(50,150)}"

# ----------- MENU -----------

print("\n==== USER AGENT GENERATOR ====\n")

for key, value in brands.items():
    print(f"{key}. {value[0]}")

choice = input("\nSelect Brand: ")

if choice not in brands:
    print("Invalid choice!")
    exit()

print("\nSelect UA Type:")
print("1. Normal")
print("2. Instagram")
print("3. Facebook")

ua_type = input("Choice: ")

amount = int(input("How many UA: "))

brand_name, models = brands[choice]

user_agents = []

# ----------- GENERATION -----------

for _ in range(amount):

    if brand_name == "iPhone":
        ios = random.choice(models)

        if ua_type == "2":  # Instagram iPhone
            ua = f"Instagram {random_instagram_version()} ({ios}; en_US)"
        
        elif ua_type == "3":  # Facebook iPhone
            ua = f"Facebook {random_facebook_version()} ({ios}; en_US)"
        
        else:
            ua = f"Mozilla/5.0 ({ios}) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile Safari/604.1"

    else:
        model = random.choice(models)
        android = random_android()
        build = random_build()
        dpi = random_dpi()
        res = random_resolution()
        device_id = random_device_id()

        if ua_type == "2":  # Instagram
            ua = f"Instagram {random_instagram_version()} Android ({android}/{random.randint(9,15)}; {dpi}; {res}; {brand_name}; {model}; {model}; {build}; {device_id}; en_US)"
        
        elif ua_type == "3":  # Facebook
            ua = f"Facebook {random_facebook_version()} Android ({android}; {dpi}; {res}; {brand_name}; {model}; {build}; {device_id})"
        
        else:
            chrome = random_chrome()
            ua = f"Mozilla/5.0 (Linux; Android {android}; {model} Build/{build}; {dpi}; {res}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome} Mobile Safari/537.36 DeviceID/{device_id}"

    user_agents.append(ua)

# ----------- SAVE -----------

folder = "/sdcard/yasin"
os.makedirs(folder, exist_ok=True)

file_path = f"{folder}/useragent.txt"

with open(file_path, "w") as f:
    for ua in user_agents:
        f.write(ua + "\n")

print(f"\n✅ Generated: {amount}")
print(f"📁 Saved to: {file_path}")
