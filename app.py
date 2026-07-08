import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Wymiarowanie Linii Produkcyjnych z Dedykowanymi Mieszalnikami dla Każdej Rodziny")
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

AVAILABLE_HOURS_MONTH = (250 * 16) / 12  # ~333.33 h/miesiąc nominalnego czasu pracy na 2 zmiany

# --- PANEL BOCZNY (INPUT DANYCH HANDLOWO-TECHNICZNYCH) ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz aktywne linie produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Wolumeny & Pojemności")
input_data = {}

for kat in wybrane_kategorie:
    short_name = kat.split(':')[-1].strip()
    st.sidebar.markdown(f"### 🧪 {short_name}")
    
    vol = st.sidebar.number_input("Roczna produkcja [kg]:", min_value=0, value=1200000, step=100000, key=f"vol_{kat}")
    
    # Elastyczne zdefiniowanie pojemności dedykowanego miksera bezpośrednio w panelu wejściowym
    mixer_cap = st.sidebar.slider("Pojemność dedykowanego mieszalnika [m³]:", min_value=1, max_value=30, value=10, step=1, key=f"cap_{kat}")
    
    packs = st.sidebar.multiselect(
        "Opakowania końcowe:",
        list(PACK_CONFIGS.keys()) + ["Bulk (Cysterna luz)"],
        default=["200l (Beczka)", "1000l (IBC)"],
        key=f"packs_{kat}"
    )
    input_data[kat] = {"wolumen": vol, "pojemnosc_m3": mixer_cap, "opakowania": packs}

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

# --- KREOWANIE ZAKŁADEK ---
tab1, tab2, tab3 = st.tabs([
    "📊 1. Główne Zestawienie Procesowe i Obłożenie", 
    "📐 2. Karta Techniczna Maszyn i Hydrodynamika", 
    "📦 3. Bilans Magazynowy i Miejsca Paletowe"
])

