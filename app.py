import streamlit as st
import pandas as pd
import math
import os

st.set_page_config(page_title="Kreator Linii FUCHS Portfolio", layout="wide")

st.title("🏭 Kompleksowy Kreator Produkcyjny FUCHS Oil")
st.subheader("System Projektowania Procesowego i Logistyki Szarż (T -> MT -> IT -> FM/FL)")
st.markdown("---")

# --- 1. BAZA DANYCH RODZIN PRODUKTOWYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Industrial: Hydraulic Oils (RENOLIN)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "type": "Olej jasny", "cp": 2.0, "dT_heat": 40, "dT_cool": 30, "stir_kw_per_m3": 0.7, "pdf": "PID_Olejowy.pdf"},
    "Industrial: Gear & Turbine Oils (RENOLIN)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.89, "cycle_h": 5, "type": "Olej ciemny/EP", "cp": 1.9, "dT_heat": 45, "dT_cool": 35, "stir_kw_per_m3": 1.1, "pdf": "PID_Olejowy.pdf"},
    "Industrial: Slideway & Machine Oils (RENAX)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "type": "Olej jasny", "cp": 2.0, "dT_heat": 35, "dT_cool": 25, "stir_kw_per_m3": 0.7, "pdf": "PID_Olejowy.pdf"},
    "Automotive: Engine Oils (TITAN)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 5, "type": "Olej silnikowy", "cp": 2.1, "dT_heat": 45, "dT_cool": 35, "stir_kw_per_m3": 0.9, "pdf": "PID_Olejowy.pdf"},
    "Automotive: Gear & Transmission Oils (TITAN)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 5, "type": "Olej przekładniowy", "cp": 2.0, "dT_heat": 50, "dT_cool": 40, "stir_kw_per_m3": 1.2, "pdf": "PID_Olejowy.pdf"},
    "Metal Processing: Water-miscible (ECOCOOL)": 
        {"material": "Stal nierdzewna (SS316L)", "density": 0.99, "cycle_h": 6, "type": "Wodorozcieńczalny", "cp": 3.8, "dT_heat": 15, "dT_cool": 10, "stir_kw_per_m3": 0.8, "pdf": "PID_Wodny.pdf"},
    "Metal Processing: Non-water-miscible (ECOCUT)": 
        {"material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 4, "type": "Olej obróbczy", "cp": 2.0, "dT_heat": 30, "dT_cool": 20, "stir_kw_per_m3": 0.8, "pdf": "PID_Olejowy.pdf"},
    "Metal Processing: Cleaners (RENOCLEAN)": 
        {"material": "Stal nierdzewna (SS304/316L)", "density": 1.01, "cycle_h": 4, "type": "Wodorozcieńczalny", "cp": 3.9, "dT_heat": 20, "dT_cool": 15, "stir_kw_per_m3": 0.6, "pdf": "PID_Wodny.pdf"}
}

AVAILABLE_HOURS_YEAR = 250 * 16  # 4000h (Praca na 2 zmiany)

# --- 2. PANEL BOCZNY (INPUTY) ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin FUCHS")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe do planowania:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Parametry i Opakowania")

input_data = {}
for kat in wybrane_kategorie:
    st.sidebar.markdown(f"### 🧪 {kat}")
    vol = st.sidebar.number_input(f"Roczna produkcja [kg]:", min_value=0, value=1200000, step=100000, key=f"vol_{kat}")
    batches = st.sidebar.number_input(f"Planowana liczba szarż/rok:", min_value=1, value=150, step=10, key=f"bat_{kat}")
    
    # Wybór dominującego typu opakowania dla linii rozlewczej
    pack = st.sidebar.selectbox(
        "Główne opakowanie końcowe (FL):",
        ["1l (Detal)", "4l / 5l (Karton)", "10l / 20l (Kanister)", "60l / 200l (Beczka)", "1000l (Paletopojemnik IBC)", "Bulk (Cysterna luz)"],
        index=3,
        key=f"pack_{kat}"
    )
    input_data[kat] = {"wolumen": vol, "szarze_rok": batches, "opakowanie": pack}

st.sidebar.markdown("---")
st.sidebar.header("🏢 Strategia Konsolidacji")
wspoldzielenie = st.sidebar.toggle("Włącz współdzielenie zbiorników (Węzły produkcyjne)", value=True)


# --- 3. SILNIK OBLICZENIOWY ---
rekomendacje_logistyka = []
specyfikacja_ciagu_technologicznego = []
total_monthly_heat_GJ = 0
total_monthly_cool_GJ = 0

