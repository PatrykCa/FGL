import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Kreator Linii FUCHS Portfolio", layout="wide")

st.title("🏭 Zaawansowany Kreator Produkcyjny FUCHS Oil")
st.subheader("Optymalizacja szarż, współdzielenie zbiorników oraz miesięczny bilans ciepła i chłodzenia")
st.markdown("---")

# --- 1. ROZBUDOWANA BAZA DANYCH PRODUKTÓW (PARAMETRY TERMICZNE) ---
# cp: ciepło właściwe [kJ/(kg*K)] - oleje ok. 2.0, wodorozcieńczalne (blisko wody) ok. 3.8
# dT_heat: o ile stopni trzeba podgrzać (np. z 15°C do 60°C -> dT = 45)
# dT_cool: o ile stopni trzeba schłodzić po procesie przed rozlewem (np. z 60°C do 25°C -> dT = 35)
FUCHS_PORTFOLIO = {
    "Industrial: Hydraulic Oils (RENOLIN)": 
        {"material": "Stal węglowa", "density": 0.88, "cycle_h": 4, "type": "Olej jasny", "cp": 2.0, "dT_heat": 40, "dT_cool": 30},
    "Industrial: Gear & Turbine Oils (RENOLIN)": 
        {"material": "Stal węglowa", "density": 0.89, "cycle_h": 5, "type": "Olej ciemny/EP", "cp": 1.9, "dT_heat": 45, "dT_cool": 35},
    "Industrial: Slideway & Machine Oils (RENAX)": 
        {"material": "Stal węglowa", "density": 0.88, "cycle_h": 4, "type": "Olej jasny", "cp": 2.0, "dT_heat": 35, "dT_cool": 25},
    "Automotive: Engine Oils (TITAN)": 
        {"material": "Stal węglowa", "density": 0.87, "cycle_h": 5, "type": "Olej silnikowy", "cp": 2.1, "dT_heat": 45, "dT_cool": 35},
    "Automotive: Gear & Transmission Oils (TITAN)": 
        {"material": "Stal węglowa", "density": 0.88, "cycle_h": 5, "type": "Olej przekładniowy", "cp": 2.0, "dT_heat": 50, "dT_cool": 40},
    "Metal Processing: Water-miscible (ECOCOOL)": 
        {"material": "Stal nierdzewna (SS316L)", "density": 0.99, "cycle_h": 6, "type": "Wodorozcieńczalny", "cp": 3.8, "dT_heat": 15, "dT_cool": 10},
    "Metal Processing: Non-water-miscible (ECOCUT)": 
        {"material": "Stal węglowa", "density": 0.87, "cycle_h": 4, "type": "Olej obróbczy", "cp": 2.0, "dT_heat": 30, "dT_cool": 20},
    "Metal Processing: Cleaners (RENOCLEAN)": 
        {"material": "Stal nierdzewna (SS304/316L)", "density": 1.01, "cycle_h": 4, "type": "Wodorozcieńczalny", "cp": 3.9, "dT_heat": 20, "dT_cool": 15}
}

AVAILABLE_HOURS_YEAR = 250 * 16  
TARGET_UTILIZATION = 0.80

# --- PANEL BOCZNY ---
st.sidebar.header("📋 KROK 1: Założenia i Wolumeny")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe do planowania:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
input_volumes = {}
for kat in wybrane_kategorie:
    input_volumes[kat] = st.sidebar.number_input(
        f"Roczna produkcja dla {kat} [kg]:", 
        min_value=0, value=600000, step=50000
    )

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Strategia Alokacji")
wspoldzielenie = st.sidebar.toggle("Włącz współdzielenie zbiorników (Konsolidacja)", value=True)

# --- 2. SILNIK OBLICZENIOWY: PRODUKCJA I ENERGIA ---
rekomendacje = []
total_monthly_heat_GJ = 0
total_monthly_cool_GJ = 0

grupy_mieszalnikow = {
    "Węzeł 1: Oleje Przemysłowe i Motoryzacyjne (Stal węglowa)": {"wolumen": 0, "produkty": [], "max_cycle": 0, "avg_density": 0.0},
    "Węzeł 2: Produkty Wodorozcieńczalne ECOCOOL/CLEAN (Stal nierdzewna)": {"wolumen": 0, "produkty": [], "max_cycle": 0, "avg_density": 0.0}
}

