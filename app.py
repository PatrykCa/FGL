import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Wymiarowanie Linii Produkcyjnych, Optymalizacja Rozlewu i Kalkulator Finansowy Odzysku Ciepła")
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
    "1l (Detal)": {"size_l": 1.0, "per_pallet": 480, "rate_szt_h": 2500},
    "4l (Karton)": {"size_l": 4.0, "per_pallet": 120, "rate_szt_h": 1200},
    "5l (Karton)": {"size_l": 5.0, "per_pallet": 96, "rate_szt_h": 1000},
    "10l (Kanister)": {"size_l": 10.0, "per_pallet": 40, "rate_szt_h": 600},
    "20l (Kanister)": {"size_l": 20.0, "per_pallet": 24, "rate_szt_h": 400},
    "60l (Beczka)": {"size_l": 60.0, "per_pallet": 9, "rate_szt_h": 150},
    "200l (Beczka)": {"size_l": 200.0, "per_pallet": 4, "rate_szt_h": 60},
    "1000l (IBC)": {"size_l": 1000.0, "per_pallet": 1, "rate_szt_h": 15}
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
godziny_na_zmiane = st.sidebar.slider("Liczba godzin na jedną zmianę:", min_value=4.0, max_value=12.0, value=8.0, step=0.5)

godziny_dziennie = liczba_zmian * godziny_na_zmiane
AVAILABLE_HOURS_MONTH = (250 * godziny_dziennie) / 12  

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 3: Wybór Opakowań do Splitu")
input_packs = {}
for kat in wybrane_kategorie:
    packs = st.sidebar.multiselect(
        f"Dostępne opakowania dla {kat}:", list(PACK_CONFIGS.keys()), default=["5l (Karton)", "200l (Beczka)", "1000l (IBC)"], key=f"packs_{kat}"
    )
    input_packs[kat] = packs

# Inicjalizacja i synchronizacja Session State
if "df_base" not in st.session_state or st.sidebar.button("🔄 Przywróć domyślne (Rekomendacja 75%)"):
    initial_rows = []
    for kat in wybrane_kategorie:
        initial_rows.append({"1. Nazwa rodziny": kat, "2. Roczna produkcja [kg]": 1200000, "3. Utilization %": 75.0})
    st.session_state.df_base = pd.DataFrame(initial_rows)

if set(st.session_state.df_base["1. Nazwa rodziny"].tolist()) != set(wybrane_kategorie):
    updated_rows = []
    for kat in wybrane_kategorie:
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

# Słowniki w session state do przenoszenia temperatur grzania z zakładki 2 do zakładki 3 i 4
if "heat_temps" not in st.session_state:
    st.session_state.heat_temps = {}
