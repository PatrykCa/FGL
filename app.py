import streamlit as st
import pandas as pd
import math
import os

st.set_page_config(page_title="Kreator Linii FUCHS Portfolio", layout="wide")

st.title("🏭 Kompleksowy Kreator Produkcyjny FUCHS Oil")
st.subheader("System Projektowania Procesowego z Blokadą Decyzji i Kartami Produktów")
st.markdown("---")

# --- 1. ROZBUDOWANA BAZA DANYCH RODZIN PRODUKTOWYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Industrial: Hydraulic Oils (RENOLIN)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "type": "Olej jasny", "cp": 2.0, 
        "flash_point": "220°C", "viscosity": "46 mm²/s (40°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Industrial: Gear & Turbine Oils (RENOLIN)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.89, "cycle_h": 5, "type": "Olej ciemny/EP", "cp": 1.9, 
        "flash_point": "240°C", "viscosity": "220 mm²/s (40°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Industrial: Slideway & Machine Oils (RENAX)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "type": "Olej jasny", "cp": 2.0, 
        "flash_point": "210°C", "viscosity": "68 mm²/s (40°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Automotive: Engine Oils (TITAN)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 5, "type": "Olej silnikowy", "cp": 2.1, 
        "flash_point": "230°C", "viscosity": "11.5 mm²/s (100°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Automotive: Gear & Transmission Oils (TITAN)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 5, "type": "Olej przekładniowy", "cp": 2.0, 
        "flash_point": "210°C", "viscosity": "14.0 mm²/s (100°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Metal Processing: Water-miscible (ECOCOOL)": {
        "material": "Stal nierdzewna (SS316L)", "density": 0.99, "cycle_h": 6, "type": "Wodorozcieńczalny", "cp": 3.8, 
        "flash_point": "Brak (Produkt wodny)", "viscosity": "60 mm²/s (40°C koncentrat)", "frost_sensitivity": "TAK (Chronić przed zamarzaniem)", "pdf": "PID_Wodny.pdf"
    },
    "Metal Processing: Non-water-miscible (ECOCUT)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 4, "type": "Olej obróbczy", "cp": 2.0, 
        "flash_point": "190°C", "viscosity": "22 mm²/s (40°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Metal Processing: Cleaners (RENOCLEAN)": {
        "material": "Stal nierdzewna (SS304/316L)", "density": 1.01, "cycle_h": 4, "type": "Wodorozcieńczalny", "cp": 3.9, 
        "flash_point": "Brak", "viscosity": "5 mm²/s (40°C)", "frost_sensitivity": "TAK", "pdf": "PID_Wodny.pdf"
    }
}

AVAILABLE_HOURS_MONTH = (250 * 16) / 12  # ~333.33 h/miesiąc

# --- 2. PANEL BOCZNY ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin FUCHS")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe do planowania:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Dane wejściowe")
input_data = {}
for kat in wybrane_kategorie:
    st.sidebar.markdown(f"### 🧪 {kat}")
    vol = st.sidebar.number_input(f"Roczna produkcja [kg]:", min_value=0, value=1200000, step=100000, key=f"vol_{kat}")
    pack = st.sidebar.selectbox(
        "Główne opakowanie końcowe (FL):",
        ["1l (Detal)", "4l / 5l (Karton)", "10l / 20l (Kanister)", "60l / 200l (Beczka)", "1000l (Paletopojemnik IBC)", "Bulk (Cysterna luz)"],
        index=3,
        key=f"pack_{kat}"
    )
    input_data[kat] = {"wolumen": vol, "opakowanie": pack}

# --- 3. INICJALIZACJA PAMIĘCI STANÓW (SESSION STATE) DLA DWUKIERUNKOWOŚCI I ZATWIERDZEŃ ---
if "confirmed_setup" not in st.session_state:
    st.session_state.confirmed_setup = {}

# --- 4. INTERFEJS ZAKŁADEK ---
tab1, tab2 = st.tabs(["📊 1. Logistyka Szarż i Zbiorniki", "📐 2. Specyfikacja Ciągu Technologicznego (P&ID)"])

