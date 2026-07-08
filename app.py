import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Dynamiczne Wymiarowanie Linii na Bazie Optymalizacji Stopnia Utylizacji Węzła")
st.markdown("---")

# --- 1. BAZA DANYCH PROCESOWYCH I FIZYKOCHEMICZNYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Hydraulic Oils (RENOLIN)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "visc_kin": 46.0, "flash_point": "220°C", "frost_sensitivity": "Nie"
    },
    "Gear & Turbine Oils (RENOLIN)": {
        "material": "Stal zwykła", "density": 0.89, "cycle_h": 5, "cp": 1.9, 
        "visc_kin": 220.0, "flash_point": "240°C", "frost_sensitivity": "Nie"
    },
    "Slideway & Machine Oils (RENAX)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "210°C", "visc_kin": 68.0, "frost_sensitivity": "Nie"
    },
    "Engine Oils (TITAN)": {
        "material": "Stal zwykła", "density": 0.87, "cycle_h": 5, "cp": 2.1, 
        "visc_kin": 95.0, "flash_point": "230°C", "frost_sensitivity": "Nie"
    },
    "Gear & Transmission Oils (TITAN)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 5, "cp": 2.0, 
        "visc_kin": 140.0, "flash_point": "210°C", "frost_sensitivity": "Nie"
    },
    "Water-miscible (ECOCOOL)": {
        "material": "Stal nierdzewna", "density": 0.99, "cycle_h": 6, "cp": 3.8, 
        "visc_kin": 60.0, "flash_point": "Brak", "frost_sensitivity": "TAK"
    },
    "Non-water-miscible (ECOCUT)": {
        "material": "Stal zwykła", "density": 0.87, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "190°C", "visc_kin": 22.0, "frost_sensitivity": "Nie"
    },
    "Cleaners (RENOCLEAN)": {
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

# --- PANEL BOCZNY (WYBÓR LINII I OPAKOWAŃ) ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz aktywne linie produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Hydraulic Oils (RENOLIN)", "Engine Oils (TITAN)", "Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Dystrybucja Opakowań")
input_packs = {}
for kat in wybrane_kategorie:
    packs = st.sidebar.multiselect(
        f"Opakowania dla {kat}:",
        list(PACK_CONFIGS.keys()),
        default=["200l (Beczka)", "1000l (IBC)"],
        key=f"packs_{kat}"
    )
    input_packs[kat] = packs

# --- PRZYGOTOWANIE STRUKTURY DANYCH W SESSION STATE ---
if "df_data" not in st.session_state or st.sidebar.button("🔄 Resetuj do rekomendacji (75%)"):
    initial_rows = []
    for kat in wybrane_kategorie:
        initial_rows.append({
            "Nazwa rodziny": kat,
            "Roczna produkcja [kg]": 1200000,
            "Utilization %": 75.0
        })
    st.session_state.df_data = pd.DataFrame(initial_rows)

# Synchronizacja stanów w przypadku dodania/usunięcia kategorii z poziomu sidebaru
current_families = st.session_state.df_data["Nazwa rodziny"].tolist() if not st.session_state.df_data.empty else []
if set(current_families) != set(wybrane_kategorie):
    new_rows = []
    for kat in wybrane_kategorie:
        new_rows.append({
            "Nazwa rodziny": kat,
            "Roczna produkcja [kg]": 1200000,
            "Utilization %": 75.0
        })
    st.session_state.df_data = pd.DataFrame(new_rows)

# --- PODZIAŁ NA TRZY ZAKŁADKI ---
tab1, tab2, tab3 = st.tabs([
    "📊 1. Główne Zestawienie i Symulacja Utylizacji", 
    "📐 2. Karta Techniczna Maszyn i Hydrodynamika", 
    "📦 3. Magazyn Wyrobów Gotowych i Palety"
])

# ==========================================
# ZAKŁADKA 1: JEDNA, INTERAKTYWNA TABELA ZBIORCZA
# ==========================================
with tab1:
    st.header("Zestawienie parametrów procesowych i optymalizacji obłożenia")
    
    if wybrane_kategorie and not st.session_state.df_data.empty:
        st.markdown("💡 *Możesz edytować kolumny **Roczna produkcja [kg]** oraz **Utilization %** bezpośrednio w komórkach tabeli. Zmiana wartości automatycznie przeliczy parametry szarży i gabaryt miksera.*")
        
        # 1. Wyświetlenie i edycja parametrów wejściowych przez użytkownika
        edited_inputs = st.data_editor(
            st.session_state.df_data,
            hide_index=True,
            use_container_width=True,
            disabled=["Nazwa rodziny"],
            column_config={
                "Nazwa rodziny": st.column_config.TextColumn("1. Nazwa rodziny"),
                "Roczna produkcja [kg]": st.column_config.NumberColumn("2. Roczna produkcja [kg] (Edytuj)", min_value=0, step=50000, format="%d"),
                "Utilization %": st.column_config.NumberColumn("3. Utilization % (Edytuj)", min_value=1.0, max_value=200.0, step=5.0)
            }
        )
        st.session_state.df_data = edited_inputs

        # 2. SILNIK OBLICZENIOWY: Dynamiczne generowanie wyników na podstawie powyższej tabeli
        st.markdown("### 📊 Wynikowa specyfikacja operacyjna linii")
        
        calculated_rows = []
        confirmed_list_temp = []
        
        for idx, row in edited_inputs.iterrows():
            kat = row["Nazwa rodziny"]
            m_annual = row["Roczna produkcja [kg]"]
            util_val = row["Utilization %"]
            
            m_monthly = m_annual / 12
            util_fraction = util_val / 100.0
            dens = FUCHS_PORTFOLIO[kat]["density"]
            cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            # Wyliczenie całkowitej liczby szarż w miesiącu
            allocated_hours = AVAILABLE_HOURS_MONTH * util_fraction
            needed_batches = math.ceil(allocated_hours / cyc) if allocated_hours > 0 else 1
            
            # Wielkość pojedynczej szarży [kg] oraz objętość robocza mieszalnika [m³]
            batch_size_kg = math.ceil(m_monthly / needed_batches) if needed_batches > 0 else 0
            calculated_vol_m3 = batch_size_kg / (dens * 1000.0) if batch_size_kg > 0 else 0.0
            
            calculated_rows.append({
                "1. Nazwa rodziny": kat,
                "2. Roczna produkcja [kg]": f"{int(m_annual):,}",
                "3. Utilization %": f"{util_val:.1f}%",
                "4. Liczba szarż na miesiąc": int(needed_batches),
                "5. Pojemność mieszalnika [m³]": f"{calculated_vol_m3:.1f} m³",
                "6. Wielkość pojedynczej szarży [kg]": f"{int(batch_size_kg):,}"
            })
            
            # Przekazanie danych do kolejnych zakładek aplikacji
            confirmed_list_temp.append({
                "tag": f"MT-{101 + idx}",
                "product_family": kat,
                "capacity_m3": max(calculated_vol_m3, 0.5),
                "material": FUCHS_PORTFOLIO[kat]["material"],
                "batches_count": needed_batches,
                "mass_per_batch": batch_size_kg,
                "annual_volume": m_annual
            })
            
        st.dataframe(pd.DataFrame(calculated_rows), hide_index=True, use_container_width=True)
        st.session_state.confirmed_mixers = confirmed_list_temp
    else:
        st.info("Zaznacz rodziny produktów w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA URZĄDZEŃ I HYDRODYNAMIKA
# ==========================================
with tab2:
    st.header("Specyfikacja Inżynieryjna i Zużycie Energii Mieszalników")
    
    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.info("ℹ️ Profile maszyn pojawią się automatycznie po wygenerowaniu danych w Zakładce 1.")
    else:
        engineering_table_data = []
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            
            st.markdown(f"### ⚙️ Reaktor Procesowy: **{mixer['tag']}** (Dedykowany dla: *{kat}*)")
            
            rho = prod_info["density"] * 1000.0  
            v_kin = prod_info["visc_kin"] / 1_000_000.0  
            eta_dyn = v_kin * rho  
            
            D_tank = round(2.2 * ((mixer["capacity_m3"] / 10.0) ** (1/3)), 2)
            d_agitor = round(D_tank / 3, 2)
            n_speed = 1.5 
            
            Re = (n_speed * (d_agitor ** 2) * rho) / eta_dyn
            Ne = 50.0 / Re if Re < 10 else (2.5 if Re < 10000 else 1.5)
                
            P_watts = Ne * (n_speed ** 3) * (d_agitor ** 5) * rho
            P_kw = P_watts / 1000.0
            
            duration_s = prod_info["cycle_h"] * 3600
            E_mix_mj = (P_watts * duration_s / 0.85) / 1_000_000.0
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                dt_heat = st.number_input(f"ΔT podgrzewania [°C] ({mixer['tag']}):", min_value=0, value=40, step=5, key=f"h_{mixer['tag']}")
                Q_heat_mj = (mixer["mass_per_batch"] * prod_info["cp"] * dt_heat) / 0.85 / 1000.0
            with col_t2:
                dt_cool = st.number_input(f"ΔT schłodzenia [°C] ({mixer['tag']}):", min_value=0, value=30, step=5, key=f"c_{mixer['tag']}")
                Q_cool_mj = (mixer["mass_per_batch"] * prod_info["cp"] * dt_cool) / 0.85 / 1000.0
                
            st.markdown(f"""
            * **Materiał konstrukcyjny reaktora:** `{prod_info['material']}` | **Wyliczona pojemność robocza miksera:** `{mixer['capacity_m3']:.2f} m³`
            * **Reologia:** lepkość kinematyczna `{prod_info['visc_kin']} mm²/s` | **Liczba Reynoldsa (Re):** `{Re:,.1f}`
            * ⚡ **Moc znamionowa napędu:** `{P_kw:.2f} kW` | **Pobór energii mechanicznej:** `{E_mix_mj:.1f} MJ/szarżę`
            * 🔥 **Ciepło technologiczne:** `{Q_heat_mj:,.1f} MJ/szarżę` | ❄️ **Zapotrzebowanie na chłód:** `{Q_cool_mj:,.1f} MJ/szarżę`
            """)
            
            engineering_table_data.append({
                "Mieszalnik": mixer["tag"],
                "Materiał": prod_info["material"],
                "Pojemność [m³]": round(mixer["capacity_m3"], 2),
                "Wielkość szarży [kg]": int(mixer["mass_per_batch"]),
                "Moc układu [kW]": round(P_kw, 2),
                "Ciepło grzania [MJ]": round(Q_heat_mj, 1),
                "Energia chłodzenia [MJ]": round(Q_cool_mj, 1),
                "Lepkość płynu": f"{prod_info['visc_kin']} cSt",
                "Klasyfikacja zapłonu (ATEX)": prod_info["flash_point"],
                "Wrażliwość na mróz": prod_info["frost_sensitivity"]
            })
            st.markdown("---")
            
        st.subheader("📋 Zbiorcza Tabela Inżynieryjna Urządzeń")
        st.dataframe(pd.DataFrame(engineering_table_data), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 3: BILANS OPAKOWAŃ I LOGISTYKA
# ==========================================
with tab3:
    st.header("Zliczanie Jednostek Opakowaniowych i Wymiarowanie Magazynu")
    
    if "confirmed_mixers" in st.session_state and st.session_state.confirmed_mixers:
        total_pallets_all = 0
        pallet_rows = []
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            v_annual = mixer["annual_volume"]
            chosen_packs = input_packs.get(kat, [])
            
            if v_annual > 0 and chosen_packs:
                m_prod_kg = v_annual / 12
                dens = FUCHS_PORTFOLIO[kat]["density"]
                total_volume_l = m_prod_kg / dens
                
                num_types = len(chosen_packs)
                liters_per_type = total_volume_l / num_types
                
                st.markdown(f"#### 🧪 Rozbicie logistyczne dla linii: *{kat}*")
                
                c_p_idx = st.columns(num_types)
                for idx, p_name in enumerate(chosen_packs):
                    config = PACK_CONFIGS[p_name]
                    
                    total_szt = math.ceil(liters_per_type / config["size_l"])
                    needed_pallets = math.ceil(total_szt / config["per_pallet"])
                    total_pallets_all += needed_pallets
                    
                    with c_p_idx[idx]:
                        st.metric(label=f"Ilość: {p_name}", value=f"{total_szt:,} szt.")
                        st.write(f"Wymagane palety: **{needed_pallets} epal**")
                        
                    pallet_rows.append({
                        "Linia produktowa": kat,
                        "Typ Jednostki": p_name,
                        "Zapotrzebowanie [szt./miesiąc]": total_szt,
                        "Układ na palecie [szt/epal]": config["per_pallet"],
                        "Miejsca Paletowe [epal]": needed_pallets,
                        "Kontrola Temperatury (Frost)": FUCHS_PORTFOLIO[kat]["frost_sensitivity"]
                    })
                st.markdown("<br>", unsafe_allow_html=True)
                
        if pallet_rows:
            st.markdown("---")
            st.subheader("📋 Miesięczny Bilans Powierzchni Składowania")
            df_pallets = pd.DataFrame(pallet_rows)
            st.dataframe(df_pallets, hide_index=True, use_container_width=True)
    else:
        st.info("ℹ️ Dane logistyczne pojawią się po skonfigurowaniu produkcji w Zakładce 1.")
