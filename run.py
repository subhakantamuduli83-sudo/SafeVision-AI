import socket
import uvicorn
import os
import sys

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def get_local_ip():
    """Finds the local network IP of this laptop."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def print_banner(ip):
    print("=" * 65)
    print("   [SAFEVISION AI] SAFETY GEAR COMPLIANCE & HAZARD MONITORING")
    print("   STPI & EmTek BPUT Hackathon Project")
    print("=" * 65)
    print(f"\n[+] Laptop 1 Local Server: http://localhost:8000")
    print(f"[+] Laptop 2 (Control Room) Dashboard URL: http://{ip}:8000")
    print("\n[+] Mobile Camera (Wireless CCTV) Setup:")
    print("    1. Open 'IP Webcam' app on your phone.")
    print("    2. Tap 'Start Server'.")
    print("    3. In the dashboard, enter the Mobile URL (e.g. http://192.168.x.x:8080/video)")
    print("\n[+] External Speaker:")
    print("    Connect to Laptop 1 audio jack or Bluetooth for voice & siren alerts.")
    print("=" * 65)
    print("Starting server now...\n")

if __name__ == "__main__":
    ip = get_local_ip()
    print_banner(ip)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