with tab1:
    st.header("Zarządzanie Wolumenami i Gabarytami Aparatury")
    st.markdown("Algorytm generuje rekomendację na bazie docelowego **75% obłożenia (utylizacji)**. W prawej kolumnie możesz przeprowadzić własną symulację.")
    
    for kat in wybrane_kategorie:
        if input_data[kat]["wolumen"] == 0:
            continue
            
        m_production_kg = input_data[kat]["wolumen"] / 12
        dens = FUCHS_PORTFOLIO[kat]["density"]
        cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
        
        # OBLICZENIA REKOMENDOWANE (LEWA STRONA) - BAZA 75% UTYLIZACJI
        eff_hours = AVAILABLE_HOURS_MONTH * 0.75  # 250 godzin
        sys_szarze_miesiac = round(eff_hours / cyc, 1)
        sys_req_m3 = (m_production_kg / sys_szarze_miesiac) / (dens * 1000)
        sys_req_m3 = max(0.5, math.ceil(sys_req_m3 * 2) / 2)
        sys_utilization = 75.0
        
        # KLUCZE ZMIENNYCH DLA DANEJ KATEGORII
        kv, ks, ku = f"v_{kat}", f"s_{kat}", f"u_{kat}"
        
        if kv not in st.session_state:
            st.session_state[kv] = float(sys_req_m3)
            st.session_state[ks] = float(sys_szarze_miesiac)
            st.session_state[ku] = float(sys_utilization)
            
        st.markdown(f"### 🏭 Linia: {kat}")
        
        with st.container(border=True):
            # 1. Wielkość produkcji na samej górze kafelka
            st.markdown(f"**1. Wymagana produkcja miesięczna (Cel):** `{int(m_production_kg):,}` kg / miesiąc")
            st.markdown("---")
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                st.markdown("#### 📐 Output Rekomendowany (System)")
                st.metric(label="2. Rekomendowana pojemność MT", value=f"{sys_req_m3:.1f} m³")
                st.metric(label="3. Szarże / miesiąc", value=f"{sys_szarze_miesiac:.1f}")
                st.metric(label="4. Poziom utylizacji", value=f"{sys_utilization:.1f} %")
                
            with col_right:
                st.markdown("#### ✍️ Input Użytkownika (Symulacja)")
                
                with st.form(key=f"form_{kat}"):
                    v_in = st.number_input("5. Pojemność zbiornika użytkownika [m³]:", value=st.session_state[kv], step=0.5, key=f"vin_{kat}")
                    s_in = st.number_input("6. Szarże / miesiąc użytkownika:", value=st.session_state[ks], step=1.0, key=f"sin_{kat}")
                    u_in = st.number_input("7. Poziom utylizacji użytkownika [%]:", value=st.session_state[ku], step=5.0, key=f"uin_{kat}")
                    
                    calc_btn = st.form_submit_button("🔄 Przelicz powiązane parametry")
                    
                    if calc_btn:
                        # Logika dwukierunkowości - sprawdzamy co drgnęło
                        if v_in != st.session_state[kv]:
                            st.session_state[kv] = v_in
                            st.session_state[ks] = round(m_production_kg / (v_in * dens * 1000), 1)
                            st.session_state[ku] = round((st.session_state[ks] * cyc / AVAILABLE_HOURS_MONTH) * 100, 1)
                        elif s_in != st.session_state[ks]:
                            st.session_state[ks] = s_in
                            st.session_state[kv] = round(max(0.5, math.ceil((m_production_kg / (s_in * dens * 1000)) * 2) / 2), 1)
                            st.session_state[ku] = round((s_in * cyc / AVAILABLE_HOURS_MONTH) * 100, 1)
                        elif u_in != st.session_state[ku]:
                            st.session_state[ku] = u_in
                            s_calc = (u_in / 100) * AVAILABLE_HOURS_MONTH / cyc
                            st.session_state[ks] = round(s_calc, 1)
                            st.session_state[kv] = round(max(0.5, math.ceil((m_production_kg / (s_calc * dens * 1000)) * 2) / 2), 1)
                        st.rerun()

            # STOPKA KAFELKA: Podsumowanie i jawne zamrożenie konfiguracji węzła
            st.markdown("---")
            choice = st.radio(
                "Wybierz wariant konstrukcyjny do wysłania do projektu technicznego:",
                ["Opcja Rekomendowana (System)", "Opcja Zsymulowana (Użytkownik)"],
                key=f"choice_{kat}"
            )
            
            if st.button("🔒 Zatwierdź i wyślij konfigurację linii", key=f"save_{kat}"):
                if choice == "Opcja Rekomendowana (System)":
                    st.session_state.confirmed_setup[kat] = {
                        "capacity": sys_req_m3, "batches": sys_szarze_miesiac, "utilization": sys_utilization
                    }
                else:
                    st.session_state.confirmed_setup[kat] = {
                        "capacity": st.session_state[kv], "batches": st.session_state[ks], "utilization": st.session_state[ku]
                    }
                st.success(f"✔️ Pomyślnie zamrożono dane dla {kat}! Przejdź do Zakładki 2.")
        st.markdown("<br>", unsafe_allowed_html=True)

