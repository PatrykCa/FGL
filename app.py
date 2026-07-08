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
# ZAKŁADKA 1: STRONA GŁÓWNA (NOWE ZESTAWIENIE)
# ==========================================
with tab1:
    st.header("Zestawienie Wolumenów i Parametrów Procesowych Fabryki")
    
    total_hours_carbon = 0.0
    total_hours_ss = 0.0
    active_rows = []
    
    for kat in wybrane_kategorie:
        v_annual = input_data[kat]["wolumen"]
        if v_annual == 0:
            continue
            
        m_prod_kg = v_annual / 12
        dens = FUCHS_PORTFOLIO[kat]["density"]
        cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
        mat = FUCHS_PORTFOLIO[kat]["material"]
        
        # Obliczenia bazowe oparte na referencyjnym zbiorniku 10m3
        v_mixer_m3 = 10.0
        batch_mass_kg = v_mixer_m3 * dens * 1000.0
        needed_batches = m_prod_kg / batch_mass_kg
        needed_hours = needed_batches * cyc
        
        if mat == "Stal zwykła":
            total_hours_carbon += needed_hours
        else:
            total_hours_ss += needed_hours
            
        # Zgodnie z wytycznymi użytkownika: komplet informacji o procesie w tabeli głównej
        active_rows.append({
            "Produkt (Rodzina FUCHS)": kat.split(":")[-1].strip(),
            "Węzeł Technologiczny": "Olejowy (Węglowy)" if mat == "Stal zwykła" else "Wodny (Nierdzewny)",
            "Wielkość produkcyjna [kg/miesiąc]": int(m_prod_kg),
            "Liczba szarż [szt/miesiąc]": round(needed_batches, 1),
            "Pojemność mieszalnika [m³]": v_mixer_m3,
            "Czas produkcji - mieszania [h/szarżę]": cyc,
            "Wymagany czas pracy maszyny [h/m]": round(needed_hours, 1)
        })
        
    if active_rows:
        # Zmieniono use_container_width na width="stretch" (nowy standard Streamlit)
        st.dataframe(pd.DataFrame(active_rows), hide_index=True, width="stretch")
        
        st.markdown("---")
        st.subheader("Globalne Obłożenie Węzłów Produkcyjnych (Cel: 75% Utylizacji)")
        
        mixers_carbon = math.ceil(total_hours_carbon / EFFECTIVE_HOURS_MONTH) if total_hours_carbon > 0 else 0
        mixers_ss = math.ceil(total_hours_ss / EFFECTIVE_HOURS_MONTH) if total_hours_ss > 0 else 0
        
        c_rec1, c_rec2 = st.columns(2)
        
        with c_rec1:
            st.info("### 🏢 Węzeł Olejowy (Stal Zwykła)")
            st.metric(label="Rekomendowana liczba mieszalników 10m³", value=f"{mixers_carbon} szt.")
            if mixers_carbon > 0:
                util_carbon = (total_hours_carbon / (mixers_carbon * AVAILABLE_HOURS_MONTH)) * 100
                st.write(f"Obłożenie węzła (Utilization %): **{util_carbon:.1f}%**")
                
        with c_rec2:
            st.success("### 🧪 Węzeł Wodny (Stal Nierdzewna)")
            st.metric(label="Rekomendowana liczba mieszalników 10m³", value=f"{mixers_ss} szt.")
            if mixers_ss > 0:
                util_ss = (total_hours_ss / (mixers_ss * AVAILABLE_HOURS_MONTH)) * 100
                st.write(f"Obłożenie węzła (Utilization %): **{util_ss:.1f}%**")
                
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
            st.success(f"Zatwierdzono strukturę! Wygenerowano {len(confirmed_list)} maszyn. Przejdź do Zakładki 2.")
    else:
        st.warning("Wprowadź niezerowe wolumeny produkcji w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA URZĄDZEŃ (HYDRODYNAMIKA)
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
            
            # WYWODZENIE ENERGII MIESZANIA (HYDRODYNAMIKA Z GRAFIK BOOKA)
            D_tank = 2.2      
            d_agitor = 0.73   
            n_speed = 1.5     
            
            # Liczba Reynoldsa (Re)
            Re = (n_speed * (d_agitor ** 2) * rho) / eta_dyn
            
            # Odczyt liczby Newtona (Ne) z charakterystyki mocowej mieszadła
            if Re < 10:
                Ne = 50.0 / Re  
            elif Re >= 10 and Re < 10000:
                Ne = 2.5        
            else:
                Ne = 1.5        
                
            # Pobór mocy: P = Ne * n³ * d⁵ * ρ [W]
            P_watts = Ne * (n_speed ** 3) * (d_agitor ** 5) * rho
            P_kw = P_watts / 1000.0
            
            # Energia mieszania na szarżę
            duration_s = prod_info["cycle_h"] * 3600
            E_mix_mj = (P_watts * duration_s / 0.85) / 1_000_000.0
            
            # DYNAMICZNY BILANS CIEPLNY (ΔT)
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
                "Energia chłodzenia [MJ]": round(Q_cool_mj, 1), "Lepkość płynu": f"{prod_info['visc_kin']}