if "filling_temps" not in st.session_state:
    st.session_state.filling_temps = {}

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 1. Główne Zestawienie i Utylizacja", 
    "📐 2. Karta Maszyn i Reologia", 
    "📦 3. Logistyka i Czas Rozlewu",
    "💰 4. Analiza Finansowa i Odzysk Energii"
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
                "1. Nazwa rodziny": st.column_config.TextColumn("1. Nazwa rodziny 🔒"),
                "2. Roczna produkcja [kg]": st.column_config.NumberColumn("2. Roczna produkcja [kg] 🟦 (Edytuj)", min_value=0, step=50000, format="%d"),
                "3. Utilization %": st.column_config.NumberColumn("3. Utilization % 🟦 (Edytuj)", min_value=1.0, max_value=300.0, step=5.0, format="%.1f%%"),
                "4. Liczba szarż na miesiąc": st.column_config.NumberColumn("4. Liczba szarż/miesiąc 🔒"),
                "5. Pojemność mieszalnika [m³]": st.column_config.TextColumn("5. Gabaryt reaktora 🔒"),
                "6. Wielkość pojedynczej szarży [kg]": st.column_config.NumberColumn("6. Masa szarży [kg] 🔒", format="%d")
            }
        )
        
        if not edited_table.equals(df_display):
            st.session_state.df_base["2. Roczna produkcja [kg]"] = edited_table["2. Roczna produkcja [kg]"]
            st.session_state.df_base["3. Utilization %"] = edited_table["3. Utilization %"]
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📥 Zatwierdź i wyślij konfigurację do kolejnych kroków", type="primary", use_container_width=True):
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
        st.warning("⚠️ Brak zatwierdzonych danych z Zakładki 1.")
    else:
        engineering_table_data = []
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            
            st.markdown(f"### ⚙️ Konfiguracja Reaktora: **{mixer['tag']}** (Dedykowany dla: *{kat}*)")
            
            V_m3 = mixer["capacity_m3"]
            rho = prod_info["density"] * 1000.0  
            D_tank = round(2.2 * ((V_m3 / 10.0) ** (1/3)), 2)
            H_tank = round((4 * V_m3) / (math.pi * (D_tank ** 2)) * 1.2, 2)
            suggested_F = math.pi * D_tank * H_tank  
            d_agitor = round(D_tank / 3, 2)
            n_speed = 1.5  
            
            c_mix1, c_mix2, c_mix3 = st.columns(3)
            with c_mix1:
                agitator_choice = st.selectbox(f"Typ wirnika:", list(AGITATOR_TYPES.keys()), key=f"agit_{mixer['tag']}", index=1)
            with c_mix2:
                visc_min = st.number_input(f"Lepkość MIN [cSt]:", min_value=1.0, value=22.0, key=f"v_min_{mixer['tag']}")
            with c_mix3:
                visc_max = st.number_input(f"Lepkość MAX [cSt]:", min_value=5.0, value=220.0, key=f"v_max_{mixer['tag']}")
            
            cfg = AGITATOR_TYPES[agitator_choice]
            def calculate_visc_power(v_kin_cst):
                eta_dyn = (v_kin_cst / 1_000_000.0) * rho  
                Re = (n_speed * (d_agitor ** 2) * rho) / eta_dyn
                Ne = cfg["laminar_C"] / Re if Re < 50 else (cfg["turbulent_Ne"] * 1.3 if Re < 10000 else cfg["turbulent_Ne"])
                return Ne * (n_speed ** 3) * (d_agitor ** 5) * rho

            P_max_w = calculate_visc_power(visc_max)
            required_motor_power_kw = (P_max_w / 0.85 * 1.20) / 1000.0
            st.success(f"⚡ **Rekomendowany silnik dla {mixer['tag']}: {required_motor_power_kw:.2f} kW**")
            
            col_geom, _ = st.columns([1, 1])
            with col_geom:
                user_F_surface = st.number_input(f"Powierzchnia wymiany ciepła F [m²]:", min_value=0.1, value=float(round(suggested_F, 2)), key=f"uf_surf_{mixer['tag']}")
            
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("**🔥 Proces Grzania**")
                user_time_heat = st.number_input(f"Zadany czas grzania [min]:", min_value=1.0, value=45.0, key=f"ut_h_{mixer['tag']}")
                user_K_heat = st.number_input(f"Współczynnik K grzania:", min_value=10.0, value=500.0, key=f"uk_h_{mixer['tag']}")
                t_init_h = st.number_input(f"Temp. początkowa [°C]:", value=20, key=f"t_ih_{mixer['tag']}")
                t_final_h = st.number_input(f"Temp. końcowa (Procesowa) [°C]:", value=60, key=f"t_fh_{mixer['tag']}")
                
                # Zapisujemy temp. końcową grzania do sesji, by przekazać do bilansu odzysku
                st.session_state.heat_temps[mixer["tag"]] = t_final_h
                
                Q_heat_j = mixer["mass_per_batch"] * (prod_info["cp"] * 1000.0) * (t_final_h - t_init_h)
                req_p_heat_kw = (Q_heat_j / (user_time_heat * 60.0)) / 1000.0
                calculated_lmtd_h = Q_heat_j / (user_K_heat * user_F_surface * (user_time_heat * 60.0)) if (user_K_heat * user_F_surface * user_time_heat) > 0 else 0.0
                st.write(f"Moc grzania: **{req_p_heat_kw:.1f} kW** | LMTD grzania: **{calculated_lmtd_h:.1f} °C**")
                
            with col_t2:
                st.markdown("**❄️ Proces Chłodzenia**")
                user_time_cool = st.number_input(f"Zadany czas chłodzenia [min]:", min_value=1.0, value=60.0, key=f"ut_c_{mixer['tag']}")
                user_K_cool = st.number_input(f"Współczynnik K chłodzenia:", min_value=10.0, value=500.0, key=f"uk_c_{mixer['tag']}")
                t_init_c = st.number_input(f"Temp. początkowa chłodzenia [°C]:", value=60, key=f"t_ic_{mixer['tag']}")
                t_final_c = st.number_input(f"Temp. końcowa chłodzenia [°C]:", value=30, key=f"t_fc_{mixer['tag']}")
                Q_cool_j = mixer["mass_per_batch"] * (prod_info["cp"] * 1000.0) * (t_init_c - t_final_c)
                req_p_cool_kw = (Q_cool_j / (user_time_cool * 60.0)) / 1000.0
                calculated_lmtd_c = Q_cool_j / (user_K_cool * user_F_surface * (user_time_cool * 60.0)) if (user_K_cool * user_F_surface * user_time_cool) > 0 else 0.0
                st.write(f"Moc chłodzenia: **{req_p_cool_kw:.1f} kW** | LMTD chłodzenia: **{calculated_lmtd_c:.1f} °C**")

            engineering_table_data.append({
                "Mieszalnik": mixer["tag"], "Materiał korpusu": prod_info["material"], "Typ Mieszadła": agitator_choice, 
                "Pojemność [m³]": round(V_m3, 2), "Masa szarży [kg]": int(mixer["mass_per_batch"]), "Rekomendowany Silnik [kW]": round(required_motor_power_kw, 2)
            })
            st.markdown("---")
        st.dataframe(pd.DataFrame(engineering_table_data), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 3: LOGISTYKA, PODZIAŁ % I TEMPERATURA ROZLEWU
# ==========================================
with tab3:
    st.header("Harmonogramowanie Rozlewu Opakowań i Parametry Termiczne")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak zatwierdzonych danych z Zakładki 1.")
    else:
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            v_annual = mixer["annual_volume"]
            chosen_packs = input_packs.get(kat, [])
            
            if v_annual > 0 and chosen_packs:
                m_monthly_kg = v_annual / 12
                dens = FUCHS_PORTFOLIO[kat]["density"]
                total_volume_l = m_monthly_kg / dens
                t_reaktor_max = st.session_state.heat_temps.get(mixer["tag"], 60.0)
                
                st.markdown(f"### 🧪 Bilans i Wydajność Rozlewu dla linii: **{kat}** (Szarża miesięczna: **{int(m_monthly_kg):,} kg**)")
                
                # NOWE: Definiowanie temperatury rozlewu gotowego produktu
                col_t_fill, _ = st.columns([1, 2])
                with col_t_fill:
                    t_filling = st.number_input(
                        f"Wymagana temperatura na rozlewie dla {mixer['tag']} [°C]:", 
                        min_value=10.0, max_value=120.0, value=float(min(30.0, t_reaktor_max)), key=f"t_fill_{mixer['tag']}"
                    )
                    st.session_state.filling_temps[mixer["tag"]] = t_filling
                
                st.markdown("👇 *Wpisz procentowy podział rozlewu (Suma musi wynosić 100%):*")
                state_key = f"pct_df_{mixer['tag']}"
                if state_key not in st.session_state:
                    init_pct = [round(100.0 / len(chosen_packs), 1)] * len(chosen_packs)
                    st.session_state[state_key] = pd.DataFrame({"Typ Opakowania": chosen_packs, "Udział w rozlewie %": init_pct})
                
                edited_pct_df = st.data_editor(
                    st.session_state[state_key], hide_index=True, key=f"editor_{state_key}", use_container_width=True, disabled=["Typ Opakowania"],
                    column_config={"Udział w rozlewie %": st.column_config.NumberColumn("Udział w rozlewie % 🟦", min_value=0.0, max_value=100.0, step=5.0, format="%.1f%%")}
                )
                st.session_state[state_key] = edited_pct_df
                
                total_sum = edited_pct_df["Udział w rozlewie %"].sum()
                if not math.isclose(total_sum, 100.0, abs_tol=0.1):
                    st.error(f"❌ Suma udziałów wynosi {total_sum:.1f}%. Skoryguj do równego 100%.")
                    continue
                
                local_results = []
                total_family_filling_hours = 0.0
                
                for _, p_row in edited_pct_df.iterrows():
                    p_name = p_row["Typ Opakowania"]
                    pct = p_row["Udział w rozlewie %"] / 100.0
                    config = PACK_CONFIGS[p_name]
                    allocated_liters = total_volume_l * pct
                    
                    total_szt = math.ceil(allocated_liters / config["size_l"]) if allocated_liters > 0 else 0
                    needed_pallets = math.ceil(total_szt / config["per_pallet"]) if total_szt > 0 else 0
                    filling_hours = total_szt / config["rate_szt_h"] if total_szt > 0 else 0.0
                    total_family_filling_hours += filling_hours
                    
                    local_results.append({
                        "Opakowanie": p_name, "Objętość [l]": f"{int(allocated_liters):,}", "Zapotrzebowanie [szt./mies]": f"{total_szt:,}",
                        "Palety [epal]": needed_pallets, "Wydajność linii [szt./h]": config["rate_szt_h"], "Czas rozlewu [h/mies]": f"{filling_hours:.1f} h"
                    })
                
                st.dataframe(pd.DataFrame(local_results), hide_index=True, use_container_width=True)
                filling_days = total_family_filling_hours / godziny_dziennie if godziny_dziennie > 0 else 0
                st.info(f"⏱️ **Zajętość systemów rozlewczych: {total_family_filling_hours:.1f} h/miesiąc** (~**{filling_days:.1f} dni roboczych**).")
                st.markdown("---")

# ==========================================
# NOWA ZAKŁADKA 4: ANALIZA FINANSOWA I ODZYSK ENERGII (REKUPERACJA)
# ==========================================
with tab4:
    st.header("💰 Finansowa Optymalizacja Cieplna i Zwrot z Rekuperacji (ESG)")
    
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak zatwierdzonych maszyn. Uruchom konfigurację w Zakładce 1.")
    else:
        st.markdown("### 🏦 Koszty mediów i Waluta")
        c_fin1, c_fin2 = st.columns(2)
        with c_fin1:
            waluta = st.selectbox("Wybierz walutę operacyjną:", ["PLN", "EUR", "USD", "GBP"])
        with c_fin2:
            cena_mwh = st.number_input(f"Stawka za energię [{waluta}/MWh]:", min_value=1.0, value=450.0, step=10.0)
        
        st.markdown("---")
        st.subheader("📊 Zestawienie Energii Możliwej do Odzyskania i Oszczędności Finansowych")
        
        financial_summary = []
        total_monthly_savings = 0.0
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            
            t_max_mix = st.session_state.heat_temps.get(mixer["tag"], 60.0)
            t_rozlew = st.session_state.filling_temps.get(mixer["tag"], 30.0)
            
            # Obliczanie miesięcznej masy całej produkcji
            m_monthly_kg = mixer["annual_volume"] / 12
            
            rekuperacja_status = "Brak (Rozlew w temp. mieszania)"
            energia_mwh_mies = 0.0
            oszczednosc_mies = 0.0
            
            # Jeżeli schładzamy produkt przed rozlewem, pojawia się potencjał odzysku
            if t_rozlew < t_max_mix:
                # Q = m * cp * delta_T (wynik w kJ, bo cp jest w kJ/(kg*K))
                delta_t_cooling = t_max_mix - t_rozlew
                Q_recovered_kj = m_monthly_kg * prod_info["cp"] * delta_t_cooling
                
                # Konwersja kJ na MWh (1 kWh = 3600 kJ, 1 MWh = 3 600 000 kJ)
                energia_mwh_mies = Q_recovered_kj / 3_600_000.0
                oszczednosc_mies = energia_mwh_mies * cena_mwh
                total_monthly_savings += oszczednosc_mies
                rekuperacja_status = "🔥 POTENCJAŁ ODZYSKU"
            
            financial_summary.append({
                "Reaktor / Linia": mixer["tag"],
                "Produkt": kat,
                "Temp. Mieszania [°C]": f"{t_max_mix}°C",
                "Temp. Rozlewu [°C]": f"{t_rozlew}°C",
                "Status": rekuperacja_status,
                "Energia do odzyskania [MWh/miesiąc]": round(energia_mwh_mies, 3),
                f"Oszczędność miesięczna [{waluta}]": round(oszczednosc_mies, 2),
                f"Oszczędność roczna [{waluta}]": round(oszczednosc_mies * 12, 2)
            })
            
        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, use_container_width=True)
        
        # --- TABLICE KPI DLA DYREKCJI FINANSOWEJ ---
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### 🏆 Globalny Potencjał Oszczędności FUCHS")
        
        kpi1, kpi2 = st.columns(2)
        with kpi1:
            st.metric(
                label=f"Łączne miesięczne redukcje kosztów energii", 
                value=f"{total_monthly_savings:,.2f} {waluta}"
            )
        with kpi2:
            st.metric(
                label=f"Prognozowane roczne oszczędności z rekuperacji", 
                value=f"{total_monthly_savings * 12:,.2f} {waluta}",
                delta="Redukcja śladu węglowego (CO₂)", delta_color="inverse"
            )
        
        st.caption("💡 *Wskazówka inżynieryjna: Odzyskana energia może zostać skierowana do wstępnego podgrzewania kolejnych szarż baz olejowych lub na cele grzewcze infrastruktury zakładowej.*")