# ==========================================
# ZAKŁADKA 1: GŁÓWNE ZESTAWIENIE PROCESOWE
# ==========================================
with tab1:
    st.header("Analiza Efektywności i Parametrów Operacyjnych Maszyn Dedykowanych")
    
    active_rows = []
    confirmed_list_temp = []
    
    for idx_num, kat in enumerate(wybrane_kategorie):
        v_annual = input_data[kat]["wolumen"]
        if v_annual == 0:
            continue
            
        m_prod_kg = v_annual / 12
        v_mixer_m3 = input_data[kat]["pojemnosc_m3"]
        dens = FUCHS_PORTFOLIO[kat]["density"]
        cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
        mat = FUCHS_PORTFOLIO[kat]["material"]
        short_name = kat.split(":")[-1].strip()
        
        # Obliczenie wagi pojedynczego pełnego wkładu reaktora w kg
        batch_mass_kg = v_mixer_m3 * dens * 1000.0
        
        # Wyznaczenie liczby szarż zaokrąglonej zawsze w GÓRĘ do liczby całkowitej (int)
        needed_batches = math.ceil(m_prod_kg / batch_mass_kg)
        
        # Realny czas pracy reaktora w miesiącu na podstawie całkowitej liczby szarż
        total_work_hours = needed_batches * cyc
        
        # Obłożenie (Utilization %) dedykowanej maszyny w odniesieniu do nominalnego czasu pracy (dwie zmiany)
        utilization_pct = (total_work_hours / AVAILABLE_HOURS_MONTH) * 100
        
        # Przypisanie unikalnego tagu inżynieryjnego maszynie dedykowanej
        mixer_tag = f"MT-{100 + idx_num + 1}"
        
        active_rows.append({
            "Dedykowany Mieszalnik": mixer_tag,
            "Rodzina Produktu FUCHS": short_name,
            "Wielkość produkcyjna [kg/miesiąc]": int(m_prod_kg),
            "Pojemność mieszalnika [m³]": v_mixer_m3,
            "Liczba szarż [całkowita]": int(needed_batches),
            "Czas produkcji [h/szarżę]": cyc,
            "Wymagany czas pracy [h/miesiąc]": round(total_work_hours, 1),
            "Obłożenie (Utilization %)": f"{utilization_pct:.1f}%"
        })
        
        # Przygotowanie danych do Zakładki nr 2
        confirmed_list_temp.append({
            "tag": mixer_tag,
            "product_family": kat,
            "capacity_m3": v_mixer_m3,
            "material": mat,
            "batches_count": needed_batches
        })
        
    if active_rows:
        st.dataframe(pd.DataFrame(active_rows), hide_index=True, use_container_width=True)
        
        # Automatyczne odświeżenie obiektów w pamięci podręcznej sesji po zmianie suwaków
        st.session_state.confirmed_mixers = confirmed_list_temp
        
        st.markdown("---")
        st.info("💡 **Inżynieryjna interpretacja obłożenia:** Jeżeli obłożenie (Utilization %) przekracza 100%, oznacza to konieczność uruchomienia 3. zmiany w fabryce lub zwiększenia pojemności reaktora w panelu bocznym.")
    else:
        st.warning("Wprowadź wolumeny i aktywuj rodziny produktowe w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA TECHNICZNA REAKTORÓW
# ==========================================
with tab2:
    st.header("Karty Charakterystyki Technicznej i Energetycznej Dedykowanych Aparatów")
    
    if not st.session_state.confirmed_mixers:
        st.info("ℹ️ Aktywuj produkty w panelu bocznym, aby wyświetlić karty techniczne aparatów.")
    else:
        engineering_table_data = []
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            
            st.markdown(f"### ⚙️ Profil Operacyjny Urządzenia: **{mixer['tag']}** (Dedykowany dla: *{kat.split(':')[-1].strip()}*)")
            
            rho = prod_info["density"] * 1000.0  # kg/m3
            v_kin = prod_info["visc_kin"] / 1_000_000.0  # m2/s
            eta_dyn = v_kin * rho  # Pa*s
            
            max_charge_kg = mixer["capacity_m3"] * prod_info["density"] * 1000.0
            
            # --- MODELOWANIE REOLOGICZNE I HYDRODYNAMICZNE MOCY ---
            # Skalowanie średnic zbiornika w funkcji pojemności geometrycznej
            D_tank = round(2.2 * ((mixer["capacity_m3"] / 10.0) ** (1/3)), 2)
            d_agitor = round(D_tank / 3, 2)
            n_speed = 1.5 # obr/s
            
            # Wyznaczenie Kryterium Reynoldsa (Re)
            Re = (n_speed * (d_agitor ** 2) * rho) / eta_dyn
            
            # Aproksymacja liczby Newtona (Ne) z wykresów oporów hydrodynamicznych
            if Re < 10:
                Ne = 50.0 / Re
            elif Re >= 10 and Re < 10000:
                Ne = 2.5
            else:
                Ne = 1.5
                
            # Wyliczenie zapotrzebowania mocy: P = Ne * n^3 * d^5 * rho [W]
            P_watts = Ne * (n_speed ** 3) * (d_agitor ** 5) * rho
            P_kw = P_watts / 1000.0
            
            # Łączna energia mieszania przypadająca na jedną pełną szarżę (sprawność przekładni = 85%)
            duration_s = prod_info["cycle_h"] * 3600
            E_mix_mj = (P_watts * duration_s / 0.85) / 1_000_000.0
            
            # --- INTERAKTYWNY BILANS TERMICZNY ---
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                dt_heat = st.number_input(f"ΔT podgrzewania [°C] ({mixer['tag']}):", min_value=0, value=40, step=5, key=f"h_{mixer['tag']}")
                Q_heat_mj = (max_charge_kg * prod_info["cp"] * dt_heat) / 0.85 / 1000.0
            with col_t2:
                dt_cool = st.number_input(f"ΔT schłodzenia [°C] ({mixer['tag']}):", min_value=0, value=30, step=5, key=f"c_{mixer['tag']}")
                Q_cool_mj = (max_charge_kg * prod_info["cp"] * dt_cool) / 0.85 / 1000.0
                
            st.markdown(f"""
            * **Materiał konstrukcyjny korpusu:** `{mixer['material']}` | **Maksymalna wielkość pojedynczego wkładu:** `{max_charge_kg:,.0f} kg`
            * **Reologia cieczy:** klasa lepkości `{prod_info['visc_kin']} mm²/s` | **Liczba Reynoldsa (Re):** `{Re:,.1f}` | **Kryterium Newtona (Ne):** `{Ne:.2f}`
            * ⚡ **Moc mechaniczna na wale mieszadła:** `{P_kw:.2f} kW` | **Pobór energii na 1 szarżę:** `{E_mix_mj:.1f} MJ`
            * 🔥 **Zapotrzebowanie na ciepło (grzanie):** `{Q_heat_mj:,.1f} MJ/szarżę` | ❄️ **Zapotrzebowanie na chłód:** `{Q_cool_mj:,.1f} MJ/szarżę`
            """)
            
            engineering_table_data.append({
                "Mieszalnik": mixer["tag"],
                "Materiał": mixer["material"],
                "Max wkład [kg]": int(max_charge_kg),
                "Lepkość": f"{prod_info['visc_kin']} cSt",
                "Moc układu [kW]": round(P_kw, 2),
                "Ciepło grzania [MJ]": round(Q_heat_mj, 1),
                "Chłód procesowy [MJ]": round(Q_cool_mj, 1),
                "Klasa Flash Point": prod_info["flash_point"],
                "Ochrona przed mrozem": prod_info["frost_sensitivity"]
            })
            st.markdown("---")
            
        st.subheader("📋 Zbiorcze Zestawienie Parametrów Aparatury")
        st.dataframe(pd.DataFrame(engineering_table_data), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 3: LOGISTYKA OPAKOWAŃ I PALET
# ==========================================
with tab3:
    st.header("Zliczanie Jednostek Opakowaniowych i Wymiarowanie Magazynu")
    
    total_pallets_all = 0
    pallet_rows = []
    
    for kat in wybrane_kategorie:
        v_annual = input_data[kat]["wolumen"]
        chosen_packs = input_data[kat]["opakowania"]
        
        # Wyłączenie BULK (cystern) z kalkulacji miejsc paletowych
        valid_packs = [p for p in chosen_packs if p != "Bulk (Cysterna luz)"]
        
        if v_annual > 0 and valid_packs:
            m_prod_kg = v_annual / 12
            dens = FUCHS_PORTFOLIO[kat]["density"]
            total_volume_l = m_prod_kg / dens
            
            num_types = len(valid_packs)
            liters_per_type = total_volume_l / num_types
            
            st.markdown(f"#### 🧪 Rozbicie logistyczne dla linii: *{kat.split(':')[-1].strip()}*")
            
            c_p_idx = st.columns(num_types)
            for idx, p_name in enumerate(valid_packs):
                config = PACK_CONFIGS[p_name]
                
                # Wyliczenie sztuk i zaokrąglenie w górę miejsc paletowych (Epal)
                total_szt = math.ceil(liters_per_type / config["size_l"])
                needed_pallets = math.ceil(total_szt / config["per_pallet"])
                total_pallets_all += needed_pallets
                
                with c_p_idx[idx]:
                    st.metric(label=f"Ilość: {p_name}", value=f"{total_szt:,} szt.")
                    st.write(f"Wymagane palety: **{needed_pallets} epal**")
                    
                pallet_rows.append({
                    "Linia produktowa": kat.split(":")[-1].strip(),
                    "Typ Jednostki": p_name,
                    "Zapotrzebowanie [szt./miesiąc]": total_szt,
                    "Układ na palecie [szt/epal]": config["per_pallet"],
                    "Miejsca Paletowe [epal]": needed_pallets,
                    "Kontrola Temperatury (Frost)": prod_info["frost_sensitivity"]
                })
            st.markdown("<br>", unsafe_allow_html=True)
            
    if pallet_rows:
        st.markdown("---")
        st.subheader("📋 Miesięczny Bilans Powierzchni Składowania Wyrobów Gotowych")
        df_pallets = pd.DataFrame(pallet_rows)
        st.dataframe(df_pallets, hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📊 Podsumowanie Przestrzeni Magazynowej (Warehouse Sizing)")
        
        frost_pallets = df_pallets[df_pallets["Kontrola Temperatury (Frost)"] == "TAK"]["Miejsca Paletowe [epal]"].sum()
        ambient_pallets = total_pallets_all - frost_pallets
        
        col_wh1, col_wh2, col_wh3 = st.columns(3)
        with col_wh1:
            st.metric(label="🔵 CAŁKOWITA POJEMNOŚĆ MAGAZYNU (Obrót)", value=f"{total_pallets_all} epal")
        with col_wh2:
            st.metric(label="🌡️ Strefa Kontrolowana (Grzana)", value=f"{frost_pallets} epal")
        with col_wh3:
            st.metric(label="📦 Strefa Standardowa (Ambient)", value=f"{ambient_pallets} epal")
