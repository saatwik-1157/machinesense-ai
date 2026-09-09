# SIH 2026 — Where SentinelAI and MachineSense AI Fit

226 problem statements, submission deadline **20 September 2026**, 500 idea slots per PS.

Two framing facts before anything else: there is **no women-safety PS and no MSME predictive-maintenance PS** in SIH 2026. Both projects were written for other competitions (SentinelAI for "Sovereign Technology for India", MachineSense for the MSME Idea Hackathon). The technology in both survives the move; the *pitch* in both does not. What follows is what to keep, what to rewrite, and what to throw away.

---

## SentinelAI

### Lead choice — SIH26187 (Software · Smart Automation · Ministry of Home Affairs)
*AI-Based Intelligent Video Analytics Platform for Border Surveillance using existing CCTV Infrastructure*

This is SentinelAI's own thesis, restated by MHA: turn existing passive cameras into an active detection network **without new hardware**. Their required feature list — human detection and tracking, vehicle detection, face detection, ANPR, virtual-fence intrusion, suspicious-activity detection, night-time movement, real-time alerts, command-centre integration — is roughly the SentinelAI node minus the pole.

**Keep**
- The core argument: existing infrastructure → intelligent network, no proprietary smart cameras. Verbatim from your Q1/Q2.
- Multi-sensor validation engine → rename to **multi-cue validation** (detection + tracking + temporal persistence across frames/cameras) and sell it as the false-alarm killer. This is your strongest differentiator and MHA cares about it.
- Edge/on-prem inference and privacy-by-local-processing. Border posts have poor connectivity — this is a requirement, not a nice-to-have.
- Safe Corridor → recast as **cross-camera handoff and continued track** of an intruder across BOP cameras. Same code, defensible framing, directly answers "object tracking".
- Alert pipeline, GPS/geolocation of events, event logging, command dashboard.
- YOLO / OpenCV / TensorFlow stack. React + Node dashboard is fine.

**Rewrite**
- Target audience: police, ambulance, family → **border security forces, BOP command, control room operators**. Delete family notification entirely.
- Scenario set: accidents and women's distress → **intrusion, unauthorised vehicle, night movement, loitering near the fence**.

**Drop**
- Streetlight/smart-pole hardware, illumination control, ESP32-class sensing. PS is software-only over standard IP CCTV.
- Acoustic and vibration sensors. Nothing in the PS ingests them.
- ₹18–20 L budget, patent claims, market/audience slides — SIH scores solution and feasibility, not investment.

**Build before submitting**
Working ANPR + OCR (this is where most teams underdeliver), virtual-fence drawing UI, and a false-positive rate number from a real test clip. A demo with a measured precision/recall beats a polished deck.

### Alternate A — SIH26178 (Hardware · Disaster Management · Qualcomm)
*Distributed AI-powered environmental monitoring network*

Pick this one if you want to **keep SentinelAI's architecture intact**. Distributed nodes, on-device inference, only alerts and summaries sent upstream, keeps working during network outages — that is literally your smart-pole mesh, with the sensing domain swapped from crime to floods, fires, air quality and landslide precursors. The Safe Corridor collaboration logic survives as node-to-node corroboration of a hazard. Cost: it is a Hardware PS, so you must build a physical node, and the CV work mostly goes away.

### Alternate B — SIH26124 (Software · BEL) *Mobile urban intelligence using public transport fleet*
Closest to SentinelAI's emergency-response soul: edge AI on cameras, hit-and-run detection with plate extraction and confidence score, vulnerable-pedestrian detection, GIS command dashboard. Choose this if the team prefers civilian public safety over border security.

### Alternate C — SIH26127 (Software · BEL) *City-wide multi-camera ANPR trajectory tracking*
Take it only if the team is genuinely strong on OCR — the PS demands >90% plate accuracy in rain, blur and angled shots, and grading will hinge on that single number.

---

## MachineSense AI

### Lead choice — SIH26170 (Software · Smart Automation · ISRO)
*AI-Driven Anomaly Detection in Component Burn-In & Screening*

Highest fit-to-existing-code of anything in the 226. Their three deliverables are three things you have already written in `backend/ml.py`:

| ISRO asks for | You already have |
|---|---|
| Module A — dynamic outlier detection against lot statistics, not static limits | robust MAD z-score against each unit's own recent history |
| Module B — regress Value_0h + Value_24h → Value_168h, flag excess drift slope | least-squares slope extrapolation to a failure threshold |
| Explainability — justify the call to a QA inspector, not a black box | your XAI per-sensor attribution with plain-language reasons |

Explainability is an explicit **evaluation metric** here. That is your entire differentiator, already built, already scored.

**Keep** — `ml.py` anomaly and trend engine, the XAI attribution layer, the dashboard shell and charts.
**Rewrite** — sensors (vibration/temperature/current) become parametric measurements (Iddq, leakage current, propagation delay); machines become component lots; health score becomes a screening risk score.
**Drop** — digital twin, energy/CO₂/₹ tariff module, MSME framing, SaaS model, ESP32 kit, the ₹19.8 L budget.
**Add** — asymmetric cost weighting so false negatives are punished hard (they say a missed defective part is catastrophic), and MAE reporting on the 168h prediction.

### Alternate — SIH26054 (Software · Robotics and Drones · DRDO)
*Real-time Digital Twin for health monitoring, fault prediction and RUL of aero piston engines in MALE UAVs*

Pick this if you want to **show the whole platform**. Every MachineSense module has a home: health score → engine health indicators, MAD anomaly → abnormal operating condition detection, RUL slope → RUL estimation, digital twin what-if → mission-profile simulation, XAI → operator justification, dashboard → real-time engine visualisation. Keep the simulator too; you have no real engine data and the PS accepts simulated state.

The one gap that will decide your score: DRDO wants a **physics-informed** twin — thermodynamic behaviour models and engine performance maps fused with the ML, plus mission replay. Your current twin is a statistical severity-reduction model. Budget real time for adding a physics layer, or the judges will read it as a dashboard rather than a digital twin.

**Drop** for either: MSME positioning, energy cost in ₹, CO₂, market size, business model, project cost.

### If you want a hardware track instead
SIH26008 (Ministry of Steel) — conveyor belt joint rupture and damage prediction in iron ore mining. Same predictive-maintenance logic, physical sensing rig required.

---

## Recommendation in one line each

SentinelAI → **SIH26187 (MHA)** if you want software and reuse of the CV work; **SIH26178 (Qualcomm)** if you want to keep the distributed-node architecture and are willing to build hardware.

MachineSense AI → **SIH26170 (ISRO)** for the highest probability of a working, defensible submission; **SIH26054 (DRDO)** if you want to demo the full platform and can add a physics model.

One caution on pairing: SIH26187 and SIH26170 are both filed under **Smart Automation**. If your college caps entries per theme, split the pair instead — SentinelAI on SIH26187 (Smart Automation) with MachineSense on SIH26054 (Robotics and Drones), or SentinelAI on SIH26178 (Disaster Management) with MachineSense on SIH26170 (Smart Automation).