# Obliczanie ciepła dla każdego produktu indywidualnie (niezależnie od sposobu mieszania)
for kat, wolumen in input_volumes.items():
    if wolumen == 0:
        continue
    rules = FUCHS_PORTFOLIO[kat]
    
    # Miesięczna masa [kg]
    m_month = wolumen / 12
    
    # Obliczanie zapotrzebowania termicznego: Q = m * cp * dT [w kJ] -> / 1000000 daje GigaDżule [GJ]
    # Sprawność układu grzewczego/chłodzącego przyjęta na poziomie 85% (dzielenie przez 0.85)
    heat_gj = (m_month * rules["cp"] * rules["dT_heat"]) / (1_000_000 * 0.85)
    cool_gj = (m_month * rules["cp"] * rules["dT_cool"]) / (1_000_000 * 0.85)
    
    total_monthly_heat_GJ += heat_gj
    total_monthly_cool_GJ += cool_gj

    if not wspoldzielenie:
        max_batches_year = (AVAILABLE_HOURS_YEAR * TARGET_UTILIZATION) / rules["cycle_h"]
        req_kg_batch = wolumen / max_batches_year
        req_m3 = max(0.5, math.ceil(((req_kg_batch / rules["density"]) / 1000) * 2) / 2)
        
        real_capacity_kg = req_m3 * 1000 * rules["density"]
        total_batches_year = math.ceil(wolumen / real_capacity_kg)
        batches_month = total_batches_year / 12
        batches_week = total_batches_year / 52
        real_utilization = ((total_batches_year * rules["cycle_h"]) / AVAILABLE_HOURS_YEAR) * 100
        
        rekomendacje.append({
            "Mieszalnik / Grupa": f"Dedykowany dla: {kat}",
            "Miesięczna produkcja [kg]": f"{int(m_month):,}",
            "Pojemność [m³]": f"{req_m3:.1f} m³",
            "Szarże / Miesiąc": f"{batches_month:.1f}",
            "Szarże / Tydzień": f"{batches_week:.1f}",
            "Ciepło Grzewcze [GJ/miesiąc]": f"{heat_gj:.2f}",
            "Chłodzenie Technologiczne [GJ/miesiąc]": f"{cool_gj:.2f}",
            "Materiał": rules["material"],
            "Utilization": f"{real_utilization:.1f}%"
        })
    else:
        if rules["type"] == "Wodorozcieńczalny":
            g_key = "Węzeł 2: Produkty Wodorozcieńczalne ECOCOOL/CLEAN (Stal nierdzewna)"
        else:
            g_key = "Węzeł 1: Oleje Przemysłowe i Motoryzacyjne (Stal węglowa)"
            
        grupy_mieszalnikow[g_key]["wolumen"] += wolumen
        grupy_mieszalnikow[g_key]["produkty"].append(kat)
        grupy_mieszalnikow[g_key]["max_cycle"] = max(grupy_mieszalnikow[g_key]["max_cycle"], rules["cycle_h"])
        grupy_mieszalnikow[g_key]["avg_density"] = rules["density"]

if wspoldzielenie:
    for nazwa_wezla, dane in grupy_mieszalnikow.items():
        if dane["wolumen"] == 0:
            continue
        max_batches_year = (AVAILABLE_HOURS_YEAR * TARGET_UTILIZATION) / dane["max_cycle"]
        req_kg_batch = dane["wolumen"] / max_batches_year
        req_m3 = ((req_kg_batch / dane["avg_density"]) / 1000)
        
        liczba_urzadzen = 1
        if req_m3 > 15.0:
            liczba_urzadzen = math.ceil(req_m3 / 12.0)
            req_m3 = req_m3 / liczba_urzadzen
            
        req_m3 = max(0.5, math.ceil(req_m3 * 2) / 2)
        real_capacity_kg = req_m3 * 1000 * dane["avg_density"] * liczba_urzadzen
        total_batches_year = math.ceil(dane["wolumen"] / (real_capacity_kg / liczba_urzadzen))
        
        batches_month = total_batches_year / 12
        batches_week = total_batches_year / 52
        real_utilization = ((total_batches_year * dane["max_cycle"]) / (AVAILABLE_HOURS_YEAR * liczba_urzadzen)) * 100
        
        # Wyliczenie sumarycznego ciepła przypisanego do danego węzła
        w_heat_gj = 0
        w_cool_gj = 0
        for p in dane["produkty"]:
            p_m_month = input_volumes[p] / 12
            w_heat_gj += (p_m_month * FUCHS_PORTFOLIO[p]["cp"] * FUCHS_PORTFOLIO[p]["dT_heat"]) / (1_000_000 * 0.85)
            w_cool_gj += (p_m_month * FUCHS_PORTFOLIO[p]["cp"] * FUCHS_PORTFOLIO[p]["dT_cool"]) / (1_000_000 * 0.85)

        rekomendacje.append({
            "Mieszalnik / Grupa": f"{nazwa_wezla} (Ilość: {liczba_urzadzen} szt.)",
            "Miesięczna produkcja [kg]": f"{int(dane['wolumen']/12):,}",
            "Pojemność (1 szt.) [m³]": f"{req_m3:.1f} m³",
            "Szarże / Miesiąc": f"{batches_month:.1f}",
            "Szarże / Tydzień": f"{batches_week:.1f}",
            "Ciepło Grzewcze [GJ/miesiąc]": f"{w_heat_gj:.2f}",
            "Chłodzenie Technologiczne [GJ/miesiąc]": f"{w_cool_gj:.2f}",
            "Materiał": "Stal nierdzewna" if "nierdzewna" in nazwa_wezla else "Stal węglowa",
            "Utilization": f"{real_utilization:.1f}%"
        })

