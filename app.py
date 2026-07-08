import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Wymiarowanie Fabryki na Podstawie Obłożenia Węzłów (Cel: 75% Utylizacji)")
st.markdown("---")

# --- 1. BAZA DANYCH PROCESOWYCH I FIZYKOCHEMICZNYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Industrial: Hydraulic Oils (RENOLIN)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "visc_kin": 46.0, "flash_point": "220°C", "frost_sensitivity": "Nie"
    },
    "Industrial: Gear & Turbine Oils (RENOLIN)": {
        "material": "Stal zwykła", "density": 0.89, "cycle_h": 5, "cp": 1.9, 
        "visc_kin": 220.0, "flash_point": "240°C", "frost_sensitivity": "Nie"
    },
    "Industrial: Slideway & Machine Oils (RENAX)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "210°C", "visc_kin": 68.0, "frost_sensitivity": "Nie"
    },
    "Automotive: Engine Oils (TITAN)": {
        "material": "Stal zwykła", "density": 0.87, "cycle_h": 5, "cp": 2.1, 
        "visc_kin": 95.0, "flash_point": "230°C", "frost_sensitivity": "Nie"
    },
    "Automotive: Gear & Transmission Oils (TITAN)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 5, "cp": 2.0, 
        "visc_kin": 140.0, "flash_point": "210°C", "frost_sensitivity": "Nie"
    },
    "Metal Processing: Water-miscible (ECOCOOL)": {
        "material": "Stal nierdzewna", "density": 0.99, "cycle_h": 6, "cp": 3.8, 
        "visc_kin": 60.0, "flash_point": "Brak", "frost_sensitivity": "TAK"
    },
    "Metal Processing: Non-water-miscible (ECOCUT)": {
        "material": "Stal zwykła", "density": 0.87, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "190°C", "visc_kin": 22.0, "frost_sensitivity": "Nie"
    },
    "Metal Processing: Cleaners (RENOCLEAN)": {
        "material": "Stal nierdzewna", "density": 1.01, "cycle_h": 4, "cp": 3.9, 
        "visc_kin": 5.0, "flash_point": "Brak", "frost_sensitivity": "TAK"
    }
}

PACK_CONFIGS = {
    "1l (Detal)": {"size_l": 1.0, "per_pallet": 480},
    "4l (Karton)": {"size_l": 4.0, "per_pallet": 120},
    "5l (Karton)": {"size_l": 5.0, "per_pallet": 96},
    "10l (Kanister)": {"size_l": 10.0, "per_pallet": 40},
    "20l (Kanister)": {"size_l": 20.0, "per_pallet": 24},
    "60l (Beczka)": {"size_l": 60.0, "per_pallet": 9},
    "200l (Beczka)": {"size_l": 200.0, "per_pallet": 4},
    "1000l (IBC)": {"size_l": 1000.0, "per_pallet": 1}
}

AVAILABLE_HOURS_MONTH = (250 * 16) / 12  # ~333.33 h/miesiąc (praca dwuzmianowa)
TARGET_UTILIZATION = 0.75
EFFECTIVE_HOURS_MONTH = AVAILABLE_HOURS_MONTH * TARGET_UTILIZATION  # ~250h

# --- PANEL BOCZNY (INPUT) ---
st.sidebar.header("📋 KROK 1: Wybór Produktów")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Parametry wejściowe")
input_data = {}

for kat in wybrane_kategorie:
    st.sidebar.markdown(f"### 🧪 {kat.split(':')[-1].strip()}")
    vol = st.sidebar.number_input("Roczna produkcja [kg]:", min_value=0, value=1200000, step=100000, key=f"vol_{kat}")
    packs = st.sidebar.multiselect(
        "Opakowania końcowe:",
        list(PACK_CONFIGS.keys()) + ["Bulk (Cysterna luz)"],
        default=["200l (Beczka)", "1000l (IBC)"],
        key=f"packs_{kat}"
    )
    input_data[kat] = {"wolumen": vol, "opakowania": packs}

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

# --- PODZIAŁ NA TRZY ZAKŁADKI ---
tab1, tab2, tab3 = st.tabs([
    "📊 1. Logistyka Szarż i Utylizacja Węzłów", 
    "📐 2. Specyfikacja Urządzeń i Hydrodynamika", 
    "📦 3. Magazyn Wyrobów Gotowych i Palety"
])

