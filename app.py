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

AVAILABLE_HOURS_MONTH = (250 * 16) / 12  # ~333.33 h/miesiąc

# --- PANEL BOCZNY ---
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

# Inicjalizacja tabeli bazowej w Session State
if "df_base" not in st.session_state or st.sidebar.button("🔄 Przywróć domyślne (Rekomendacja 75%)"):
    initial_rows = []
    for kat in wybrane_kategorie:
        initial_rows.append({
            "1. Nazwa rodziny": kat,
            "2. Roczna produkcja [kg]": 1200000,
            "3. Utilization %": 75.0
        })
    st.session_state.df_base = pd.DataFrame(initial_rows)

# Synchronizacja przy zmianie liczby zaznaczonych rodzin w sidebarze
if set(st.session_state.df_base["1. Nazwa rodziny"].tolist()) != set(wybrane_kategorie):
    updated_rows = []
    for kat in wybrane_kategorie:
        updated_rows.append({
            "1. Nazwa rodziny": kat,
            "2. Roczna produkcja [kg]": 1200000,
            "3. Utilization %": 75.0
        })
    st.session_state.df_base = pd.DataFrame(updated_rows)

# Zmienna sesyjna zabezpieczająca przekazywanie danych po zatwierdzeniu
if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

# --- PODZIAŁ NA TRZY ZAKŁADKI ---
tab1, tab2, tab3 = st.tabs([
    "📊 1. Główne Zestawienie i Symulacja Utylizacji", 
    "📐 2. Karta Techniczna Maszyn i Hydrodynamika", 
    "📦 3. Magazyn Wyrobów Gotowych i Palety"
])

