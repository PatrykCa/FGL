import streamlit as st
import pandas as pd
import math
import os

st.set_page_config(page_title="Kreator Linii FUCHS Portfolio", layout="wide")

st.title("🏭 Kompleksowy Kreator Produkcyjny FUCHS Oil")
st.subheader("System Projektowania Procesowego z Dynamiczną Symulacją Mieszalnika MT")
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

AVAILABLE_HOURS_YEAR = 250 * 16  # 4000h rocznie (2 zmiany)
AVAILABLE_HOURS_MONTH = AVAILABLE_HOURS_YEAR / 12  # ~333.3h

# --- 2. PANEL BOCZNY ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin FUCHS")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe do planowania:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Parametry wejściowe")

input_data = {}
for kat in wybrane_kategorie:
    st.sidebar.markdown(f"### 🧪 {kat}")
    vol = st.sidebar.number_input(f"Roczna produkcja [kg]:", min_value=0, value=1200000, step=100000, key=f"vol_{kat}")
    batches = st.sidebar.number_input(f"Planowana liczba szarż/rok:", min_value=1, value=150, step=10, key=f"bat_{kat}")
    pack = st.sidebar.selectbox(
        "Główne opakowanie końcowe (FL):",
        ["1l (Detal)", "4l / 5l (Karton)", "10l / 20l (Kanister)", "60l / 200l (Beczka)", "1000l (Paletopojemnik IBC)", "Bulk (Cysterna luz)"],
        index=3,
        key=f"pack_{kat}"
    )
    input_data[kat] = {"wolumen": vol, "szarze_rok": batches, "opakowanie": pack}

st.sidebar.markdown("---")
st.sidebar.header("🏢 Strategia Alokacji")
wspoldzielenie = st.sidebar.toggle("Włącz współdzielenie zbiorników (Węzły produkcyjne)", value=True)


# --- 3. PRZYGOTOWANIE AGREGACJI DANYCH ---
total_monthly_heat_GJ = 0
total_monthly_cool_GJ = 0

grupy_mieszalnikow = {
    "Węzeł 1: Oleje Przemysłowe i Motoryzacyjne": {"id": 1, "tag": "100", "wolumen": 0, "szarze_rok": 0, "produkty": [], "max_cycle": 0, "avg_density": 0.0, "max_stir": 0.0, "pdf": "PID_Olejowy.pdf"},
    "Węzeł 2: Produkty Wodorozcieńczalne ECOCOOL/CLEAN": {"id": 2, "tag": "200", "wolumen": 0, "szarze_rok": 0, "produkty": [], "max_cycle": 0, "avg_density": 0.0, "max_stir": 0.0, "pdf": "PID_Wodny.pdf"}
}

# Wstępne zsumowanie do węzłów
for kat, dane in input_data.items():
    wolumen = dane["wolumen"]
    if wolumen == 0:
        continue
    rules = FUCHS_PORTFOLIO[kat]
    m_month = wolumen / 12
    
    total_monthly_heat_GJ += (m_month * rules["cp"] * rules["dT_heat"]) / (1_000_000 * 0.85)
    total_monthly_cool_GJ += (m_month * rules["cp"] * rules["dT_cool"]) / (1_000_000 * 0.85)

    if rules["type"] == "Wodorozcieńczalny":
        g_key = "Węzeł 2: Produkty Wodorozcieńczalne ECOCOOL/CLEAN"
    else:
        g_key = "Węzeł 1: Oleje Przemysłowe i Motoryzacyjne"
        
    grupy_mieszalnikow[g_key]["wolumen"] += wolumen
    grupy_mieszalnikow[g_key]["szarze_rok"] += dane["szarze_rok"]
    grupy_mieszalnikow[g_key]["produkty"].append((kat, dane["opakowanie"]))
    grupy_mieszalnikow[g_key]["max_cycle"] = max(grupy_mieszalnikow[g_key]["max_cycle"], rules["cycle_h"])
    grupy_mieszalnikow[g_key]["avg_density"] = rules["density"] if grupy_mieszalnikow[g_key]["avg_density"] == 0 else (grupy_mieszalnikow[g_key]["avg_density"] + rules["density"])/2
    grupy_mieszalnikow[g_key]["max_stir"] = max(grupy_mieszalnikow[g_key]["max_stir"], rules["stir_kw_per_m3"])