# --- 3. PREZENTACJA TABELI WYNIKÓW ---
st.header("📊 Miesięczny Plan Produkcji, Szarż i Energii Termicznej")
if rekomendacje:
    st.table(pd.DataFrame(rekomendacje))
else:
    st.info("Zaznacz produkty w panelu bocznym.")

# --- 4. ZBIORCZY BILANS MEDIÓW TERMICZNYCH ---
st.markdown("---")
st.header("🌡️ Łączne Miesięczne Zapotrzebowanie Termiczne Zakładu")
st.markdown("Parametry niezbędne do doboru kotłowni (pary/oleju grzewczego) oraz agregatu wody lodowej (chłodni kominowej):")

c1, c2 = st.columns(2)
with c1:
    st.metric(
        label="🔥 POTRZEBNE CIEPŁO (Grzanie szarży)", 
        value=f"{total_monthly_heat_GJ:.1f} GJ / miesiąc",
        help="Energia potrzebna do podgrzania baz i surowców w płaszczach grzewczych reaktorów."
    )
with c2:
    st.metric(
        label="❄️ POTRZEBNE CHŁODZENIE (Zrzut temperatury)", 
        value=f"{total_monthly_cool_GJ:.1f} GJ / miesiąc",
        help="Ciepło, które należy odebrać z produktu za pomocą wody chłodzącej przed przepompowaniem do magazynu gotowego."
    )

st.markdown("---")

# --- 5. ASYSTENT SEKWENCJONOWANIA SZARŻ (CO PO CZYM) ---
st.header("🔄 Interaktywna Matryca Przezbrojeń (Sekwencjonowanie)")
col1, col2 = st.columns(2)
with col1:
    prod_aktualny = st.selectbox("1. Produkt, który był produkowany PRZED CHWILĄ (Ostatnia szarża):", list(FUCHS_PORTFOLIO.keys()), index=0)
with col2:
    prod_nastepny = st.selectbox("2. Produkt, który chcesz produkować TERAZ (Następna szarża):", list(FUCHS_PORTFOLIO.keys()), index=1)

type_akt = FUCHS_PORTFOLIO[prod_aktualny]["type"]
type_nast = FUCHS_PORTFOLIO[prod_nastepny]["type"]

st.markdown("### 🔔 Wynik weryfikacji technologicznej:")
if prod_aktualny == prod_nastepny:
    st.success("🟢 **Ta sama rodzina produktowa:** Kontynuacja bez przezbrajania i strat energii.")
elif type_akt == "Wodorozcieńczalny" and type_nast != "Wodorozcieńczalny":
    st.error("🔴 **KRYTYCZNE ZAGROŻENIE:** Przejście z chłodziwa wodnego na olej. Wymagane suszenie instalacji i mycie. Ryzyko zmatowienia i zniszczenia oleju!")
elif type_akt != "Wodorozcieńczalny" and type_nast == "Wodorozcieńczalny":
    st.error("🔴 **KRYTYCZNE ZAGROŻENIE:** Przejście z oleju na produkt wodny (ECOCOOL). Ślady oleju zepsują stabilność emulsji. Wymagane mycie detergentami!")
elif type_akt == "Olej ciemny/EP" and type_nast == "Olej jasny":
    st.warning("🟡 **WYMAGANE PŁUKANIE (Flushing):** Ryzyko skażenia koloru i przeniesienia agresywnych dodatków EP do jasnego oleju. Wymagane płukanie gorącą bazą.")
else:
    st.info("🟡 **ZALECANE PRZEDMUCHANIE / LEKKIE PŁUKANIE:** Przejście między kompatybilnymi bazami mineralnymi.")
