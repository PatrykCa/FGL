import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Kreator Linii FUCHS Portfolio", layout="wide")

st.title("🏭 Kompleksowy Kreator Produkcyjny FUCHS Oil")
st.subheader("Zarządzanie Wolumenami i Gabarytami Aparatury (Układ Tabelaryczny)")
st.markdown("---")

# --- 1. BAZA DANYCH RODZIN PRODUKTOWYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Industrial: Hydraulic Oils (RENOLIN)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "220°C", "viscosity": "46 mm²/s (40°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Industrial: Gear & Turbine Oils (RENOLIN)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.89, "cycle_h": 5, "cp": 1.9, 
        "flash_point": "240°C", "viscosity": "220 mm²/s (40°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Industrial: Slideway & Machine Oils (RENAX)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "210°C", "viscosity": "68 mm²/s (40°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Automotive: Engine Oils (TITAN)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 5, "cp": 2.1, 
        "flash_point": "230°C", "viscosity": "11.5 mm²/s (100°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Automotive: Gear & Transmission Oils (TITAN)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.88, "cycle_h": 5, "cp": 2.0, 
        "flash_point": "210°C", "viscosity": "14.0 mm²/s (100°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Metal Processing: Water-miscible (ECOCOOL)": {
        "material": "Stal nierdzewna (SS316L)", "density": 0.99, "cycle_h": 6, "cp": 3.8, 
        "flash_point": "Brak (Produkt wodny)", "viscosity": "60 mm²/s (40°C)", "frost_sensitivity": "TAK", "pdf": "PID_Wodny.pdf"
    },
    "Metal Processing: Non-water-miscible (ECOCUT)": {
        "material": "Stal węglowa (Carbon Steel)", "density": 0.87, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "190°C", "viscosity": "22 mm²/s (40°C)", "frost_sensitivity": "Nie", "pdf": "PID_Olejowy.pdf"
    },
    "Metal Processing: Cleaners (RENOCLEAN)": {
        "material": "Stal nierdzewna (SS304/316L)", "density": 1.01, "cycle_h": 4, "cp": 3.9, 
        "flash_point": "Brak", "viscosity": "5 mm²/s (40°C)", "frost_sensitivity": "TAK", "pdf": "PID_Wodny.pdf"
    }
}

AVAILABLE_HOURS_MONTH = (250 * 16) / 12  # ~333.33 h/miesiąc

# --- 2. PANEL BOCZNY ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin FUCHS")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe:",
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
        "Opakowanie końcowe (FL):",
        ["1l (Detal)", "4l / 5l (Karton)", "10l / 20l (Kanister)", "60l / 200l (Beczka)", "1000l (Paletopojemnik IBC)", "Bulk (Cysterna luz)"],
        index=3,
        key=f"pack_{kat}"
    )
    input_data[kat] = {"wolumen": vol, "opakowanie": pack}

# Inicjalizacja stanów
if "confirmed_setup" not in st.session_state:
    st.session_state.confirmed_setup = {}

tab1, tab2 = st.tabs(["📊 1. Logistyka Szarż i Zbiorniki", "📐 2. Specyfikacja Ciągu Technologicznego (P&ID)"])