# ==========================================
# ZAKŁADKA 1: JEDNA ZBIORCZA TABELA Z BLOKADAMI I ZATWIERDZENIEM
# ==========================================
with tab1:
    st.header("Zintegrowane Zestawienie Parametrów Procesowych")
    
    if wybrane_kategorie and not st.session_state.df_base.empty:
        st.markdown("""
        💡 *Wskazówki edycji:*
        * Pola oznaczone kolorem **🟦 [Edytuj]** są przeznaczone do wprowadzania danych wejściowych.
        * Pola oznaczone kolorem **🔒 [Blokada]** przeliczają się automatycznie na podstawie pozostałych kolumn.
        """)
        
        display_rows = []
        for idx, row in st.session_state.df_base.iterrows():
            kat = row["1. Nazwa rodziny"]
            m_annual = row["2. Roczna produkcja [kg]"]
            util_val = row["3. Utilization %"]
            
            m_monthly = m_annual / 12
            util_fraction = util_val / 100.0
            dens = FUCHS_PORTFOLIO[kat]["density"]
            cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            allocated_hours = AVAILABLE_HOURS_MONTH * util_fraction
            needed_batches = math.ceil(allocated_hours / cyc) if allocated_hours > 0 else 1
            
            batch_size_kg = math.ceil(m_monthly / needed_batches) if needed_batches > 0 else 0
            calculated_vol_m3 = batch_size_kg / (dens * 1000.0) if batch_size_kg > 0 else 0.0
            
            display_rows.append({
                "1. Nazwa rodziny": kat,
                "2. Roczna produkcja [kg]": int(m_annual),
                "3. Utilization %": float(util_val),
                "4. Liczba szarż na miesiąc": int(needed_batches),
                "5. Pojemność mieszalnika [m³]": f"{calculated_vol_m3:.1f} m³",
                "6. Wielkość pojedynczej szarży [kg]": int(batch_size_kg),
                "hidden_vol_m3": calculated_vol_m3,
                "hidden_batches": needed_batches,
                "hidden_batch_kg": batch_size_kg
            })
            
        df_display = pd.DataFrame(display_rows)
        
        # Wizualne wyróżnienie kolumn przy użyciu nagłówków i opisów kolumn
        edited_table = st.data_editor(
            df_display,
            hide_index=True,
            use_container_width=True,
            disabled=["1. Nazwa rodziny", "4. Liczba szarż na miesiąc", "5. Pojemność mieszalnika [m³]", "6. Wielkość pojedynczej szarży [kg]"],
            column_config={
                "1. Nazwa rodziny": st.column_config.TextColumn("1. Nazwa rodziny 🔒"),
                "2. Roczna produkcja [kg]": st.column_config.NumberColumn("2. Roczna produkcja [kg] 🟦 (Edytuj)", min_value=0, step=50000, format="%d"),
                "3. Utilization %": st.column_config.NumberColumn("3. Utilization % 🟦 (Edytuj)", min_value=1.0, max_value=200.0, step=5.0, format="%.1f%%"),
                "4. Liczba szarż na miesiąc": st.column_config.NumberColumn("4. Liczba szarż/miesiąc 🔒"),
                "5. Pojemność mieszalnika [m³]": st.column_config.TextColumn("5. Gabaryt reaktora 🔒"),
                "6. Wielkość pojedynczej szarży [kg]": st.column_config.NumberColumn("6. Masa szarży [kg] 🔒", format="%d"),
                "hidden_vol_m3": None, "hidden_batches": None, "hidden_batch_kg": None
            }
        )
        
        # Zapisanie bieżącego stanu edytora do bazy sesji
        st.session_state.df_base["2. Roczna produkcja [kg]"] = edited_table["2. Roczna produkcja [kg]"]
        st.session_state.df_base["3. Utilization %"] = edited_table["3. Utilization %"]
        
        st.markdown("<br>", unsafe_allow_html=True)
        # WYMAGANY PRZYCISK ZATWIERDZAJĄCY PRZEKAZANIE DANYCH DALEJ
        if st.button("📥 Zatwierdź i wyślij konfigurację do Zakładek 2 i 3", type="primary", use_container_width=True):
            confirmed_list_temp = []
            for idx, r in edited_table.iterrows():
                kat = r["1. Nazwa rodziny"]
                confirmed_list_temp.append({
                    "tag": f"MT-{101 + idx}",
                    "product_family": kat,
                    "capacity_m3": max(r["hidden_vol_m3"], 0.5),
                    "material": FUCHS_PORTFOLIO[kat]["material"],
                    "batches_count": r["hidden_batches"],
                    "mass_per_batch": r["hidden_batch_kg"],
                    "annual_volume": r["2. Roczna produkcja [kg]"]
                })
            st.session_state.confirmed_mixers = confirmed_list_temp
            st.success("✅ Dane zostały pomyślnie przetworzone! Przejdź do Zakładki 2 i 3, aby zobaczyć wyniki.")
            
    else:
        st.info("Zaznacz rodziny produktów w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: KARTA MASZYN Z CZASEM GRZANIA I CHŁODZENIA
# ==========================================
with tab2:
    st.header("Specyfikacja Inżynieryjna i Zużycie Energii Mieszalników")
    
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak zatwierdzonych danych. Wróć do Zakładki 1 i kliknij przycisk 'Zatwierdź i wyślij konfigurację'.")
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
                # Obliczenie energii cieplnej (w MJ) oraz czasu grzania (w minutach przy założeniu mocy grzewczej miksera)
                Q_heat_mj = (mixer["mass_per_batch"] * prod_info["cp"] * dt_heat) / 0.85 / 1000.0
                p_heat_kw = max(P_kw * 4, 25.0)  # Symulowana moc wbudowanej wężownicy/płaszcza grzewczego
                time_heat_min = (Q_heat_mj * 1_000_000) / (p_heat_kw * 1000) / 60 if p_heat_kw > 0 else 0
                
            with col_t2:
                dt_cool = st.number_input(f"ΔT schłodzenia [°C] ({mixer['tag']}):", min_value=0, value=30, step=5, key=f"c_{mixer['tag']}")
                Q_cool_mj = (mixer["mass_per_batch"] * prod_info["cp"] * dt_cool) / 0.85 / 1000.0
                p_cool_kw = max(P_kw * 5, 30.0)  # Symulowana moc układu chłodzenia
                time_cool_min = (Q_cool_mj * 1_000_000) / (p_cool_kw * 1000) / 60 if p_cool_kw > 0 else 0
                
            st.markdown(f"""
            * **Materiał konstrukcyjny:** `{prod_info['material']}` | **Wyliczona pojemność robocza miksera:** `{mixer['capacity_m3']:.2f} m³`
            * ⚡ **Moc znamionowa napędu:** `{P_kw:.2f} kW` | **Miksowanie mechaniczne płynu:** `{E_mix_mj:.1f} MJ/szarżę`
            * 🔥 **Ciepło technologiczne:** `{Q_heat_mj:,.1f} MJ/szarżę` ➡️ **Szacowany czas podgrzewania:** `{time_heat_min:.1f} minut`
            * ❄️ **Zapotrzebowanie na chłód:** `{Q_cool_mj:,.1f} MJ/szarżę` ➡️ **Szacowany czas schładzania:** `{time_cool_min:.1f} minut`
            """)
            
            engineering_table_data.append({
                "Mieszalnik": mixer["tag"],
                "Materiał": prod_info["material"],
                "Pojemność [m³]": round(mixer["capacity_m3"], 2),
                "Wielkość szarży [kg]": int(mixer["mass_per_batch"]),
                "Moc układu [kW]": round(P_kw, 2),
                "Czas grzania [min]": round(time_heat_min, 1),
                "Czas chłodzenia [min]": round(time_cool_min, 1),
                "Lepkość płynu": f"{prod_info['visc_kin']} cSt",
                "Wrażliwość na mróz": prod_info["frost_sensitivity"]
            })
            st.markdown("---")
            
        st.subheader("📋 Zbiorcza Karta Techniczna Maszyn")
        st.dataframe(pd.DataFrame(engineering_table_data), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 3: BILANS OPAKOWAŃ I LOGISTYKA
# ==========================================
with tab3:
    st.header("Zliczanie Jednostek Opakowaniowych i Wymiarowanie Magazynu")
    
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak zatwierdzonych danych. Wróć do Zakładki 1 i kliknij przycisk 'Zatwierdź i wyślij konfigurację'.")
    else:
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
