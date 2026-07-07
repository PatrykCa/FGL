import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Kreator Linii FUCHS Portfolio", layout="wide")

st.title("📐 Inteligentny Kreator Projektowy Nowego Zakładu")
st.subheader("Dobór aparatury i bilansowanie pod kątem Portfolio Produktów FUCHS")
st.markdown("---")

# --- 1. OFICJALNA BAZA DANYCH PODZIAŁU PORTFOLIO FUCHS OIL ---
FUCHS_PORTFOLIO = {
    # FILAR 1: INDUSTRIAL LUBRICANTS (Środki smarne dla przemysłu)
    "Industrial: Hydraulic Oils (RENOLIN)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "e_ratio": 0.02, "g_ratio": 0.0, "group": "Industrial"},
    "Industrial: Gear & Turbine Oils (RENOLIN)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.89, "cycle_h": 5, "e_ratio": 0.02, "g_ratio": 0.0, "group": "Industrial"},
    "Industrial: Slideway & Machine Oils (RENAX)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "e_ratio": 0.02, "g_ratio": 0.0, "group": "Industrial"},
    
    # FILAR 2: AUTOMOTIVE LUBRICANTS (Motoryzacja)
    "Automotive: Engine Oils (TITAN)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 5, "e_ratio": 0.02, "g_ratio": 0.0, "group": "Automotive"},
    "Automotive: Gear & Transmission Oils (TITAN)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 5, "e_ratio": 0.02, "g_ratio": 0.0, "group": "Automotive"},
    
    # FILAR 3: LUBRICATING GREASES (Smary plastyczne)
    "Greases: Plain/Roller Bearing & Multi-purpose (RENOLIT)": 
        {"material": "Stal węglowa / Specjalna (Wysoka lepkość)", "density": 0.92, "cycle_h": 10, "e_ratio": 0.11, "g_ratio": 0.19, "group": "Greases"},
    
    # FILAR 4: METAL PROCESSING LUBRICANTS (Obróbka metali - KLUCZOWE RÓŻNICE MATERIAŁOWE)
    "Metal Processing: Water-miscible Cutting/Grinding (ECOCOOL)": 
        {"material": "Stal nierdzewna (SS316L) - WODOROZCIENCZALNE!", "density": 0.99, "cycle_h": 6, "e_ratio": 0.02, "g_ratio": 0.0, "group": "Metal Processing"},
    "Metal Processing: Non-water-miscible / Neat Oils (ECOCUT)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 4, "e_ratio": 0.02, "g_ratio": 0.0, "group": "Metal Processing"},
    "Metal Processing: Corrosion Preventives (ANTICORIT)": 
        {"material": "Stal nierdzewna / Specjalna (Zależnie od bazy)", "density": 0.86, "cycle_h": 5, "e_ratio": 0.02, "g_ratio": 0.0, "group": "Metal Processing"},
    "Metal Processing: Cleaners (RENOCLEAN)": 
        {"material": "Stal nierdzewna (SS304/SS316L) - WODOROZCIENCZALNE!", "density": 1.01, "cycle_h": 4, "e_ratio": 0.02, "g_ratio": 0.0, "group": "Metal Processing"}
}

CONV_GAS = 11.35
STALE_TLO_PRAD = 800000
STALE_TLO_GAZ = 1100000
TARGET_UTILIZATION = 0.80  
AVAILABLE_HOURS_YEAR = 250 * 16  # 4000h pracy rocznie

# --- KROK 1: INTERFEJS UŻYTKOWNIKA ---
st.sidebar.header("📋 KROK 1: Portfolio FUCHS")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe FUCHS do produkcji:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Metal Processing: Water-miscible Cutting/Grinding (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("📊 KROK 2: Planowane Wolumeny [kg/rok]")

input_volumes = {}
for kat in wybrane_kategorie:
    input_volumes[kat] = st.sidebar.number_input(
        f"Roczna produkcja dla {kat}:", 
        min_value=0, value=500000, step=50000
    )

# --- 2. SILNIK OBLICZENIOWY OPTYMALIZACJI UTILIZATION ---
rekomendacje = []
total_e_proc = 0
total_g_proc = 0

for kat, wolumen in input_volumes.items():
    if wolumen == 0:
        continue
        
    rules = FUCHS_PORTFOLIO[kat]
    max_batches_per_reaktor = (AVAILABLE_HOURS_YEAR * TARGET_UTILIZATION) / rules["cycle_h"]
    required_kg_per_batch = wolumen / max_batches_per_reaktor
    required_m3_per_batch = (required_kg_per_batch / rules["density"]) / 1000
    
    # Skalowanie liczby reaktorów, jeśli szarża wychodzi za duża (> 15 m3)
    if required_m3_per_batch > 15.0:
        liczba_mieszalnikow = math.ceil(required_m3_per_batch / 12.0)
        pojemnosc_jednego = required_m3_per_batch / liczba_mieszalnikow
    else:
        liczba_mieszalnikow = 1
        pojemnosc_jednego = required_m3_per_batch
        
    pojemnosc_jednego = max(0.5, math.ceil(pojemnosc_jednego * 2) / 2)
    
    # Wyliczenie realnego wykorzystania czasowego reaktora (% Utilization)
    real_batch_capacity_kg = (pojemnosc_jednego * 1000) * rules["density"]
    real_batches_count = wolumen / real_batch_capacity_kg
    real_hours_used = real_batches_count * rules["cycle_h"]
    real_utilization = (real_hours_used / (liczba_mieszalnikow * AVAILABLE_HOURS_YEAR)) * 100
    
    total_e_proc += wolumen * rules["electricity"]
    total_g_proc += wolumen * rules["gas"]
    
    rekomendacje.append({
        "Linia / Rodzina FUCHS": kat,
        "Wolumen [kg/rok]": f"{wolumen:,}",
        "Sugerowana liczba reaktorów": liczba_mieszalnikow,
        "Zalecana Pojemność (1 szt.)": f"{pojemnosc_jednego:.1f} m³",
        "Materiał konstrukcyjny": rules["material"],
        "Docelowe Wykorzystanie (% Utilization)": f"{real_utilization:.1f}%"
    })

# --- 3. WIZUALIZACJA I SPECYFIKACJA TECHNICZNA ---
st.header("🏢 Rekomendacja Linii Produkcyjnych i Dobór Materiałów")
st.markdown("Algorytm przeanalizował gęstości baz oraz korozyjność komponentów wodorozcieńczalnych:")

if rekomendacje:
    st.table(pd.DataFrame(rekomendacje))
else:
    st.info("Wybierz rodziny z portfolio FUCHS w panelu bocznym.")

st.markdown("---")
st.header("⚡ Szacowany Bilans Mediów Energetycznych Zakładu")

total_electricity = STALE_TLO_PRAD + total_e_proc
total_gas_m3 = (STALE_TLO_GAZ + total_g_proc) / CONV_GAS

c1, c2 = st.columns(2)
with c1:
    st.metric(label="⚡ Łączny Prąd Zakładu (Mieszalniki + Tło)", value=f"{int(total_electricity):,} kWh/rok")
with c2:
    st.metric(label="🔥 Łączne Zapotrzebowanie na Gaz", value=f"{int(total_gas_m3):,} m³/rok")