# --- 4. PREZENTACJA INTERFEJSU (ZAKŁADKI) ---
tab1, tab2 = st.tabs(["📊 1. Logistyka Szarż i Zbiorniki", "📐 2. Specyfikacja Ciągu Technologicznego (P&ID)"])

with tab1:
    st.header("Zarządzanie Wolumenami i Gabarytami Aparatury")
    
    # Przetwarzamy każdy aktywny Węzeł oddzielnie w formie pionowych kafelków
    for nazwa_wezla, dane in grupy_mieszalnikow.items():
        if dane["wolumen"] == 0:
            continue
            
        m_production_kg = dane["wolumen"] / 12
        avg_density = dane["avg_density"] if dane["avg_density"] > 0 else 0.88
        cycle_h = dane["max_cycle"]
        
        # OBLICZENIA SYSTEMOWE (AUTOMATYCZNE)
        sys_szarze_miesiac = dane["szarze_rok"] / 12
        sys_req_m3 = (m_production_kg / sys_szarze_miesiac) / (avg_density * 1000)
        sys_req_m3 = max(0.5, math.ceil(sys_req_m3 * 2) / 2)  # Zaokrąglenie handlowe do 0.5 m3
        sys_utilization = (sys_szarze_miesiac * cycle_h / AVAILABLE_HOURS_MONTH) * 100

        # KONTROLERY DLA MECHANIZMU DWUKIERUNKOWEGO PRZELICZANIA (USER VALUE)
        # Inicjalizacja stanów dla zmiennych użytkownika, jeśli nie istnieją
        key_v = f"u_v_{dane['id']}"
        key_s = f"u_s_{dane['id']}"
        key_u = f"u_u_{dane['id']}"
        
        if key_v not in st.session_state:
            st.session_state[key_v] = float(sys_req_m3)
            st.session_state[key_s] = float(sys_szarze_miesiac)
            st.session_state[key_u] = float(sys_utilization)

        # CALLBACKI DLA INTERAKTYWNEJ MATEMATYKI
        def update_from_volume(id_node=dane['id'], m_prod=m_production_kg, dens=avg_density, cyc=cycle_h):
            kv, ks, ku = f"u_v_{id_node}", f"u_s_{id_node}", f"u_u_{id_node}"
            v_val = st.session_state[kv]
            if v_val > 0:
                s_calc = m_prod / (v_val * dens * 1000)
                st.session_state[ks] = round(s_calc, 1)
                st.session_state[ku] = round((s_calc * cyc / AVAILABLE_HOURS_MONTH) * 100, 1)

        def update_from_batches(id_node=dane['id'], m_prod=m_production_kg, dens=avg_density, cyc=cycle_h):
            kv, ks, ku = f"u_v_{id_node}", f"u_s_{id_node}", f"u_u_{id_node}"
            s_val = st.session_state[ks]
            if s_val > 0:
                v_calc = m_prod / (s_val * dens * 1000)
                st.session_state[kv] = round(max(0.5, math.ceil(v_calc * 2) / 2), 1)
                st.session_state[ku] = round((s_val * cyc / AVAILABLE_HOURS_MONTH) * 100, 1)

        def update_from_utilization(id_node=dane['id'], m_prod=m_production_kg, dens=avg_density, cyc=cycle_h):
            kv, ks, ku = f"u_v_{id_node}", f"u_s_{id_node}", f"u_u_{id_node}"
            u_val = st.session_state[ku]
            if u_val > 0:
                s_calc = (u_val / 100) * AVAILABLE_HOURS_MONTH / cyc
                v_calc = m_prod / (s_calc * dens * 1000)
                st.session_state[ks] = round(s_calc, 1)
                st.session_state[kv] = round(max(0.5, math.ceil(v_calc * 2) / 2), 1)

        # BUDOWA WIDOKU KAFELKOWEGO (ZGODNIE ZE SZKICEM)
        st.markdown(f"### 🏭 {nazwa_wezla}")
        
        with st.container(border=True):
            # 1. Miesięczna produkcja (Wspólna na samej górze ramki)
            st.markdown(f"**1. Miesięczna produkcja linii:** `{int(m_production_kg):,}` kg/miesiąc")
            st.markdown("---")
            
            col_sys, col_user = st.columns(2)
            
            with col_sys:
                st.markdown("#### 📐 Rekomendacja Algorytmu")
                st.metric(label="2. Rekomendowana pojemność MT", value=f"{sys_req_m3:.1f} m³")
                st.metric(label="3. Szarże / miesiąc (Sys)", value=f"{sys_szarze_miesiac:.1f}")
                st.metric(label="4. Obłożenie (Utilization % Sys)", value=f"{sys_utilization:.1f} %")
                
            with col_user:
                st.markdown("#### ✍️ Symulacja Użytkownika (Pola edytowalne)")
                
                # 5. Rekomendowana pojemność użytkownika
                st.number_input(
                    "5. Pojemność zbiornika użytkownika [m³]:", 
                    min_value=0.5, step=0.5, 
                    key=key_v, 
                    on_change=update_from_volume
                )
                
                # 6. Szarże / miesiąc użytkownika
                st.number_input(
                    "6. Szarże / miesiąc użytkownika:", 
                    min_value=0.1, step=1.0, 
                    key=key_s, 
                    on_change=update_from_batches
                )
                
                # 7. Obłożenie (utilization %) użytkownika
                st.number_input(
                    "7. Maksymalne obłożenie [%]:", 
                    min_value=0.1, max_value=100.0, step=5.0, 
                    key=key_u, 
                    on_change=update_from_utilization
                )
        st.markdown("<br>", unsafe_allowed_html=True)

