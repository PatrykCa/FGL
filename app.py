import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Zaawansowane Wymiarowanie Mieszadeł dla Zmiennej Lepkości i Różnych Geometrii Wirnika")
st.markdown("---")

# --- 1. BAZA DANYCH PROCESOWYCH I FIZYKOCHEMICZNYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Hydraulic Oils (RENOLIN)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "220°C", "frost_sensitivity": "Nie"
    },
    "Gear & Turbine Oils (RENOLIN)": {
        "material": "Stal zwykła", "density": 0.89, "cycle_h": 5, "cp": 1.9, 
        "flash_point": "240°C", "frost_sensitivity": "Nie"
    },
    "Slideway & Machine Oils (RENAX)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "210°C", "frost_sensitivity": "Nie"
    },
    "Engine Oils (TITAN)": {
        "material": "Stal zwykła", "density": 0.87, "cycle_h": 5, "cp": 2.1, 
        "flash_point": "230°C", "frost_sensitivity": "Nie"
    },
    "Gear & Transmission Oils (TITAN)": {
        "material": "Stal zwykła", "density": 0.88, "cycle_h": 5, "cp": 2.0, 
        "flash_point": "210°C", "frost_sensitivity": "Nie"
    },
    "Water-miscible (ECOCOOL)": {
        "material": "Stal nierdzewna", "density": 0.99, "cycle_h": 6, "cp": 3.8, 
        "flash_point": "Brak", "frost_sensitivity": "TAK"
    },
    "Non-water-miscible (ECOCUT)": {
        "material": "Stal zwykła", "density": 0.87, "cycle_h": 4, "cp": 2.0, 
        "flash_point": "190°C", "frost_sensitivity": "Nie"
    },
    "Cleaners (RENOCLEAN)": {
        "material": "Stal nierdzewna", "density": 1.01, "cycle_h": 4, "cp": 3.9, 
        "flash_point": "Brak", "frost_sensitivity": "TAK"
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

AGITATOR_TYPES = {
    "Turbinowe (Rushton)": {"laminar_C": 70.0, "turbulent_Ne": 5.0, "desc": "Wysokie ścinanie, doskonałe do dyspersji dodatków."},
    "Łapowe / Płatowe": {"laminar_C": 50.0, "turbulent_Ne": 2.5, "desc": "Mieszanie łagodne, niskie opory, uniwersalne do olejów."},
    "Propelerowe (Śmigłowe)": {"laminar_C": 35.0, "turbulent_Ne": 0.8, "desc": "Mieszanie osiowe, wysoka cyrkulacja przy niskiej lepkości."}
}

# --- PANEL BOCZNY ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz aktywne linie produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Hydraulic Oils (RENOLIN)", "Engine Oils (TITAN)", "Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⏱️ KROK 2: Założenia Czasu Pracy")
liczba_zmian = st.sidebar.slider("Liczba zmian produkcyjnych:", min_value=1.0, max_value=3.0, value=1.0, step=0.5)
godziny_na_zmiane = st.sidebar.number_input("Liczba godzin na jedną zmianę:", min_value=4, max_value=12, value=8, step=1)

godziny_dziennie = liczba_zmian * godziny_na_zmiane
AVAILABLE_HOURS_MONTH = (250 * godziny_dziennie) / 12  

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 3: Dystrybucja Opakowań")
input_packs = {}
for kat in wybrane_kategorie:
    packs = st.sidebar.multiselect(
        f"Opakowania dla {kat}:", list(PACK_CONFIGS.keys()), default=["200l (Beczka)", "1000l (IBC)"], key=f"packs_{kat}"
    )
    input_packs[kat] = packs

# --- NAPRAWIONA INICJALIZACJA STANÓW (ELIMINACJA ATTRIBUTERROR LINIJA 90) ---
if "df_base" not in st.session_state or st.sidebar.button("🔄 Przywróć domyślne (Rekomendacja 75%)"):
    initial_rows = []
    for kat in wybrane_kategorie:
        initial_rows.append({"1. Nazwa rodziny": kat, "2. Roczna produkcja [kg]": 1200000, "3. Utilization %": 75.0})
    st.session_state.df_base = pd.DataFrame(initial_rows)

# Synchronizacja przy zmianie listy wybranych kategorii
current_stored = st.session_state.df_base["1. Nazwa rodziny"].tolist() if not st.session_state.df_base.empty else []
if set(current_stored) != set(wybrane_kategorie):
    updated_rows = []
    for kat in wybrane_kategorie:
        # Zachowaj istniejące dane, dopisz nowe
        existing = st.session_state.df_base[st.session_state.df_base["1. Nazwa rodziny"] == kat]
        if not existing.empty:
            updated_rows.append({
                "1. Nazwa rodziny": kat,
                "2. Roczna produkcja [kg]": int(existing.iloc[0]["2. Roczna produkcja [kg]"]),
                "3. Utilization %": float(existing.iloc[0]["3. Utilization %"])
            })
        else:
            updated_rows.append({"1. Nazwa rodziny": kat, "2. Roczna produkcja [kg]": 1200000, "3. Utilization %": 75.0})
    st.session_state.df_base = pd.DataFrame(updated_rows)

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

tab1, tab2, tab3 = st.tabs([
    "📊 1. Główne Zestawienie i Symulacja Utylizacji", 
    "📐 2. Karta Techniczna Maszyn i Reologia", 
    "📦 3. Magazyn Wyrobów Gotowych i Palety"
])

# ==========================================
# ZAKŁADKA 1: TABELA PROCESOWA
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych (Baza: {godziny_dziennie:.1f}h/dzień)")
    if wybrane_kategorie and not st.session_state.df_base.empty:
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
                "1. Nazwa rodziny": kat, "2. Roczna produkcja [kg]": int(m_annual), "3. Utilization %": float(util_val),
                "4. Liczba szarż na miesiąc": int(needed_batches), "5. Pojemność mieszalnika [m³]": f"{calculated_vol_m3:.1f} m³",
                "6. Wielkość pojedynczej szarży [kg]": int(batch_size_kg),
                "hidden_vol_m3": calculated_vol_m3, "hidden_batches": needed_batches, "hidden_batch_kg": batch_size_kg
            })
            
        df_display = pd.DataFrame(display_rows)
        edited_table = st.data_editor(
            df_display, hide_index=True, use_container_width=True,
            disabled=["1. Nazwa rodziny", "4. Liczba szarż na miesiąc", "5. Pojemność mieszalnika [m³]", "6. Wielkość pojedynczej szarży [kg]"],
            column_config={
                "2. Roczna produkcja [kg]": st.column_config.NumberColumn("2. Roczna produkcja [kg] 🟦", min_value=0, step=50000, format="%d"),
                "3. Utilization %": st.column_config.NumberColumn("3. Utilization % 🟦", min_value=1.0, max_value=300.0, step=5.0, format="%.1f%%")
            }
        )
        
        if not edited_table.equals(df_display):
            st.session_state.df_base["2. Roczna produkcja [kg]"] = edited_table["2. Roczna produkcja [kg]"]
            st.session_state.df_base["3. Utilization %"] = edited_table["3. Utilization %"]
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📥 Zatwierdź i wyślij konfigurację do Zakładek 2 i 3", type="primary", use_container_width=True):
            confirmed_list_temp = []
            for idx, r in edited_table.iterrows():
                kat = r["1. Nazwa rodziny"]
                confirmed_list_temp.append({
                    "tag": f"MT-{101 + idx}", "product_family": kat, "capacity_m3": max(r["hidden_vol_m3"], 0.5),
                    "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": r["hidden_batches"],
                    "mass_per_batch": r["hidden_batch_kg"], "annual_volume": r["2. Roczna produkcja [kg]"]
                })
            st.session_state.confirmed_mixers = confirmed_list_temp
            st.success("✅ Konfiguracja zatwierdzona! Przejdź do Zakładki 2.")
    else:
        st.info("Zaznacz rodziny produktów w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: KARTA MASZYN - REOLOGIA I CIEPŁO
# ==========================================
with tab2:
    st.header("Wymiarowanie Układu Mieszania pod Kątem Zmiennej Lepkości")
    
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak zatwierdzonych danych. Wróć do Zakładki 1 i kliknij przycisk 'Zatwierdź i wyślij konfigurację'.")
    else:
        engineering_table_data = []
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            
            st.markdown(f"### ⚙️ Konfiguracja Reaktora: **{mixer['tag']}** (Dedykowany dla: *{kat}*)")
            
            # --- INPUT PARAMETRÓW MIESZADŁA I LEPKOŚCI ---
            c_mix1, c_mix2, c_mix3 = st.columns(3)
            with c_mix1:
                agitator_choice = st.selectbox(f"Typ wirnika mieszadła:", list(AGITATOR_TYPES.keys()), key=f"agit_{mixer['tag']}", index=1)
                st.caption(f"ℹ️ *{AGITATOR_TYPES[agitator_choice]['desc']}*")
            with c_mix2:
                visc_min = st.number_input(f"Lepkość MINIMALNA (startowa) [cSt]:", min_value=1.0, value=22.0, step=5.0, key=f"v_min_{mixer['tag']}")
            with c_mix3:
                visc_max = st.number_input(f"Lepkość MAKSYMALNA (końcowa) [cSt]:", min_value=5.0, value=220.0, step=10.0, key=f"v_max_{mixer['tag']}")
            
            # --- OBLICZENIA HYDRODYNAMICZNE ---
            V_m3 = mixer["capacity_m3"]
            rho = prod_info["density"] * 1000.0  
            D_tank = round(2.2 * ((V_m3 / 10.0) ** (1/3)), 2)
            H_tank = round((4 * V_m3) / (math.pi * (D_tank ** 2)) * 1.2, 2)
            F_surface = math.pi * D_tank * H_tank  
            d_agitor = round(D_tank / 3, 2)
            n_speed = 1.5  
            
            cfg = AGITATOR_TYPES[agitator_choice]
            
            def calculate_visc_power(v_kin_cst):
                eta_dyn = (v_kin_cst / 1_000_000.0) * rho  
                Re = (n_speed * (d_agitor ** 2) * rho) / eta_dyn
                if Re < 50:  
                    Ne = cfg["laminar_C"] / Re
                elif Re >= 50 and Re < 10000:  
                    Ne = cfg["turbulent_Ne"] * 1.3
                else:  
                    Ne = cfg["turbulent_Ne"]
                P_w = Ne * (n_speed ** 3) * (d_agitor ** 5) * rho
                return P_w, Re, Ne

            P_min_w, Re_min, Ne_min = calculate_visc_power(visc_min)
            P_max_w, Re_max, Ne_max = calculate_visc_power(visc_max)
            required_motor_power_kw = (P_max_w / 0.85 * 1.20) / 1000.0
            
            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.write(f"🟢 **Stan początkowy szarży ({visc_min} cSt):**")
                st.write(f"* $Re_{{min}}$: `{Re_min:,.1f}` | $Ne$: `{Ne_min:.2f}` | Moc netto: **{P_min_w/1000.0:.2f} kW**")
            with col_res2:
                st.write(f"🔴 **Stan końcowy szarży ({visc_max} cSt):**")
                st.write(f"* $Re_{{max}}$: `{Re_max:,.1f}` | $Ne$: `{Ne_max:.2f}` | Moc netto: **{P_max_w/1000.0:.2f} kW**")
                
            st.success(f"⚡ **Rekomendowana moc silnika: {required_motor_power_kw:.2f} kW** (Uwzględnia bufor bezpieczeństwa +20%)")
            
            # --- SEKCJA CIEPLNA (LMTD) ---
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("**🔥 Proces Grzania**")
                user_time_heat = st.number_input(f"Zadany czas grzania [min]:", min_value=1.0, value=45.0, key=f"ut_h_{mixer['tag']}")
                user_K_heat = st.number_input(f"Współczynnik K grzania [W/(m²·K)]:", min_value=10.0, value=500.0, key=f"uk_h_{mixer['tag']}")
                t_init_h = st.number_input(f"Temp. początkowa [°C]:", value=20, key=f"t_ih_{mixer['tag']}")
                t_final_h = st.number_input(f"Temp. końcowa [°C]:", value=60, key=f"t_fh_{mixer['tag']}")
                
                Q_heat_j = mixer["mass_per_batch"] * (prod_info["cp"] * 1000.0) * (t_final_h - t_init_h)
                req_p_heat_kw = (Q_heat_j / (user_time_heat * 60.0)) / 1000.0
                calculated_lmtd_h = Q_heat_j / (user_K_heat * F_surface * (user_time_heat * 60.0)) if (user_K_heat * F_surface * user_time_heat) > 0 else 0.0
                st.write(f"Wymagana moc grzania: **{req_p_heat_kw:.1f} kW** | Wymagane LMTD: **{calculated_lmtd_h:.1f} °C**")
                
            with col_t2:
                st.markdown("**❄️ Proces Chłodzenia**")
                user_time_cool = st.number_input(f"Zadany czas chłodzenia [min]:", min_value=1.0, value=60.0, key=f"ut_c_{mixer['tag']}")
                user_K_cool = st.number_input(f"Współczynnik K chłodzenia [W/(m²·K)]:", min_value=10.0, value=500.0, key=f"uk_c_{mixer['tag']}")
                t_init_c = st.number_input(f"Temp. początkowa [°C]:", value=70, key=f"t_ic_{mixer['tag']}")
                t_final_c = st.number_input(f"Temp. końcowa [°C]:", value=30, key=f"t_fc_{mixer['tag']}")
                
                Q_cool_j = mixer["mass_per_batch"] * (prod_info["cp"] * 1000.0) * (t_init_c - t_final_c)
                req_p_cool_kw = (Q_cool_j / (user_time_cool * 60.0)) / 1000.0
                calculated_lmtd_c = Q_cool_j / (user_K_cool * F_surface * (user_time_cool * 60.0)) if (user_K_cool * F_surface * user_time_cool) > 0 else 0.0
                st.write(f"Wymagana moc chłodzenia: **{req_p_cool_kw:.1f} kW** | Wymagane LMTD: **{calculated_lmtd_c:.1f} °C**")

            engineering_table_data.append({
                "Mieszalnik": mixer["tag"], "Typ Mieszadła": agitator_choice, "Pojemność [m³]": round(V_m3, 2), "Masa szarży [kg]": int(mixer["mass_per_batch"]),
                "Lepkość zakres [cSt]": f"{visc_min} - {visc_max}", "Rekomendowany Silnik [kW]": round(required_motor_power_kw, 2),
                "Moc grzania [kW]": round(req_p_heat_kw, 1), "Moc chłodzenia [kW]": round(req_p_cool_kw, 1)
            })
            st.markdown("---")
            
        st.subheader("📋 Zbiorcze Zestawienie Urządzeń")
        st.dataframe(pd.DataFrame(engineering_table_data), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 3: LOGISTYKA
# ==========================================
with tab3:
    st.header("Zliczanie Jednostek Opakowaniowych i Wymiarowanie Magazynu")
    if st.session_state.confirmed_mixers:
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
                
                for p_name in chosen_packs:
                    config = PACK_CONFIGS[p_name]
                    total_szt = math.ceil(liters_per_type / config["size_l"])
                    needed_pallets = math.ceil(total_szt / config["per_pallet"])
                    total_pallets_all += needed_pallets
                    
                    pallet_rows.append({
                        "Linia produktowa": kat, "Typ Jednostki": p_name, "Zapotrzebowanie [szt./miesiąc]": total_szt,
                        "Miejsca Paletowe [epal]": needed_pallets
                    })
        if pallet_rows:
            st.dataframe(pd.DataFrame(pallet_rows), hide_index=True, use_container_width=True)
