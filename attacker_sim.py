import time
import requests

COLLECTOR_URL = "http://localhost:8001"

def set_load(intensity: int, label: str):
    try:
        res = requests.post(f"{COLLECTOR_URL}/trigger/load", json={"intensity": intensity}, timeout=3)
        print(f"\n[{label}] Set gateway load to {intensity}% -> {res.json()}")
    except requests.RequestException:
        print("\n[ERROR] local_collector.py is not running on Port 8001!")

def toggle_outage():
    try:
        res = requests.post(f"{COLLECTOR_URL}/trigger/outage", timeout=3).json()
        print(f"\n[SAAS LINK] {res.get('status')}: {res.get('message')}")
    except requests.RequestException:
        print("\n[ERROR] local_collector.py is not running on Port 8001!")

if __name__ == "__main__":
    print("====================================================")
    print("   AEGIS BANKING TRAFFIC & ATTACK TUNER (LIVE DEMO) ")
    print("====================================================")
    while True:
        print("\nSelect Traffic / Attack Load Level:")
        print("  [1] No Load / Normal Baseline (15% -> EXCELLENT)")
        print("  [2] Moderate Peak UPI Surge   (55% -> GOOD / FAIR)")
        print("  [3] Heavy Traffic Warning     (75% -> FAIR)")
        print("  [4] Full DDoS + Brute-Force   (95% -> POOR + Incident)")
        print("  [5] Custom Load Intensity     (0 - 100%)")
        print("  [6] Toggle SaaS Outage / Reconnect Buffer Flush")
        print("  [0] Exit")
        choice = input("Enter choice (0-6): ").strip()

        if choice == "0":
            break
        elif choice == "1":
            set_load(15, "NORMAL BASELINE")
        elif choice == "2":
            set_load(55, "PEAK UPI SURGE")
        elif choice == "3":
            set_load(75, "HEAVY LOAD")
        elif choice == "4":
            set_load(95, "CRITICAL OVERLOAD")
        elif choice == "5":
            try:
                val = int(input("Enter custom intensity (0-100): "))
                set_load(max(0, min(100, val)), "CUSTOM LOAD")
            except ValueError:
                print("Invalid integer.")
        elif choice == "6":
            toggle_outage()
