import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Kompleksowe Wymiarowanie Fabryki: Wolumeny ➔ Aparatura ➔ Energetyka ➔ Magazyn")
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
        "visc_kin": 68.0, "flash_point": "210°C", "frost_sensitivity": "Nie"
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
        "visc_kin": 22.0, "flash_point": "190°C", "frost_sensitivity": "Nie"
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

AVAILABLE_HOURS_MONTH = (250 * 16) / 12  # ~333.33 h przy pracy na 2 zmiany
TARGET_UTILIZATION = 0.75
EFFECTIVE_HOURS_MONTH = AVAILABLE_HOURS_MONTH * TARGET_UTILIZATION  # ~250h na maszynę

# --- 2. PANEL BOCZNY (WPROWADZANIE DANYCH WEJŚCIOWYCH) ---
st.sidebar.header("📋 KROK 1: Wybór Produktów")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Wielkości i Pakowanie")
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

# --- PAMIĘĆ PO ZATWIERDZENIU REKOMENDACJI ---
if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

# --- 3. PODZIAŁ NA TRZY SPECJALISTYCZNE ZAKŁADKI ---
tab1, tab2, tab3 = st.tabs([
    "📊 1. Wymiarowanie i Rekomendacja Linii", 
    "📐 2. Specyfikacja Urządzeń i Hydrodynamika", 
    "📦 3. Logistyka Opakowań i Magazyn Paletowy"
])

