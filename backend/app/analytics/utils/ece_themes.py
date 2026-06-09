"""ECE-relevant research theme labels mapped from project title keywords."""

from __future__ import annotations

import re
from collections import Counter

ECE_THEMES: list[tuple[str, list[str]]] = [
    ("VLSI & Embedded Systems", ["vlsi", "fpga", "asic", "embedded", "soc", "rtl", "verilog", "hdl", "chip"]),
    ("Signal Processing & Communications", ["signal", "communication", "dsp", "modulation", "ofdm", "wireless", "lte", "5g", "6g"]),
    ("Power Electronics & Energy Systems", ["power", "energy", "converter", "inverter", "grid", "battery", "photovoltaic", "solar"]),
    ("IoT & Wireless Networks", ["iot", "sensor", "wsn", "lora", "zigbee", "bluetooth", "wifi", "network"]),
    ("Control Systems & Robotics", ["control", "robot", "robotics", "automation", "pid", "uav", "drone"]),
    ("Analog & Digital Circuits", ["analog", "digital", "circuit", "amplifier", "filter", "adc", "dac"]),
    ("RF & Microwave Engineering", ["rf", "microwave", "antenna", "radar", "millimeter", "mmwave", "terahertz"]),
    ("Machine Learning for ECE Applications", ["machine learning", "deep learning", "neural", "classification", "cnn", "ai"]),
    ("Biomedical Electronics", ["biomedical", "ecg", "eeg", "medical", "health", "biosignal", "wearable"]),
    ("Semiconductor Devices", ["semiconductor", "mosfet", "transistor", "memristor", "nanoelectronics", "device"]),
]

_STOP_WORDS = frozenset(
    "a an the and or of in on for to with by from at is are was were be been being "
    "using based study design analysis system implementation via into over under "
    "iiitd iiit delhi project thesis".split()
)


def classify_project_theme(title: str) -> str:
    """Map a project title to the best-matching ECE theme."""
    lower = title.lower()
    best_label = "Other ECE Research"
    best_hits = 0
    for label, keywords in ECE_THEMES:
        hits = sum(1 for kw in keywords if kw in lower)
        if hits > best_hits:
            best_hits = hits
            best_label = label
    if best_hits == 0:
        words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", lower)
        for w in words:
            if w not in _STOP_WORDS:
                return "Other ECE Research"
    return best_label


def theme_distribution(titles: list[str]) -> list[dict]:
    counter: Counter[str] = Counter()
    for title in titles:
        counter[classify_project_theme(title)] += 1
    ordered_labels = [label for label, _ in ECE_THEMES] + ["Other ECE Research"]
    return [{"theme": label, "count": counter.get(label, 0)} for label in ordered_labels if counter.get(label, 0)]
