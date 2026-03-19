import random
import os
import string

# ----------- BRAND + MODELS -----------
brands = {
    "1": ("Samsung", ["SM-G991B","SM-G996B","SM-G998B","SM-A515F","SM-A525F"]),
    "2": ("Xiaomi", ["Mi 10","Mi 11","Redmi Note 10","Redmi Note 11"]),
    "3": ("Realme", ["RMX1911","RMX1971","RMX3085"]),
    "4": ("Oppo", ["CPH1909","CPH2083"]),
    "5": ("Vivo", ["V2027","V2036"]),
    "6": ("Huawei", ["VOG-L29","ELE-L29"]),
    "7": ("OnePlus", ["ONEPLUS A6000","ONEPLUS A6010"]),
    "8": ("Google Pixel", ["Pixel 6","Pixel 7"]),
    "9": ("Motorola", ["Moto G9","Moto G10"]),
    "10": ("Nokia", ["Nokia 6","Nokia 7"]),
    "11": ("Sony", ["Xperia 1","Xperia 5"]),
    "12": ("Asus", ["ROG Phone 2","ROG Phone 3"]),
    "13": ("Lenovo", ["Lenovo K10","Lenovo Z6"]),
    "14": ("Tecno", ["TECNO KA7","TECNO KC8"]),
    "15": ("Infinix", ["X650","X665"]),
    "16": ("Itel", ["itel A25","itel A48"]),
    "17": ("ZTE", ["ZTE Blade A5"]),
    "18": ("LG", ["LG-K40","LG-K50"]),
    "19": ("HTC", ["HTC U11","HTC U12"]),
    "20": ("BlackBerry", ["Key2"]),
    "21": ("iPhone", [
        "iPhone OS 14_0",
        "iPhone OS 15_0",
        "iPhone OS 16_0",
        "iPhone OS 17_0"
    ])
}

# ----------- REALISTIC DATA -----------

abis = ["arm64-v8a","armeabi-v7a"]
locales = ["en_US","en_GB","en_IN","bn_BD"]
densities = ["320dpi","420dpi","480dpi","560dpi"]
resolutions = ["720x1280","1080x1920","1080x2400","1440x3200"]

android_versions = {
    "9": 28,
    "10": 29,
    "11": 30,
    "12": 31,
    "13": 33,
    "14": 34
}

def rand_build():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def rand_device():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

def rand_chrome():
    return f"{random.randint(110,125)}.0.{random.randint(1000,5000)}.{random.randint(10,150)}"

def ig_version():
    return f"{random.randint(250,310)}.0.0.{random.randint(10,100)}.{random.randint(50,200)}"

def ig_version_code():
    return str(random.randint(400000000,500000000))

def fb_version():
    return f"{random.randint(400,480)}.0.0.{random.randint(10,100)}.{random.randint(50,200)}"

def fb_version_code():
    return str(random.randint(300000000,400000000))

# ----------- MENU -----------

print("\n==== PRO USER AGENT GENERATOR ====\n")

for k,v in brands.items():
    print(f"{k}. {v[0]}")

choice = input("\nSelect Brand: ")

if choice not in brands:
    exit("Invalid")

print("\n1. Normal\n2. Instagram\n3. Facebook")
ua_type = input("Select Type: ")

amount = int(input("How many UA: "))

brand, models = brands[choice]

results = []

# ----------- GENERATION -----------

for _ in range(amount):

    if brand == "iPhone":
        ios = random.choice(models)
        locale = random.choice(locales)

        if ua_type == "2":
            ua = f"Instagram {ig_version()} ({ios}; {locale}; scale=3.00; 1170x2532; Apple; iPhone)"
        
        elif ua_type == "3":
            ua = f"FBAN/FBIOS;FBAV/{fb_version()};FBBV/{fb_version_code()};FBDV/iPhone;FBLC/{locale};FBCR/;FBMD/iPhone"

        else:
            ua = f"Mozilla/5.0 (iPhone; CPU {ios} like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile Safari/604.1"

    else:
        model = random.choice(models)
        android = random.choice(list(android_versions.keys()))
        sdk = android_versions[android]
        dpi = random.choice(densities)
        res = random.choice(resolutions)
        abi = random.choice(abis)
        locale = random.choice(locales)
        build = rand_build()
        device_id = rand_device()

        if ua_type == "2":  # Instagram PRO
            ua = f"Instagram {ig_version()} Android ({sdk}/{android}; {dpi}; {res}; {brand}; {model}; {model}; {build}; {abi}; {locale}; {ig_version_code()})"

        elif ua_type == "3":  # Facebook PRO
            ua = f"Dalvik/2.1.0 (Linux; U; Android {android}; {model} Build/{build}) [FBAN/FB4A;FBAV/{fb_version()};FBBV/{fb_version_code()};FBDM/{{density={dpi},width={res.split('x')[0]},height={res.split('x')[1]}}};FBLC/{locale};FBCR/;FBMF/{brand};FBBD/{brand};FBPN/com.facebook.katana;FBDV/{model};FBSV/{android};FBOP/1;FBCA/{abi};]"

        else:
            chrome = rand_chrome()
            ua = f"Mozilla/5.0 (Linux; Android {android}; {model} Build/{build}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome} Mobile Safari/537.36 DeviceID/{device_id}"

    results.append(ua)

# ----------- SAVE -----------

path = "/sdcard/yasin"
os.makedirs(path, exist_ok=True)

file = f"{path}/useragent.txt"

with open(file, "w") as f:
    for ua in results:
        f.write(ua + "\n")

print(f"\n✅ Generated: {amount}")
print(f"📁 Saved: {file}")
