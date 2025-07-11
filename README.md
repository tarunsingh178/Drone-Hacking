# 📡 Wi-Fi Drone Hacking & Protocol Analysis (Educational Project)

> **⚠️ Disclaimer**: This project was conducted for educational and ethical cybersecurity research only. All tests were performed on personally-owned hardware in a controlled lab environment. Unauthorized access to devices is strictly illegal.

## 🚀 Project Overview

This repository contains the research, analysis, and ethical hacking of a **Wi-Fi-based drone**, aiming to understand its communication protocols, security flaws, and potential attack vectors.

The primary goal was to analyze how the drone communicates with its mobile application and identify any vulnerabilities in its Wi-Fi-based command/control channels.

## 🎯 Objectives

- Discover and connect to the drone's hidden Wi-Fi network.
- Intercept, log, and analyze traffic between the drone and its controller app.
- Reverse engineer the mobile app and identify command payloads.
- Recreate and send commands to the drone from a custom script.
- Evaluate the security measures implemented (or lack thereof).

## 🧰 Tools Used

- **Wireshark** – for network packet capture and protocol analysis.
- **nmap / netdiscover / airodump-ng** – for network and Wi-Fi reconnaissance.
- **APKTool / JADX** – for decompiling and reverse engineering the Android app.
- **Python (Scapy / Sockets)** – for crafting and sending custom packets.
- **ProxyDroid / Burp Suite / mitmproxy** – for app traffic interception (if HTTP-based).
- **Linux (Kali/Ubuntu)** – primary analysis environment.

## 🔍 Methodology

### 1. Network Discovery
- Identified that the drone acts as a Wi-Fi Access Point (AP).
- Connected directly to the drone’s Wi-Fi using a phone/laptop.
- Detected hidden SSID and retrieved it using `airodump-ng`.

### 2. Packet Capture & Analysis
- Captured communication between the app and drone using Wireshark.
- Identified control packets (e.g., UDP or TCP commands sent on specific ports).
- Analyzed video stream, telemetry data, and control signals.

### 3. App Reverse Engineering
- Decompiled the drone control APK.
- Located classes and methods responsible for socket communication.
- Extracted IP, ports, and message structures (e.g., JSON or byte arrays).

### 4. Custom Payload Injection
- Recreated command packets using Python and sent them to the drone via socket.
- Successfully emulated movement commands (takeoff, land, directional control).

### 5. Vulnerability Assessment
- Found that the drone does not implement:
  - Encryption (commands sent in plain text)
  - Authentication or pairing mechanisms
- Demonstrated how a rogue device could hijack the session.