# ==========================================
# ZAKŁADKA 1: WYMIAROWANIE I REKOMENDACJA
# ==========================================
with tab1:
    st.header("Dobór Parku Maszynowego pod założone Obłożenie 75%")
    
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
        
        # Obliczenie potrzebnych roboczogodzin w oparciu o ustandaryzowaną szarżę 10m3
        batch_mass_10m3 = 10.0 * dens * 1000.0
        needed_batches = m_prod_kg / batch_mass_10m3
        needed_hours = needed_batches * cyc
        
        if mat == "Stal zwykła":
            total_hours_carbon += needed_hours
        else:
            total_hours_ss += needed_hours
            
        active_rows.append({
            "Produkt (Rodzina FUCHS)": kat.split(":")[-1].strip(),
            "Linia Materiałowa": mat,
            "Gęstość [g/cm³]": dens,
            "Miesięczna Produkcja [kg]": int(m_prod_kg),
            "Czas Cyklu Szarży [h]": cyc,
            "Wymagane Roboczogodziny [h/miesiąc]": round(needed_hours, 1)
        })
        
    if active_rows:
        st.dataframe(pd.DataFrame(active_rows), hide_index=True, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Rekomendacja Liczby Mieszalników (Wymiarowanie Globalne)")
        
        # Wyliczenie fizycznej ilości maszyn 10m3
        mixers_carbon = math.ceil(total_hours_carbon / EFFECTIVE_HOURS_MONTH) if total_hours_carbon > 0 else 0
        mixers_ss = math.ceil(total_hours_ss / EFFECTIVE_HOURS_MONTH) if total_hours_ss > 0 else 0
        
        c_rec1, c_rec2 = st.columns(2)
        
        with c_rec1:
            st.info("### 🏢 Węzeł Stali Zwykłej (Olejowy)")
            st.metric(label="Sugerowana liczba mieszalników 10m³", value=f"{mixers_carbon} szt.")
            if mixers_carbon > 0:
                util = (total_hours_carbon / (mixers_carbon * AVAILABLE_HOURS_MONTH)) * 100
                st.write(f"Prognozowane obłożenie węzła: **{util:.1f}%** (Target: 75%)")
                
        with c_rec2:
            st.success("### 🧪 Węzeł Stali Nierdzewnej (Wodny)")
            st.metric(label="Sugerowana liczba mieszalników 10m³", value=f"{mixers_ss} szt.")
            if mixers_ss > 0:
                util = (total_hours_ss / (mixers_ss * AVAILABLE_HOURS_MONTH)) * 100
                st.write(f"Prognozowane obłożenie węzła: **{util:.1f}%** (Target: 75%)")
                
        st.markdown("---")
        if st.button("🔒 ZATWIERDŹ REKOMENDACJĘ I WYGENERUJ APARATY"):
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
            st.success(f"Pomyślnie utworzono {len(confirmed_list)} reaktorów procesowych! Przejdź do zakładki nr 2.")
    else:
        st.warning("Ustaw wolumeny produkcyjne w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA I HYDRODYNAMIKA
# ==========================================
with tab2:
    st.header("Profil Inżynieryjny i Zapotrzebowanie Energetyczne Maszyn")
    
    if not st.session_state.confirmed_mixers:
        st.info("ℹ️ Zatwierdź rekomendację w Zakładce 1, aby wygenerować specyfikacje techniczne urządzeń.")
    else:
        # Wybór reprezentatywnego produktu do przypisania parametrów fizycznych do maszyn węzła
        oil_products = [kat for kat in wybrane_kategorie if FUCHS_PORTFOLIO[kat]["material"] == "Stal zwykła" and input_data[kat]["wolumen"] > 0]
        water_products = [kat for kat in wybrane_kategorie if FUCHS_PORTFOLIO[kat]["material"] == "Stal nierdzewna" and input_data[kat]["wolumen"] > 0]
        
        engineering_data = []
        
        for mixer in st.session_state.confirmed_mixers:
            st.markdown(f"### ⚙️ Reaktor: **{mixer['tag']}** ({mixer['material']})")
            
            # Dobór parametrów fizycznych w zależności od przypisanego węzła
            if mixer["type_node"] == "Olejowy" and oil_products:
                ref_product = oil_products[0]
            elif mixer["type_node"] == "Wodny" and water_products:
                ref_product = water_products[0]
            else:
                ref_product = wybrane_kategorie[0]
                
            prod_info = FUCHS_PORTFOLIO[ref_product]
            rho = prod_info["density"] * 1000.0  # kg/m3
            v_kin = prod_info["visc_kin"] / 1_000_000.0  # m2/s
            eta_dyn = v_kin * rho  # Pa*s (lepkość dynamiczna)
            
            max_charge_kg = mixer["capacity_m3"] * prod_info["density"] * 1000.0
            
            # --- MODELOWANIE HYDRODYNAMICZNE MOCY MIESZANIA ---
            D_tank = 2.2      # m (średnica zbiornika)
            d_agitor = 0.73   # m (średnica mieszadła płatowego)
            n_speed = 1.5     # obr/s (prędkość obrotowa mieszadła)
            
            # Liczba Reynoldsa (wzór z przesłanych grafik): Re = (n * d^2 * rho) / eta
            Re = (n_speed * (d_agitor ** 2) * rho) / eta_dyn
            
            # Wyznaczenie kryterium mocy (Liczby Newtona Ne) na podstawie krzywej z wykresu
            if Re < 10:
                Ne = 50.0 / Re  # Zakres laminarny
            elif Re >= 10 and Re < 10000:
                Ne = 2.5        # Zakres przejściowy (wartość uśredniona dla geometrii)
            else:
                Ne = 1.5        # Zakres w pełni burzliwy (stabilizacja Ne)
                
            # Pobór mocy efektywnej: P = Ne * n^3 * d^5 * rho [W]
            P_watts = Ne * (n_speed ** 3) * (d_agitor ** 5) * rho
            P_kw = P_watts / 1000.0
            
            # Całkowita energia mieszania na szarżę (uwzględniając sprawność napędu 85%)
            duration_s = prod_info["cycle_h"] * 3600
            E_mix_mj = (P_watts * duration_s / 0.85) / 1_000_000.0
            
            # --- INTERAKTYWNY BILANS TERMICZNY ---
            c_term1, c_term2 = st.columns(2)
            with c_term1:
                dt_heat = st.number_input(f"ΔT grzania [°C] dla {mixer['tag']}:", min_value=0, value=40, step=5, key=f"h_{mixer['tag']}")
                # Q = m * cp * dT / sprawność wymiennika 0.85
                Q_heat_mj = (max_charge_kg * prod_info["cp"] * dt_heat) / 0.85 / 1000.0
            with c_term2:
                dt_cool = st.number_input(f"ΔT chłodzenia [°C] dla {mixer['tag']}:", min_value=0, value=30, step=5, key=f"c_{mixer['tag']}")
                Q_cool_mj = (max_charge_kg * prod_info["cp"] * dt_cool) / 0.85 / 1000.0
                
            st.markdown(f"""
            * **Maksymalny wkład jednostkowy (szarża):** `{max_charge_kg:,.0f} kg`
            * **Zdefiniowana lepkość kinematyczna:** `{prod_info['visc_kin']} mm²/s` | **Liczba Reynoldsa (Re):** `{Re:,.1f}` | **Kryterium Newtona (Ne):** `{Ne:.2f}`
            * ⚡ **Wyliczona moc na wale mieszadła:** `{P_kw:.2f} kW` | **Energia mieszania szarży:** `{E_mix_mj:.1f} MJ`
            * 🔥 **Energia potrzebna do podgrzania szarży:** `{Q_heat_mj:,.1f} MJ`
            * ❄️ **Energia potrzebna do schłodzenia szarży:** `{Q_cool_mj:,.1f} MJ`
            """)
            
            engineering_data.append({
                "Tag": mixer["tag"], "Materiał": mixer["material"], "Max wkład [kg]": int(max_charge_kg),
                "Moc mieszadła [kW]": round(P_kw, 2), "Energia podgrzewania [MJ]": round(Q_heat_mj, 1), 
                "Energia chłodzenia [MJ]": round(Q_cool_mj, 1), "Klasa lepkości": f"{prod_info['visc_kin']} cSt", 
                "Zagrożenie ATEX (Flash Point)": prod_info["flash_point"], "Wrażliwość na mróz": prod_info["frost_sensitivity"]
            })
            st.markdown("---")
            
        st.subheader("📋 Zbiorcze Zestawienie Parametrów Technicznych Maszyn")
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
        
        # Filtrujemy Bulk, ponieważ cysterny nie zajmują miejsc paletowych w magazynie
        valid_packs = [p for p in chosen_packs if p != "Bulk (Cysterna luz)"]
        
        if v_annual > 0 and valid_packs:
            m_prod_kg = v_annual / 12
            dens = FUCHS_PORTFOLIO[kat]["density"]
            total_volume_l = m_prod_kg / dens
            
            num_types = len(valid_packs)
            liters_per_type = total_volume_l / num_types
            
            st.markdown(f"#### 🧪 Rozbicie logistyczne: {kat.split(':')[-1].strip()}")
            
            c_p_idx = st.columns(num_types)
            for idx, p_name in enumerate(valid_packs):
                config = PACK_CONFIGS[p_name]
                
                # Obliczenie fizycznej liczby sztuk opakowań
                total_szt = math.ceil(liters_per_type / config["size_l"])
                # Obliczenie wymaganych miejsc paletowych (zaokrąglone w górę)
                needed_pallets = math.ceil(total_szt / config["per_pallet"])
                total_pallets_all += needed_pallets
                
                with c_p_idx[idx]:
                    st.metric(label=f"Sztuk: {p_name}", value=f"{total_szt:,} szt.")
                    st.write(f"📦 Miejsca paletowe: **{needed_pallets} epal**")
                    
                pallet_rows.append({
                    "Produkt": kat.split(":")[-1].strip(),
                    "Typ Opakowania": p_name,
                    "Zapotrzebowanie [szt./miesiąc]": total_szt,
                    "Pakowanie na palecie [szt/epal]": config["per_pallet"],
                    "Wymagane Miejsca Paletowe [epal]": needed_pallets,
                    "Wrażliwość na temperaturę (Frost)": FUCHS_PORTFOLIO[kat]["frost_sensitivity"]
                })
            st.markdown("<br>", unsafe_allowed_html=True)
            
    if pallet_rows:
        st.markdown("---")
        st.subheader("📋 Miesięczny Bilans Powierzchni Magazynowej Wyrobów Gotowych")
        df_pallets = pd.DataFrame(pallet_rows)
        st.dataframe(df_pallets, hide_index=True, use_container_width=True)
        
        # Podsumowanie stref magazynowych
        st.markdown("---")
        st.subheader("📊 Podsumowanie Strategiczne dla Dyrektora Logistyki")
        
        frost_pallets = df_pallets[df_pallets["Wrażliwość na temperaturę (Frost)"] == "TAK"]["Wymagane Miejsca Paletowe [epal]"].sum()
        ambient_pallets = total_pallets_all - frost_pallets
        
        col_wh1, col_wh2, col_wh3 = st.columns(3)
        with col_wh1:
            st.metric(label="🔵 CAŁKOWITY WYMAGANY MAGAZYN (Miesięczny obrót)", value=f"{total_pallets_all} miejsc paletowych")
        with col_wh2:
            st.metric(label="🌡️ Strefa Ogrzewana (Zabezpieczenie przed mrozem)", value=f"{frost_pallets} miejsc")
        with col_wh3:
            st.metric(label="📦 Strefa Standardowa (Ambient)", value=f"{ambient_pallets} miejsc")