with tab1:
    st.header("Zestawienie Wolumenów i Parametrów Szarż")
    st.caption("Rekomendacja systemu wyliczana jest automatycznie przy założeniu 75% poziomu utylizacji (obłożenia) aparatury.")
    
    # Tworzymy dynamiczny formularz-tabelę, gdzie każdy produkt to wiersz, ale z polami edytowalnymi obok siebie
    for kat in wybrane_kategorie:
        if input_data[kat]["wolumen"] == 0:
            continue
            
        m_production_kg = input_data[kat]["wolumen"] / 12
        dens = FUCHS_PORTFOLIO[kat]["density"]
        cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
        
        # OBLICZENIA SYSTEMOWE (REKOMENDACJA NA BAZIE 75%)
        eff_hours = AVAILABLE_HOURS_MONTH * 0.75  # 250 godzin
        sys_szarze_miesiac = round(eff_hours / cyc, 1)
        sys_req_m3 = (m_production_kg / sys_szarze_miesiac) / (dens * 1000)
        sys_req_m3 = max(0.5, math.ceil(sys_req_m3 * 2) / 2)
        sys_utilization = 75.0
        
        kv, ks, ku = f"v_{kat}", f"s_{kat}", f"u_{kat}"
        if kv not in st.session_state:
            st.session_state[kv] = float(sys_req_m3)
            st.session_state[ks] = float(sys_szarze_miesiac)
            st.session_state[ku] = float(sys_utilization)
            
        st.markdown(f"#### 🧪 Produkt: {kat}")
        
        # Pojedynczy wiersz jako horyzontalna tabela za pomocą kolumn Streamlit
        with st.container(border=True):
            # 1. Nagłówek wiersza z wielkością produkcji
            st.markdown(f"**1. Miesięczna produkcja:** `{int(m_production_kg):,}` kg/miesiąc | **Opakowanie:** {input_data[kat]['opakowanie']}")
            
            c_label, c_sys, c_user, c_action = st.columns([1, 2, 3, 2])
            
            with c_label:
                st.markdown("<br><p style='color:gray; font-size:13px;'>2. Pojemność MT<br><br>3. Szarże/miesiąc<br><br>4. Utylizacja %</p>", unsafe_allowed_html=True)
                
            with c_sys:
                st.markdown("**📐 Rekomendacja (75%)**")
                st.markdown(f"`{sys_req_m3:.1f} m³` — Pojemność MT")
                st.markdown(f"`{sys_szarze_miesiac:.1f}` — Szarże/miesiąc")
                st.markdown(f"`{sys_utilization:.1f} %` — Utylizacja")
                
            with c_user:
                st.markdown("**✍️ Symulacja Użytkownika**")
                with st.form(key=f"form_row_{kat}"):
                    v_in = st.number_input("5. Pojemność [m³]:", value=st.session_state[kv], step=0.5, key=f"vin_{kat}")
                    s_in = st.number_input("6. Szarże / miesiąc:", value=st.session_state[ks], step=1.0, key=f"sin_{kat}")
                    u_in = st.number_input("7. Utylizacja [%]:", value=st.session_state[ku], step=5.0, key=f"uin_{kat}")
                    
                    calc_btn = st.form_submit_button("🔄 Przelicz wiersz")
                    if calc_btn:
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
                        
            with c_action:
                st.markdown("**🔒 Decyzja projektowa**")
                choice = st.radio(
                    "Wariant dla linii:",
                    ["Rekomendowany", "Użytkownika"],
                    key=f"choice_{kat}",
                    label_visibility="collapsed"
                )
                if st.button("Zatwierdź produkt", key=f"save_{kat}"):
                    if choice == "Rekomendowany":
                        st.session_state.confirmed_setup[kat] = {
                            "capacity": sys_req_m3, "batches": sys_szarze_miesiac, "utilization": sys_utilization
                        }
                    else:
                        st.session_state.confirmed_setup[kat] = {
                            "capacity": st.session_state[kv], "batches": st.session_state[ks], "utilization": st.session_state[ku]
                        }
                    st.toast(f"✔️ Zapisano wariant: {choice} dla {kat.split(':')[-1]}")
                    
        st.markdown("<hr style='margin:10px 0px;'>", unsafe_allowed_html=True)

with tab2:
    st.header("📐 Inżynieryjna Specyfikacja Ciągu Technologicznego")
    
    if not st.session_state.confirmed_setup:
        st.info("ℹ️ Aby wygenerować specyfikację techniczną, zatwierdź opcje dla wybranych produktów w Zakładce 1.")
    else:
        rows = []
        idx = 101
        for kat, dane in st.session_state.confirmed_setup.items():
            rules = FUCHS_PORTFOLIO[kat]
            v_final = dane["capacity"]
            
            rows.append({
                "Tag Mieszalnika": f"MT-{idx}",
                "Rodzina Produktowa": kat.split(":")[-1].strip(),
                "Pojemność [m³]": f"{v_final:.1f} m³",
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
        
        st.markdown("#### 🌡️ Parametry Procesowe i Bilans Cieplny")
        final_table_data = []
        for index, row in df_ins.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 3, 3])
                with c1:
                    st.markdown(f"**{row['Tag Mieszalnika']}**<br><small>{row['Rodzina Produktowa']}</small>", unsafe_allowed_html=True)
                with c2:
                    dt_heat = st.number_input(f"ΔT grzania [°C] ({row['Tag Mieszalnika']}):", value=40, step=5, key=f"dth_{row['Tag Mieszalnika']}")
                    total_heat_gj = (row["Masa Szarży [kg]"] * row["cp"] * dt_heat * row["Szarże / miesiąc"]) / (1_000_000 * 0.85)
                with c3:
                    dt_cool = st.number_input(f"ΔT chłodzenia [°C] ({row['Tag Mieszalnika']}):", value=30, step=5, key=f"dtc_{row['Tag Mieszalnika']}")
                    total_cool_gj = (row["Masa Szarży [kg]"] * row["cp"] * dt_cool * row["Szarże / miesiąc"]) / (1_000_000 * 0.85)
                
                final_table_data.append({
                    "Tag": row["Tag Mieszalnika"],
                    "Produkt": row["Rodzina Produktowa"],
                    "Pojemność": row["Pojemność [m³]"],
                    "Stal": row["Materiał (Stal)"],
                    "Ciepło grzania [GJ/m]": f"{total_heat_gj:.2f} GJ",
                    "Ciepło chłodzenia [GJ/m]": f"{total_cool_gj:.2f} GJ",
                    "Flash Point": row["Flash Point"],
                    "Lepkość": row["Viscosity"],
                    "Wrażliwość na mróz": row["Frost Sensitivity"]
                })
        
        st.markdown("---")
        st.markdown("### 📋 Zbiorcza Tabela Technologiczna")
        st.table(pd.DataFrame(final_table_data))
