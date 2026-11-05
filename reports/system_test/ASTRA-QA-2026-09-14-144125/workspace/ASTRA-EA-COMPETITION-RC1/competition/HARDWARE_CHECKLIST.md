# ASTRA-EA: Demonstration Hardware Checklist

**Classification:** Physical Operations Pre-Flight Packing & Deployment Checklist  
**Release:** `ASTRA-EA-COMPETITION-RC1`

---

## 1. Primary Computing & Power Hardware
- [ ] **Primary Workstation / Laptop:**
  - OS: Linux x86_64 (Kernel 6.x+)
  - GPU: Dedicated NVIDIA GPU (or Intel/AMD CPU with AVX2)
  - Battery: Charged to 100%
- [ ] **Workstation Power Adapter:** High-wattage power brick + power cord
- [ ] **Backup Laptop:** Configured with identical git clone, venv, and frozen weights
- [ ] **Power Strip / Extension Cable:** 3-meter grounded surge-protected extension cord

---

## 2. Optical Sensors & Mounting Hardware
- [ ] **Primary Camera:** USB 3.0 Full HD (1080p, 30+ FPS) webcam
- [ ] **Backup Camera:** Secondary 1080p USB webcam
- [ ] **Camera Mount / Tripod:** Adjustable tabletop mount or overhead gooseneck clamp (40–60 cm elevation)
- [ ] **USB Cables & Adapters:** High-speed USB-A to USB-C adapters (if applicable)

---

## 3. Physical Laboratory Experiment Apparatus
- [ ] **Specimen Tube:** Cylindrical tube with green screw cap (Primary nominal target)
- [ ] **Centrifuge Tube:** Conical 15ml tube with blue cap (Primary deviation object)
- [ ] **Micropipette Tool:** Handheld pipettor (nominal Step 2 / recovery target)
- [ ] **Tube Holding Rack:** Acrylic or plastic 4-way laboratory rack
- [ ] **White Non-Reflective Mat:** Neutral gray or white workspace surface to ensure optimal contrast

---

## 4. Audio, Networking & Display Cables
- [ ] **External Audio Speaker / Headset:** 3.5mm jack or USB speaker for audible cockpit voice alerts
- [ ] **Cat6 Ethernet Cable:** 2-meter patch cable for demonstrating network disconnect & reconnect
- [ ] **HDMI / DisplayPort Cable:** For connecting to judge review monitors or overhead projectors
- [ ] **Display Adapters:** USB-C to HDMI / VGA adapter

---

## 5. Offline Emergency Backups & Documentation
- [ ] **Encrypted USB 3.0 Flash Drive:**
  - Complete git repository clone + frozen model checkpoint
  - `requirements-lock.txt` and offline pip wheelhouse
  - Standalone HTML reports (`final_traceability_example.html`, `comparison.html`)
  - Recorded fallback demonstration video (`final_submission/demo_videos/`)
- [ ] **Printed Materials:**
  - 3 printed copies of `competition/QUICK_REFERENCE_CARD.md`
  - 1 printed copy of `competition/OPERATOR_MANUAL.md`
  - 1 printed copy of `docs/final/sih-requirement-traceability.md`