# Definicja struktur dla zintegrowanych węzłów (gdy konsolidacja jest włączona)
grupy_mieszalnikow = {
    "Węzeł 1: Oleje Przemysłowe i Motoryzacyjne": {"id": 1, "tag": "100", "wolumen": 0, "szarze_rok": 0, "produkty": [], "max_cycle": 0, "avg_density": 0.0, "max_stir": 0.0, "pdf": "PID_Olejowy.pdf"},
    "Węzeł 2: Produkty Wodorozcieńczalne ECOCOOL/CLEAN": {"id": 2, "tag": "200", "wolumen": 0, "szarze_rok": 0, "produkty": [], "max_cycle": 0, "avg_density": 0.0, "max_stir": 0.0, "pdf": "PID_Wodny.pdf"}
}

# Obliczenia podstawowe (Pętla po produktach)
for kat, dane in input_data.items():
    wolumen = dane["wolumen"]
    if wolumen == 0:
        continue
    rules = FUCHS_PORTFOLIO[kat]
    m_month = wolumen / 12
    
    # Bilans energii cieplnej (Sprawność układu grzania/chłodzenia przyjęta jako 85%)
    heat_gj = (m_month * rules["cp"] * rules["dT_heat"]) / (1_000_000 * 0.85)
    cool_gj = (m_month * rules["cp"] * rules["dT_cool"]) / (1_000_000 * 0.85)
    
    total_monthly_heat_GJ += heat_gj
    total_monthly_cool_GJ += cool_gj

    # OPCJA A: BRAK KONSOLIDACJI (Linie dedykowane oddzielnie)
    if not wspoldzielenie:
        req_kg_batch = wolumen / dane["szarze_rok"]
        req_m3 = max(0.5, math.ceil(((req_kg_batch / rules["density"]) / 1000) * 2) / 2)
        batches_month = dane["szarze_rok"] / 12
        batches_week = dane["szarze_rok"] / 52
        real_utilization = ((dane["szarze_rok"] * rules["cycle_h"]) / AVAILABLE_HOURS_YEAR) * 100
        
        rekomendacje_logistyka.append({
            "Linia Produktowa": f"Dedykowana: {kat}",
            "Miesięczna produkcja [kg]": f"{int(m_month):,}",
            "Zalecana Pojemność MT [m³]": f"{req_m3:.1f} m³",
            "Szarże / Miesiąc": f"{batches_month:.1f}",
            "Szarże / Tydzień": f"{batches_week:.1f}",
            "Materiał konstrukcyjny": rules["material"],
            "Utilization (%)": f"{real_utilization:.1f}%"
        })
        
        p_motor = max(0.75, math.ceil((req_m3 * rules["stir_kw_per_m3"]) * 2) / 2)
        id_suffix = len(specyfikacja_ciagu_technologicznego) + 101
        
        specyfikacja_ciagu_technologicznego.append({
            "Ciąg Technologiczny": f"Linia dedykowana {kat.split(':')[-1].strip()}",
            "Zbiornik Baz B (T)": f"T-{id_suffix} ({req_m3 * 1.5:.1f} m³)",
            "Mieszalnik (MT)": f"MT-{id_suffix} ({req_m3:.1f} m³ / {p_motor:.1f} kW)",
            "Bufor Produktu (IT)": f"IT-{id_suffix} ({req_m3 * 1.2:.1f} m³)",
            "Nalewak (FM) + Linia (FL)": f"FM-{id_suffix} + FL-{id_suffix} ({dane['opakowanie']})",
            "Ciepło MT [GJ/m]": f"{heat_gj:.2f}",
            "Chłodzenie MT [GJ/m]": f"{cool_gj:.2f}",
            "Plik PDF": rules["pdf"]
        })
        
    # OPCJA B: WŁĄCZONE WSPÓŁDZIELENIE (Agregacja do Węzłów)
    else:
        if rules["type"] == "Wodorozcieńczalny":
            g_key = "Węzeł 2: Produkty Wodorozcieńczalne ECOCOOL/CLEAN"
        else:
            g_key = "Węzeł 1: Oleje Przemysłowe i Motoryzacyjne"
            
        grupy_mieszalnikow[g_key]["wolumen"] += wolumen
        grupy_mieszalnikow[g_key]["szarze_rok"] += dane["szarze_rok"]
        grupy_mieszalnikow[g_key]["produkty"].append((kat, dane["opakowanie"]))
        grupy_mieszalnikow[g_key]["max_cycle"] = max(grupy_mieszalnikow[g_key]["max_cycle"], rules["cycle_h"])
        grupy_mieszalnikow[g_key]["avg_density"] = rules["density"]
        grupy_mieszalnikow[g_key]["max_stir"] = max(grupy_mieszalnikow[g_key]["max_stir"], rules["stir_kw_per_m3"])