with tab2:
    st.header("🛠️ Specyfikacja Urządzeń i Parametry Procesowe")
    st.info("Ta sekcja generuje kompletny sprzęt w oparciu o zatwierdzone w pierwszej zakładce parametry.")
    
    # Wyświetlamy uproszczony ciąg maszyn na podstawie wyboru symulacji
    specyfikacja_final = []
    for nazwa_wezla, dane in grupy_mieszalnikow.items():
        if dane["wolumen"] == 0:
            continue
        key_v = f"u_v_{dane['id']}"
        v_user = st.session_state.get(key_v, 5.0)
        p_motor = max(0.75, math.ceil((v_user * dane["max_stir"]) * 2) / 2)
        
        lista_opakowan = list(set([op for _, op in dane["produkty"]]))
        opakowania_str = ", ".join(lista_opakowan)
        id_tag = f"{dane['id']}01"
        
        specyfikacja_final.append({
            "Węzeł": nazwa_wezla.split(':')[-1].strip(),
            "Zbiornik Surowca (T)": f"T-{id_tag} ({v_user * 1.5:.1f} m³)",
            "Mieszalnik (MT)": f"MT-{id_tag} ({v_user:.1f} m³ / {p_motor:.1f} kW)",
            "Bufor Produktu (IT)": f"IT-{id_tag} ({v_user * 1.2:.1f} m³)",
            "Nalewak (FM) + Linia (FL)": f"FM-{id_tag} + FL-{id_tag} ({opakowania_str})",
            "Plik P&ID": dane["pdf"]
        })
        
    if specyfikacja_final:
        df_final = pd.DataFrame(specyfikacja_final)
        st.table(df_final.drop(columns=["Plik P&ID"]))
        
        st.markdown("---")
        st.subheader("📂 Dedykowane Schematy Technologiczne P&ID (Rekomendowane PDF)")
        
        cc = st.columns(len(specyfikacja_final))
        for idx, row in enumerate(specyfikacja_final):
            with cc[idx]:
                st.markdown(f"**Ciąg: {row['Węzeł']}**")
                file_path = row["Plik P&ID"]
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        st.download_button("📥 Pobierz P&ID (PDF)", data=f, file_name=file_path, mime="application/pdf", key=f"f_dl_{idx}")
                else:
                    st.warning(f"⚠️ Wgraj `{file_path}` na GitHub.")