with tab2:
    st.header("📐 Inżynieryjna Specyfikacja Ciągu Technologicznego")
    
    if not st.session_state.confirmed_setup:
        st.info("ℹ️ Aby wyświetlić listę aparatów i bilans mediów, musisz najpierw zatwierdzić przynajmniej jedną linię w Zakładce 1 za pomocą przycisku '🔒 Zatwierdź i wyślij'.")
    else:
        st.markdown("### 📋 Zweryfikowana Lista Mieszalników (MT)")
        
        rows = []
        idx = 101
        for kat, dane in st.session_state.confirmed_setup.items():
            rules = FUCHS_PORTFOLIO[kat]
            v_final = dane["capacity"]
            
            # Tworzenie unikalnego wiersza z tagiem inżynieryjnym
            rows.append({
                "Tag Mieszalnika": f"MT-{idx}",
                "Rodzina Produktowa": kat.split(":")[-1].strip(),
                "Zatwierdzona Pojemność [m³]": f"{v_final:.1f} m³",
                "Szarże / miesiąc": dane["batches"],
                "Obłożenie (%)": f"{dane['utilization']:.1f}%",
                "Materiał (Stal)": rules["material"],
                "Flash Point": rules["flash_point"],
                "Viscosity": rules["viscosity"],
                "Frost Sensitivity": rules["frost_sensitivity"],
                "Masa Szarży [kg]": v_final * rules["density"] * 1000,
                "cp": rules["cp"],
                "pdf": rules["pdf"]
            })
            idx += 1
            
        df_ins = pd.DataFrame(rows)
        
        # FORMULARZ I KOLUMNY INTERAKTYWNE DLA DELTA T
        st.markdown("#### 🌡️ Bilans Energii Cieplnej i Chłodniczej")
        st.caption("Wpisz oczekiwane wartości różnic temperatur (Delta T) osobno dla każdego mieszalnika, aby wyliczyć zapotrzebowanie na GJ:")
        
        final_table_data = []
        for index, row in df_ins.iterrows():
            with st.container(border=True):
                st.markdown(f"**Mieszalnik {row['Tag Mieszalnika']}** ({row['Rodzina Produktowa']})")
                c_h1, c_h2 = st.columns(2)
                
                with c_h1:
                    dt_heat = st.number_input(f"Różnica temperatur grzania ΔT_heat [°C] dla {row['Tag Mieszalnika']}:", value=40, step=5, key=f"dth_{row['Tag Mieszalnika']}")
                    # Q = m * cp * dT / (1 000 000 * sprawność 0.85) -> Wynik w GJ na szarżę przemnożony przez liczbę szarż w miesiącu
                    total_heat_gj = (row["Masa Szarży [kg]"] * row["cp"] * dt_heat * row["Szarże / miesiąc"]) / (1_000_000 * 0.85)
                    
                with c_h2:
                    dt_cool = st.number_input(f"Różnica temperatur chłodzenia ΔT_cool [°C] dla {row['Tag Mieszalnika']}:", value=30, step=5, key=f"dtc_{row['Tag Mieszalnika']}")
                    total_cool_gj = (row["Masa Szarży [kg]"] * row["cp"] * dt_cool * row["Szarże / miesiąc"]) / (1_000_000 * 0.85)
                
                final_table_data.append({
                    "Tag": row["Tag Mieszalnika"],
                    "Produkt": row["Rodzina Produktowa"],
                    "Pojemność": row["Zatwierdzona Pojemność [m³]"],
                    "Stal": row["Materiał (Stal)"],
                    "ΔT Grzania [°C]": f"+{dt_heat} °C",
                    "Ciepło potrzebne [GJ/m]": f"{total_heat_gj:.2f} GJ",
                    "ΔT Chłodzenia [°C]": f"-{dt_cool} °C",
                    "Ciepło do odebrania [GJ/m]": f"{total_cool_gj:.2f} GJ",
                    "Flash Point": row["Flash Point"],
                    "Lepkość": row["Viscosity"],
                    "Wrażliwość na mróz": row["Frost Sensitivity"],
                    "pdf": row["pdf"]
                })
        
        st.markdown("---")
        st.markdown("### 📋 Zbiorcza Tabela Inżynieryjna")
        df_engineering = pd.DataFrame(final_table_data)
        st.table(df_engineering.drop(columns=["pdf"]))
        
        # SEKCJA GENEROWANIA DOKUMENTACJI PDF
        st.markdown("---")
        st.subheader("📂 Generowanie i Pobieranie Dokumentacji P&ID")
        
        cc = st.columns(len(final_table_data))
        for idx, item in enumerate(final_table_data):
            with cc[idx]:
                st.markdown(f"**Aparat {item['Tag']}**")
                file_path = item["pdf"]
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        st.download_button(f"📥 Pobierz P&ID ({item['Tag']})", data=f, file_name=file_path, mime="application/pdf", key=f"f_dl_{idx}")
                else:
                    st.warning(f"⚠️ Brak `{file_path}`")
                    st.caption("Umieść plik w katalogu na GitHub.")