# Generowanie wyników dla Węzłów skonsolidowanych
if wspoldzielenie:
    for nazwa_wezla, dane in grupy_mieszalnikow.items():
        if dane["wolumen"] == 0:
            continue
        
        req_kg_batch = dane["wolumen"] / dane["szarze_rok"]
        req_m3 = ((req_kg_batch / dane["avg_density"]) / 1000)
        
        # Jeśli szarża jednostkowa przekracza 15m3, automatycznie zwielokrotniamy aparaty w węźle
        liczba_mieszalnikow = 1
        if req_m3 > 15.0:
            liczba_mieszalnikow = math.ceil(req_m3 / 12.0)
            req_m3 = req_m3 / liczba_mieszalnikow
            
        req_m3 = max(0.5, math.ceil(req_m3 * 2) / 2)
        batches_month = dane["szarze_rok"] / 12
        batches_week = dane["szarze_rok"] / 52
        
        # Współczynnik wykorzystania uwzględnia rozłożenie pracy na kilka fizycznych mikserów
        real_utilization = ((dane["szarze_rok"] * dane["max_cycle"]) / (AVAILABLE_HOURS_YEAR * liczba_mieszalnikow)) * 100
        mat_konstrukcyjny = "Stal nierdzewna (SS316L)" if "Wodorozcieńczalne" in nazwa_wezla else "Stal węglowa (Carbon Steel)"
        
        rekomendacje_logistyka.append({
            "Węzeł Produkcyjny": f"{nazwa_wezla} (Ilość MT: {liczba_mieszalnikow} szt.)",
            "Miesięczna produkcja [kg]": f"{int(dane['wolumen']/12):,}",
            "Pojemność 1szt. MT [m³]": f"{req_m3:.1f} m³",
            "Szarże / Miesiąc": f"{batches_month:.1f}",
            "Szarże / Tydzień": f"{batches_week:.1f}",
            "Materiał konstrukcyjny": mat_konstrukcyjny,
            "Utilization (%)": f"{real_utilization:.1f}%"
        })
        
        # Wyliczenie sumarycznej energii dla skonsolidowanego węzła
        w_heat_gj = 0
        w_cool_gj = 0
        for p, _ in dane["produkty"]:
            p_m_month = input_data[p]["wolumen"] / 12
            w_heat_gj += (p_m_month * FUCHS_PORTFOLIO[p]["cp"] * FUCHS_PORTFOLIO[p]["dT_heat"]) / (1_000_000 * 0.85)
            w_cool_gj += (p_m_month * FUCHS_PORTFOLIO[p]["cp"] * FUCHS_PORTFOLIO[p]["dT_cool"]) / (1_000_000 * 0.85)
            
        # Tworzenie fizycznych rekordów urządzeń w ciągu technologicznym
        lista_opakowan = list(set([op for _, op in dane["produkty"]]))
        opakowania_str = ", ".join(lista_opakowan)
        
        for i in range(1, liczba_mieszalnikow + 1):
            p_motor = max(0.75, math.ceil((req_m3 * dane["max_stir"]) * 2) / 2)
            id_tag = f"{dane['id']}{i:02d}"
            
            specyfikacja_ciagu_technologicznego.append({
                "Ciąg Technologiczny": f"Zestaw produkcyjny {nazwa_wezla.split(':')[-1].strip()} #{i}",
                "Zbiornik Surowca (T)": f"T-{id_tag} ({req_m3 * 1.5:.1f} m³)",
                "Mieszalnik (MT)": f"MT-{id_tag} ({req_m3:.1f} m³ / {p_motor:.1f} kW)",
                "Bufor Produktu (IT)": f"IT-{id_tag} ({req_m3 * 1.2:.1f} m³)",
                "Nalewak (FM) + Linia (FL)": f"FM-{id_tag} + FL-{id_tag} ({opakowania_str})",
                "Ciepło MT [GJ/m/szt]": f"{(w_heat_gj / liczba_mieszalnikow):.2f}",
                "Chłodzenie MT [GJ/m/szt]": f"{(w_cool_gj / liczba_mieszalnikow):.2f}",
                "Plik PDF": dane["pdf"]
            })


# --- 4. PREZENTACJA INTERFEJSU (ZAKŁADKI) ---
tab1, tab2 = st.tabs(["📊 1. Logistyka Szarż i Zbiorniki", "📐 2. Specyfikacja Ciągu Technologicznego (P&ID)"])

with tab1:
    st.header("Zarządzanie Wolumenami i Gabarytami Aparatury")
    if rekomendacje_logistyka:
        st.table(pd.DataFrame(rekomendacje_logistyka))
    else:
        st.info("Wybierz przynajmniej jedną rodzinę produktów w panelu bocznym.")