# ==========================================
# ZAKŁADKA 1: STRONA GŁÓWNA (ZGODNA Z WYTYCZNYMI)
# ==========================================
with tab1:
    st.header("Zestawienie Wolumenów i Parametrów Procesowych Fabryki")
    
    total_hours_carbon = 0.0
    total_hours_ss = 0.0
    active_rows = []
    
    # Pierwszy przebieg: obliczenie wymaganych godzin, by poznać łączną liczbę maszyn i obłożenie węzła
    for kat in wybrane_kategorie:
        v_annual = input_data[kat]["wolumen"]
        if v_annual == 0:
            continue
        m_prod_kg = v_annual / 12
        dens = FUCHS_PORTFOLIO[kat]["density"]
        cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
        mat = FUCHS_PORTFOLIO[kat]["material"]
        
        batch_mass_kg = 10.0 * dens * 1000.0
        needed_batches = m_prod_kg / batch_mass_kg
        needed_hours = needed_batches * cyc
        
        if mat == "Stal zwykła":
            total_hours_carbon += needed_hours
        else:
            total_hours_ss += needed_hours

    # Wyznaczenie liczby mieszalników i ostatecznego obłożenia węzłów
    mixers_carbon = math.ceil(total_hours_carbon / EFFECTIVE_HOURS_MONTH) if total_hours_carbon > 0 else 0
    mixers_ss = math.ceil(total_hours_ss / EFFECTIVE_HOURS_MONTH) if total_hours_ss > 0 else 0
    
    util_carbon_val = (total_hours_carbon / (mixers_carbon * AVAILABLE_HOURS_MONTH)) * 100 if mixers_carbon > 0 else 0.0
    util_ss_val = (total_hours_ss / (mixers_ss * AVAILABLE_HOURS_MONTH)) * 100 if mixers_ss > 0 else 0.0

    # Drugi przebieg: budowanie tabeli z precyzyjnymi danymi technicznymi i przypisanym obłożeniem węzła
    for kat in wybrane_kategorie:
        v_annual = input_data[kat]["wolumen"]
        if v_annual == 0:
            continue
            
        m_prod_kg = v_annual / 12
        dens = FUCHS_PORTFOLIO[kat]["density"]
        cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
        mat = FUCHS_PORTFOLIO[kat]["material"]
        
        v_mixer_m3 = 10.0
        batch_mass_kg = v_mixer_m3 * dens * 1000.0
        needed_batches = m_prod_kg / batch_mass_kg
        
        # Przypisanie obłożenia odpowiedniego węzła
        node_utilization = f"{util_carbon_val:.1f}%" if mat == "Stal zwykła" else f"{util_ss_val:.1f}%"
        
        active_rows.append({
            "Produkt (Rodzina FUCHS)": kat.split(":")[-1].strip(),
            "Rodzaj materiału": "Stal zwykła (Olejowy)" if mat == "Stal zwykła" else "Stal nierdzewna (Wodny)",
            "Wielkość produkcyjna [kg/miesiąc]": int(m_prod_kg),
            "Liczba szarż [szt/miesiąc]": round(needed_batches, 1),
            "Pojemność mieszalnika [m³]": v_mixer_m3,
            "Czas produkcji - mieszania [h/szarżę]": cyc,
            "Obłożenie węzła (Utilization %)": node_utilization
        })
        
    if active_rows:
        st.dataframe(pd.DataFrame(active_rows), hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Podsumowanie Struktury i Rekomendacja Liczby Maszyn")
        
        c_rec1, c_rec2 = st.columns(2)
        with c_rec1:
            st.info("### 🏢 Węzeł Olejowy (Stal Zwykła)")
            st.metric(label="Rekomendowana liczba mieszalników 10m³", value=f"{mixers_carbon} szt.")
            st.write(f"Globalne obłożenie węzła: **{util_carbon_val:.1f}%**")
                
        with c_rec2:
            st.success("### 🧪 Węzeł Wodny (Stal Nierdzewna)")
            st.metric(label="Rekomendowana liczba mieszalników 10m³", value=f"{mixers_ss} szt.")
            st.write(f"Globalne obłożenie węzła: **{util_ss_val:.1f}%**")
                
        st.markdown("---")
        if st.button("🔒 ZATWIERDŹ STRUKTURĘ WĘZŁÓW I PROJEKTUJ APARATURĘ"):
            confirmed_list = []
            idx = 101
            for _ in range(mixers_carbon):
                confirmed_list.append({"tag": f"MT-{idx}", "material": "Stal zwykła", "capacity_m3": 10.0, "type_node": "Olejowy"})
                idx += 1
            idx = 201
            for _ in range(mixers_ss):
                confirmed_list.append({"tag": f"MT-{idx}", "material": "Stal nierdzewna", "capacity_m3": 10.0, "type_node": "Wodny"})
                idx += 1
            st.session_state.confirmed_mixers = confirmed_list
            st.success(f"Zatwierdzono! Wygenerowano aparatury: {len(confirmed_list)} szt. Przejdź do Zakładki 2.")
    else:
        st.warning("Wprowadź niezerowe wolumeny produkcji w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA URZĄDZEŃ
# ==========================================
with tab2:
    st.header("Specyfikacja Hydrodynamiczna i Termiczna Mieszalników")
    
    if not st.session_state.confirmed_mixers:
        st.info("ℹ️ Zatwierdź rekomendację w Zakładce 1, aby wygenerować profile aparatury.")
    else:
        oil_products = [kat for kat in wybrane_kategorie if FUCHS_PORTFOLIO[kat]["material"] == "Stal zwykła" and input_data[kat]["wolumen"] > 0]
        water_products = [kat for kat in wybrane_kategorie if FUCHS_PORTFOLIO[kat]["material"] == "Stal nierdzewna" and input_data[kat]["wolumen"] > 0]
        
        engineering_data = []
        
        for mixer in st.session_state.confirmed_mixers:
            st.markdown(f"### ⚙️ Reaktor Procesowy: **{mixer['tag']}**")
            
            if mixer["type_node"] == "Olejowy" and oil_products:
                ref_product = oil_products[0]
            elif mixer["type_node"] == "Wodny" and water_products:
                ref_product = water_products[0]
            else:
                ref_product = wybrane_kategorie[0]
                
            prod_info = FUCHS_PORTFOLIO[ref_product]
            rho = prod_info["density"] * 1000.0  
            v_kin = prod_info["visc_kin"] / 1_000_000.0  
            eta_dyn = v_kin * rho  
            
            max_charge_kg = mixer["capacity_m3"] * prod_info["density"] * 1000.0
            
            # Hydrodynamika mieszania
            D_tank = 2.2      
            d_agitor = 0.73   
            n_speed = 1.5     
            
            Re = (n_speed * (d_agitor ** 2) * rho) / eta_dyn
            
            if Re < 10:
                Ne = 50.0 / Re  
            elif Re >= 10 and Re < 10000:
                Ne = 2.5        
            else:
                Ne = 1.5        
                
            P_watts = Ne * (n_speed ** 3) * (d_agitor ** 5) * rho
            P_kw = P_watts / 1000.0
            
            duration_s = prod_info["cycle_h"] * 3600
            E_mix_mj = (P_watts * duration_s / 0.85) / 1_000_000.0
            
            c_term1, c_term2 = st.columns(2)
            with c_term1:
                dt_heat = st.number_input(f"ΔT grzania [°C] ({mixer['tag']}):", min_value=0, value=40, step=5, key=f"h_{mixer['tag']}")
                Q_heat_mj = (max_charge_kg * prod_info["cp"] * dt_heat) / 0.85 / 1000.0
            with c_term2:
                dt_cool = st.number_input(f"ΔT chłodzenia [°C] ({mixer['tag']}):", min_value=0, value=30, step=5, key=f"c_{mixer['tag']}")
                Q_cool_mj = (max_charge_kg * prod_info["cp"] * dt_cool) / 0.85 / 1000.0
                
            st.markdown(f"""
            * **Max. wielkość pojedynczego wkładu:** `{max_charge_kg:,.0f} kg`
            * **Zdefiniowana lepkość:** `{prod_info['visc_kin']} mm²/s` | **Liczba Reynoldsa (Re):** `{Re:,.1f}` | **Kryterium Newtona (Ne):** `{Ne:.2f}`
            * ⚡ **Moc potrzebna do mieszania cieczy:** `{P_kw:.2f} kW` | **Energia mieszania:** `{E_mix_mj:.1f} MJ/szarżę`
            * 🔥 **Energia potrzebna do podgrzania:** `{Q_heat_mj:,.1f} MJ` | ❄️ **Energia potrzebna do schłodzenia:** `{Q_cool_mj:,.1f} MJ`
            """)
            
            engineering_data.append({
                "Tag": mixer["tag"], "Materiał konstrukcyjny": mixer["material"], "Max wkład [kg]": int(max_charge_kg),
                "Moc mieszadła [kW]": round(P_kw, 2), "Energia grzania [MJ]": round(Q_heat_mj, 1), 
                "Energia chłodzenia [MJ]": round(Q_cool_mj, 1), "Lepkość płynu": f"{prod_info['visc_kin']} cSt", 
                "Temperatura zapłonu": prod_info["flash_point"], "Wrażliwość na mróz": prod_info["frost_sensitivity"]
            })
            st.markdown("---")
            
        st.subheader("📋 Zbiorcza Tabela Technologiczna Urządzeń")
        st.dataframe(pd.DataFrame(engineering_data), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 3: LOGISTYKA OPAKOWAŃ I MAGAZYN
# ==========================================
with tab3:
    st.header("Zliczanie Jednostek Opakowaniowych i Wymiarowanie Magazynu")
    
    total_pallets_all = 0
    pallet_rows = []
    
    for kat in wybrane_kategorie:
        v_annual = input_data[kat]["wolumen"]
        chosen_packs = input_data[kat]["opakowania"]
        
        valid_packs = [p for p in chosen_packs if p != "Bulk (Cysterna luz)"]
        
        if v_annual > 0 and valid_packs:
            m_prod_kg = v_annual / 12
            dens = FUCHS_PORTFOLIO[kat]["density"]
            total_volume_l = m_prod_kg / dens
            
            num_types = len(valid_packs)
            liters_per_type = total_volume_l / num_types
            
            st.markdown(f"#### 🧪 Logistyka opakowań dla linii: {kat.split(':')[-1].strip()}")
            
            c_p_idx = st.columns(num_types)
            for idx, p_name in enumerate(valid_packs):
                config = PACK_CONFIGS[p_name]
                
                total_szt = math.ceil(liters_per_type / config["size_l"])
                needed_pallets = math.ceil(total_szt / config["per_pallet"])
                total_pallets_all += needed_pallets
                
                with c_p_idx[idx]:
                    st.metric(label=f"Ilość: {p_name}", value=f"{total_szt:,} szt.")
                    st.write(f"Wymagane palety: **{needed_pallets} epal**")
                    
                pallet_rows.append({
                    "Produkt": kat.split(":")[-1].strip(),
                    "Typ Opakowania": p_name,
                    "Zapotrzebowanie [szt./miesiąc]": total_szt,
                    "Pakowanie na palecie [szt/epal]": config["per_pallet"],
                    "Wymagane Miejsca Paletowe [epal]": needed_pallets,
                    "Wrażliwość na temperaturę (Frost)": FUCHS_PORTFOLIO[kat]["frost_sensitivity"]
                })
            st.markdown("<br>", unsafe_allow_html=True)
            
    if pallet_rows:
        st.markdown("---")
        st.subheader("📋 Miesięczny Bilans Powierzchni Magazynowej Wyrobów Gotowych")
        df_pallets = pd.DataFrame(pallet_rows)
        st.dataframe(df_pallets, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📊 Podsumowanie Przestrzeni Magazynowej")
        
        # Poprawiona nazwa słownika (FUCHS_PORTFOLIO zamiast wcześniejszego błędu)
        frost_pallets = df_pallets[df_pallets["Wrażliwość na temperaturę (Frost)"] == "TAK"]["Wymagane Miejsca Paletowe [epal]"].sum()
        ambient_pallets = total_pallets_all - frost_pallets
        
        col_wh1, col_wh2, col_wh3 = st.columns(3)
        with col_wh1:
            st.metric(label="🔵 Całkowita pojemność magazynu", value=f"{total_pallets_all} epal")
        with col_wh2:
            st.metric(label="🌡️ Strefa Ogrzewana (Frost Protection)", value=f"{frost_pallets} epal")
        with col_wh3:
            st.metric(label="📦 Strefa Standardowa (Ambient)", value=f"{ambient_pallets} epal")
