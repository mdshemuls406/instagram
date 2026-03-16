import random
import os

brands = {
    "1": {
        "name": "Samsung",
        "models": [
            "SM-G991B", "SM-G996B", "SM-G998B",
            "SM-A515F", "SM-A525F", "SM-A715F",
            "SM-M315F", "SM-M515F"
        ]
    },
    "2": {
        "name": "Xiaomi",
        "models": [
            "Mi 9T", "Mi 10", "Mi 11",
            "Redmi Note 8", "Redmi Note 9", "Redmi Note 10",
            "Redmi Note 11", "POCO X3"
        ]
    },
    "3": {
        "name": "Realme",
        "models": [
            "RMX1911", "RMX1971", "RMX2020",
            "RMX2185", "RMX3085", "RMX3360"
        ]
    },
    "4": {
        "name": "Oppo",
        "models": [
            "CPH1909", "CPH1931", "CPH2083",
            "CPH2145", "CPH2173"
        ]
    },
    "5": {
        "name": "Vivo",
        "models": [
            "V2027", "V2036", "V2050",
            "V2061", "V2109"
        ]
    },
    "6": {
        "name": "Huawei",
        "models": [
            "ANE-LX1", "MAR-LX1A", "VOG-L29",
            "LYA-L29", "ELE-L29"
        ]
    },
    "7": {
        "name": "OnePlus",
        "models": [
            "ONEPLUS A5000", "ONEPLUS A6000",
            "ONEPLUS A6010", "ONEPLUS A3003"
        ]
    }
}

android_versions = [
    "8.0", "8.1", "9", "10", "11", "12", "13", "14"
]

chrome_versions = [
    "109.0.0.0",
    "110.0.0.0",
    "111.0.0.0",
    "112.0.0.0",
    "113.0.0.0",
    "114.0.0.0"
]

print("\n==== Mobile Brand List ====\n")

for key, value in brands.items():
    print(f"{key}. {value['name']}")

choice = input("\nSelect Brand Number: ")

if choice not in brands:
    print("Invalid choice!")
    exit()

amount = int(input("How many user agents to generate: "))

selected_brand = brands[choice]
models = selected_brand["models"]

user_agents = []

for i in range(amount):
    model = random.choice(models)
    android = random.choice(android_versions)
    chrome = random.choice(chrome_versions)

    ua = f"Mozilla/5.0 (Linux; Android {android}; {model}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome} Mobile Safari/537.36"
    user_agents.append(ua)

folder = "/sdcard/yasin"

if not os.path.exists(folder):
    os.makedirs(folder)

file_path = f"{folder}/useragent.txt"

with open(file_path, "w") as f:
    for ua in user_agents:
        f.write(ua + "\n")

print(f"\nGenerated {amount} User Agents")
print(f"Saved to: {file_path}")