with tab2:
    st.header("🛠️ Inżynieryjna Specyfikacja Urządzeń i Bilans Energii")
    st.markdown("Układ urządzeń i podział mediów wygenerowany automatycznie na podstawie konfiguracji technologicznej:")
    
    if specyfikacja_ciagu_technologicznego:
        df_ciag = pd.DataFrame(specyfikacja_ciagu_technologicznego)
        # Ukrywamy kolumnę techniczną z nazwą pliku na potrzeby czystego widoku tabeli
        st.table(df_ciag.drop(columns=["Plik PDF"]))
        
        # --- SEKCJA ZAŁĄCZNIKÓW PDF (DOKUMENTACJA P&ID) ---
        st.markdown("---")
        st.subheader("📂 Schematy P&ID dla Zespołów Maszynowych (PDF)")
        st.markdown("Pobierz powiązane rzutowanie techniczne orurowania i oprzyrządowania P&ID dla zweryfikowanych ciągów:")
        
        cc = st.columns(len(specyfikacja_ciagu_technologicznego))
        for idx, wiersz in enumerate(specyfikacja_ciagu_technologicznego):
            with cc[idx]:
                st.markdown(f"**{wiersz['Ciąg Technologiczny']}**")
                file_path = wiersz["Plik PDF"]
                
                # Bezpieczne sprawdzanie czy plik fizycznie istnieje w repozytorium przed wywołaniem download_button
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label="📥 Pobierz P&ID (PDF)",
                            data=f,
                            file_name=file_path,
                            mime="application/pdf",
                            key=f"dl_{idx}"
                        )
                else:
                    st.warning("⚠️ Brak pliku PDF w repozytorium")
                    st.caption(f"Wgraj plik: `{file_path}` na GitHub.")
                    
        # Zbiorcze podsumowanie mediów zakładu na samym dole
        st.markdown("---")
        st.subheader("🌡️ Sumaryczny Bilans Cieplny Mieszalników Głównych (Miesięczny)")
        c1, c2 = st.columns(2)
        with c1:
            st.metric(label="🔥 ŁĄCZNE ZAPOTRZEBOWANIE NA CIEPŁO GRZEWCZE", value=f"{total_monthly_heat_GJ:.1f} GJ / miesiąc")
        with c2:
            st.metric(label="❄️ ŁĄCZNE ZAPOTRZEBOWANIE NA ZIMNO TECHNOLOGICZNE", value=f"{total_monthly_cool_GJ:.1f} GJ / miesiąc")
            
    else:
        st.info("Wybierz przynajmniej jedną rodzinę produktów w panelu bocznym.")

st.markdown("---")

# --- 5. MATRYCA SEKWENCJONOWANIA (OPERACYJNA) ---
st.header("🔄 Interaktywna Matryca Przezbrojeń (Matryca Kompatybilności)")
col1, col2 = st.columns(2)
with col1:
    prod_aktualny = st.selectbox("1. Produkt, który był produkowany (Ostatnia szarża):", list(FUCHS_PORTFOLIO.keys()), index=0)
with col2:
    prod_nastepny = st.selectbox("2. Produkt planowany do produkcji (Następna szarża):", list(FUCHS_PORTFOLIO.keys()), index=1)

type_akt = FUCHS_PORTFOLIO[prod_aktualny]["type"]
type_nast = FUCHS_PORTFOLIO[prod_nastepny]["type"]

st.markdown("### 🔔 Rekomendacja i Status Technologiczny:")
if prod_aktualny == prod_nastepny:
    st.success("🟢 **Ta sama rodzina produktowa:** Kontynuacja kampanii produkcyjnej bez konieczności mycia lub płukania instalacji.")
elif type_akt == "Wodorozcieńczalny" and type_nast != "Wodorozcieńczalny":
    st.error("🔴 **KRYTYCZNE ZAGROŻENIE SKAŻENIEM:** Przejście z produktu wodnego na olejowy! Absolutnie wymagane pełne opróżnienie, mycie detergentami i rygorystyczne suszenie instalacji przed dozowaniem oleju.")
elif type_akt != "Wodorozcieńczalny" and type_nast == "Wodorozcieńczalny":
    st.error("🔴 **KRYTYCZNE ZAGROŻENIE SKAŻENIEM:** Przejście z oleju mineralnego na produkt wodorozcieńczalny (ECOCOOL). Wymagane intensywne mycie alkaliczne układu rurociągów w celu eliminacji filmu olejowego.")
elif type_akt == "Olej ciemny/EP" and type_nast == "Olej jasny":
    st.warning("🟡 **WYMAGANE PŁUKANIE INSTALACJI (Flushing):** Wysokie ryzyko degradacji koloru i zanieczyszczenia dodatkami siarkowo-fosforowymi (EP). Wskazane płukanie gorącym olejem bazowym.")
else:
    st.info("🟡 **ZALECANE PRZEDMUCHANIE AZOTEM / LEKKIE PŁUKANIE:** Przejście między kompatybilnymi bazami olejowymi mineralnymi. Zalecany purging linii rurociągowych sprężonym powietrzem lub azotem.")
