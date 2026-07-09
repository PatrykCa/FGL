import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Kompletna Platforma Wymiarowania Linii, Reologii, Logistyki i Surowców")
st.markdown("---")

# --- 1. BAZA DANYCH PROCESOWYCH I FIZYKOCHEMICZNYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Hydraulic Oils (RENOLIN)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0},
    "Gear & Turbine Oils (RENOLIN)": {"material": "Stal zwykła", "density": 0.89, "cycle_h": 5, "cp": 1.9, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0},
    "Slideway & Machine Oils (RENAX)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0},
    "Engine Oils (TITAN)": {"material": "Stal zwykła", "density": 0.87, "cycle_h": 5, "cp": 2.1, "oil_group": "Syntetyczne (Gr. III/IV)", "water_content": 0.0},
    "Gear & Transmission Oils (TITAN)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 5, "cp": 2.0, "oil_group": "Syntetyczne (Gr. III/IV)", "water_content": 0.0},
    "Water-miscible (ECOCOOL)": {"material": "Stal nierdzewna", "density": 0.99, "cycle_h": 6, "cp": 3.8, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.65},
    "Non-water-miscible (ECOCUT)": {"material": "Stal zwykła", "density": 0.87, "cycle_h": 4, "cp": 2.0, "oil_group": "Mineralne (Gr. I/II)", "water_content": 0.0},
    "Cleaners (RENOCLEAN)": {"material": "Stal nierdzewna", "density": 1.01, "cycle_h": 4, "cp": 3.9, "oil_group": "Brak (Specjalistyczne)", "water_content": 0.85}
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
    "Turbinowe (Rushton)": {"laminar_C": 70.0, "turbulent_Ne": 5.0},
    "Łapowe / Płatowe": {"laminar_C": 50.0, "turbulent_Ne": 2.5},
    "Propelerowe (Śmigłowe)": {"laminar_C": 35.0, "turbulent_Ne": 0.8}
}

# --- 2. INICJALIZACJA STRUKTUR W SESJI ---
if "prod_dict" not in st.session_state:
    st.session_state.prod_dict = {}
for k in FUCHS_PORTFOLIO.keys():
    if k not in st.session_state.prod_dict:
        st.session_state.prod_dict[k] = {
            "roczna": 1200000, 
            "user_vol_m3": 15.0,  
            "skus": 1, 
            "num_tanks": 1
        }

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

if "calculated_times" not in st.session_state:
    st.session_state.calculated_times = {}

# ==========================================
# ZINTEGROWANY PANEL BOCZNY
# ==========================================
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

st.sidebar.header("⚙️ KROK 3: Konfiguracja i Split Opakowań")
opakowania_podzial = st.session_state.setdefault("opakowania_podzial", {})

for kat in wybrane_kategorie:
    st.sidebar.markdown(f"##### 🏭 Linia: **{kat}**")
    packs = st.sidebar.multiselect(f"Dostępne opakowania:", list(PACK_CONFIGS.keys()), default=["5l (Karton)", "200l (Beczka)", "1000l (IBC)"], key=f"packs_{kat}")
    
    if packs:
        domyslny_procent = round(100.0 / len(packs), 1)
        suma_procentow_linii = 0.0
        for p in packs:
            key_id = f"pct_{kat}_{p}"
            current_val = opakowania_podzial.get(key_id, domyslny_procent)
            val = st.sidebar.number_input(f"    ↳ Udział {p} [%]", min_value=0.0, max_value=100.0, value=float(current_val), step=5.0, key=key_id)
            opakowania_podzial[key_id] = val
            suma_procentow_linii += val
        
        if round(suma_procentow_linii, 1) == 100.0:
            st.sidebar.success(f"    ✅ Bilans {kat}: 100%")
        else:
            st.sidebar.error(f"    ❌ Suma dla {kat}: {suma_procentow_linii}% (Musi być 100%!)")
    st.sidebar.markdown("---")

# --- STRUKTURA INTERFEJSU ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 1. Główne Zestawienie i Utylizacja", 
    "📐 2. Karta Maszyn i Dobór Pomp", 
    "📦 3. Logistyka i Czas Rozlewu",
    "💰 4. Analiza Finansowa i Koszty Produkcji",
    "🛢️ 5. Surowce i Park Zbiorników"
])

# ==========================================
# ZAKŁADKA 1: GŁÓWNE ZESTAWIENIE I DEDYKOWANA FLOTA
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych (Baza: {godziny_dziennie:.1f}h/dzień)")
    
    if wybrane_kategorie:
        if "tab1_editor" in st.session_state and "edited_rows" in st.session_state.tab1_editor:
            edits = st.session_state.tab1_editor["edited_rows"]
            active_families = [k for k in FUCHS_PORTFOLIO.keys() if k in wybrane_kategorie]
            for idx, changes in edits.items():
                if int(idx) < len(active_families):
                    family_name = active_families[int(idx)]
                    if "2. Roczna produkcja [kg] 🟦" in changes:
                        st.session_state.prod_dict[family_name]["roczna"] = int(changes["2. Roczna produkcja [kg] 🟦"])
                    if "3. Pojemność Mieszalnika [m³] 🟦" in changes:
                        st.session_state.prod_dict[family_name]["user_vol_m3"] = float(changes["3. Pojemność Mieszalnika [m³] 🟦"])
                    if "4. Liczba SKUs 🟦" in changes:
                        st.session_state.prod_dict[family_name]["skus"] = int(changes["4. Liczba SKUs 🟦"])

        input_matrix_rows = []
        for kat in wybrane_kategorie:
            input_matrix_rows.append({
                "1. Nazwa rodziny 🔒": kat,
                "2. Roczna produkcja [kg] 🟦": int(st.session_state.prod_dict[kat]["roczna"]),
                "3. Pojemność Mieszalnika [m³] 🟦": float(st.session_state.prod_dict[kat]["user_vol_m3"]),
                "4. Liczba SKUs 🟦": int(st.session_state.prod_dict[kat]["skus"])
            })

        st.markdown("##### 📥 Krok A: Definiowanie Założeń Zdolności Produkcyjnej, Gabarytów i SKUs")
        
        with st.form("form_założeń_wejściowych"):
            edited_table = st.data_editor(
                pd.DataFrame(input_matrix_rows),
                hide_index=True,
                width="stretch",
                disabled=["1. Nazwa rodziny 🔒"],
                column_config={
                    "2. Roczna produkcja [kg] 🟦": st.column_config.NumberColumn(min_value=0, step=50000, format="%d"),
                    "3. Pojemność Mieszalnika [m³] 🟦": st.column_config.NumberColumn(min_value=0.5, max_value=150.0, step=0.5, format="%.1f m³"),
                    "4. Liczba SKUs 🟦": st.column_config.NumberColumn(min_value=1, step=1)
                },
                key="tab1_editor"
            )
            st.form_submit_button("💾 Zapisz dane wejściowe i przelicz zapotrzebowanie aparatów", type="primary", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 🛢️ Krok B: Konfiguracja Floty Równoległej na Podstawie Liczby SKUs")
        
        for kat in wybrane_kategorie:
            current_skus = st.session_state.prod_dict[kat]["skus"]
            if current_skus > 1:
                st.session_state.prod_dict[kat]["num_tanks"] = st.number_input(
                    f"Wykryto **{current_skus} SKUs** dla linii **{kat}**. Na ile osobnych mieszalników chcesz rozbić tę produkcję?",
                    min_value=1,
                    max_value=int(current_skus),
                    value=min(int(st.session_state.prod_dict[kat].get("num_tanks", 1)), int(current_skus)),
                    key=f"tanks_input_{kat}"
                )
            else:
                st.session_state.prod_dict[kat]["num_tanks"] = 1

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🏭 3. Skorygowana i Zweryfikowana Flota Mieszalników")
        
        final_fleet_rows = []
        confirmed_mixers_blueprint = []
        total_annual_production = 0
        total_batches_per_month_global = 0
        total_volume_global = 0.0
        tag_counter = 101

        for kat in wybrane_kategorie:
            m_annual = st.session_state.prod_dict[kat]["roczna"]
            v_tank_user = st.session_state.prod_dict[kat]["user_vol_m3"]
            tanks_count = st.session_state.prod_dict[kat]["num_tanks"]
            
            rho_product = FUCHS_PORTFOLIO[kat]["density"]
            cyc_h = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            mass_per_batch = v_tank_user * rho_product * 1000.0
            annual_per_tank = m_annual / tanks_count
            monthly_per_tank = annual_per_tank / 12.0
            
            batches_per_tank = math.ceil(monthly_per_tank / mass_per_batch) if mass_per_batch > 0 else 0
            real_utilization = (batches_per_tank * cyc_h) / AVAILABLE_HOURS_MONTH * 100.0 if AVAILABLE_HOURS_MONTH > 0 else 0.0
            
            for t_idx in range(tanks_count):
                tag_id = f"MT-{tag_counter}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                status_txt = "🟢 Optymalna" if real_utilization <= 85.0 else "⚠️ Przeciążenie (>85%)"
                if v_tank_user < 5.0:
                    status_txt = "❌ Poniżej minimum fabryki (<5 m³)"

                final_fleet_rows.append({
                    "ID Urządzenia 🔒": tag_id,
                    "Przypisana Linia 🔒": kat,
                    "Pojemność geometryczna [m³] 🔒": round(v_tank_user, 1),
                    "Stała Masa Szarży [kg] 🔒": int(mass_per_batch),
                    "Liczba szarż [/mies per aparat] 🔒": int(batches_per_tank),
                    "Realna Utylizacja Czasowa 🔒": round(real_utilization, 1),
                    "Status Operacyjny 🔒": status_txt
                })
                
                confirmed_mixers_blueprint.append({
                    "tag": tag_id, "product_family": kat, "capacity_m3": v_tank_user,
                    "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": batches_per_tank,
                    "mass_per_batch": int(mass_per_batch), "annual_volume": annual_per_tank
                })
                
                total_batches_per_month_global += batches_per_tank
                total_volume_global += v_tank_user
                
            total_annual_production += m_annual
            tag_counter += 1

        df_final_fleet = pd.DataFrame(final_fleet_rows)
        st.dataframe(
            df_final_fleet, hide_index=True, width="stretch",
            column_config={
                "Realna Utylizacja Czasowa 🔒": st.column_config.NumberColumn(format="%.1f%%"),
                "Pojemność geometryczna [m³] 🔒": st.column_config.NumberColumn(format="%.1f m³"),
                "Stała Masa Szarży [kg] 🔒": st.column_config.NumberColumn(format="%d kg")
            }
        )

        st.markdown("<br>", unsafe_allow_html=True)
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        with sum_col1: st.metric(label="📈 Sumaryczny tonaż roczny zakładu", value=f"{total_annual_production:,} kg")
        with sum_col2: st.metric(label="🔄 Suma szarż floty / miesiąc", value=f"{total_batches_per_month_global} szarż")
        with sum_col3: st.metric(label="📐 Całkowita kubatura floty mieszalników", value=f"{total_volume_global:.1f} m³")
            
        st.markdown("---")
        if st.button("📥 Zatwierdź i wyślij konfigurację do kolejnych kroków", type="primary", use_container_width=True):
            st.session_state.confirmed_mixers = confirmed_mixers_blueprint
            if "master_logistics_df" in st.session_state:
                del st.session_state["master_logistics_df"]
            st.success(f"🎉 Sukces! Flota złożona z {len(confirmed_mixers_blueprint)} urządzeń została stabilnie zablokowana i przekazana do dalszych analiz.")

# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA MASZYN & REOLOGIA
# ==========================================
with tab2:
    st.header("📐 Specyfikacja Maszyn, Reologii i Dynamicznej Termodynamiki")

    if not st.session_state.confirmed_mixers:
        st.info("💡 Aby wygenerować specyfikację, najpierw zatwierdź konfigurację floty w **Zakładce 1**.")
    else:
        mixers_fleet = st.session_state.confirmed_mixers
        spec_rows = []
        if "pump_flows" not in st.session_state: st.session_state.pump_flows = {}
        A_BASE = 17.0

        for m in mixers_fleet:
            tag = m["tag"]
            kat = m["product_family"]
            v_working = m["capacity_m3"]
            mass_batch_kg = m["mass_per_batch"]
            cyc_h = FUCHS_PORTFOLIO[kat]["cycle_h"]
            rho_product = FUCHS_PORTFOLIO[kat]["density"] * 1000.0
            c_p_default = float(FUCHS_PORTFOLIO[kat]["cp"])
            default_mat = FUCHS_PORTFOLIO[kat]["material"]

            with st.expander(f"🔮 Dedykowany Konfigurator Instancji: {tag} ({kat})", expanded=True):
                sub_t1, sub_t2, sub_t3 = st.tabs(["🔥❄️ 1. Układ Termiczny", "⚙️ 2. Kinematyka Mieszadła", "🔄 3. Układ Pompowy"])
                
                with sub_t1:
                    c_h1, c_h2 = st.columns(2)
                    with c_h1: mat_reaktora = st.selectbox("Materiał korpusu:", ["Stal węglowa", "Stal nierdzewna"], index=0 if "zwykła" in default_mat else 1, key=f"mat_{tag}")
                    with c_h2: v_flow_l_min = st.number_input("Przepływ nośników [l/min]:", min_value=10.0, value=410.0, key=f"vflow_{tag}")
                    medium_term = st.selectbox("Nośnik grzewczy:", ["Para wodna", "Olej termalny", "Gorąca woda"], key=f"medg_{tag}")
                    T1_init = st.number_input("Temp. początkowa [°C]:", value=20.0, key=f"t1_{tag}")
                    T2_final = st.number_input("Temp. procesu MAX [°C]:", value=70.0, key=f"t2_{tag}")
                    t_in_carrier = st.number_input("Temp. nośnika grz. [°C]:", value=120.0, key=f"t_car_{tag}")
                    medium_chl = st.selectbox("Nośnik chłodzący:", ["Brak (Zrzut na gorąco)", "Woda z wieży (ok. 20°C)", "Woda z chillera (ok. 7°C)"], key=f"medc_{tag}")
                    T3_rozlew = st.number_input("Temp. rozlewu [°C]:", value=40.0, key=f"t3_{tag}", disabled=(medium_chl=="Brak (Zrzut na gorąco)"))
                    t_in_chl = st.number_input("Temp. nośnika chł. [°C]:", value=15.0, key=f"tinc_{tag}", disabled=(medium_chl=="Brak (Zrzut na gorąco)"))

                with sub_t2:
                    typ_wirnika = st.selectbox("Geometria wirnika:", list(AGITATOR_TYPES.keys()), index=1, key=f"agit_type_{tag}")
                    obroty_rpm = st.number_input("Obroty [RPM]:", min_value=10, value=90, key=f"rpm_{tag}")
                    motor_efficiency = st.slider("Sprawność napędu [%]:", min_value=50, max_value=98, value=85, key=f"eff_mot_{tag}")

                with sub_t3:
                    q_user_m3_h = st.number_input("Wydajność Q [m³/h]:", min_value=1.0, value=max(1.0, float(round(v_working / 0.75, 1))), key=f"qp_{tag}")
                    pipe_l_m = st.number_input("Długość rury L [m]:", min_value=1.0, value=15.0, key=f"pl_{tag}")
                    pipe_d_mm = st.number_input("Średnica wewn. D [mm]:", min_value=25, value=80, key=f"pd_{tag}")
                    visc_max_cst = st.number_input("Lepkość MAX [cSt]:", min_value=10.0, value=800.0, key=f"vmax_{tag}")
                    h_static_m = st.number_input("Wysokość H_stat [m]:", value=3.0, key=f"ph_{tag}")
                    visc_min_cst = st.number_input("Lepkość MIN [cSt]:", min_value=1.0, value=100.0, key=f"vmin_{tag}")

            # --- OBLICZENIA CIEPLNE ---
            st.session_state.pump_flows[tag] = q_user_m3_h
            scaled_area_m2 = A_BASE * ((v_working / 10.0) ** (2/3))
            k_base_grz = 0.55 if "Para" in medium_term else 0.40 if "nierdzewna" in mat_reaktora else 0.60
            w_cap_grz = ((v_flow_l_min / 60.0) * 1.0) * 4.2
            
            if (t_in_carrier > T1_init and t_in_carrier > T2_final) and w_cap_grz > 0:
                ntu_g = (k_base_grz * scaled_area_m2) / w_cap_grz
                eff_g = (1.0 - math.exp(-ntu_g)) / ntu_g if ntu_g > 0 else 1.0
                Q_grz_kwh = (mass_batch_kg * c_p_default * abs(T2_final - T1_init)) / 3600.0
                power_grz_kw = k_base_grz * scaled_area_m2 * abs(t_in_carrier - T1_init) * eff_g
                tau_grz = Q_grz_kwh / power_grz_kw if power_grz_kw > 0 else 0.0
            else: Q_grz_kwh, tau_grz = 0.0, 0.0

            if medium_chl != "Brak (Zrzut na gorąco)" and T2_final > T3_rozlew:
                k_base_chl = 0.45 if "nierdzewna" in mat_reaktora else 0.75
                w_cap_chl = ((v_flow_l_min / 60.0) * 1.0) * 4.184
                ntu_c = (k_base_chl * scaled_area_m2) / w_cap_chl
                eff_c = (1.0 - math.exp(-ntu_c)) / ntu_c if ntu_c > 0 else 1.0
                Q_chl_kwh = (mass_batch_kg * c_p_default * abs(T2_final - T3_rozlew)) / 3600.0
                power_chl_kw = k_base_chl * scaled_area_m2 * abs(T2_final - t_in_chl) * eff_c
                tau_chl = Q_chl_kwh / power_chl_kw if power_chl_kw > 0 else 0.0
            else: Q_chl_kwh, tau_chl = 0.0, 0.0

            total_thermal_time = tau_grz + tau_chl

            # --- OBLICZENIA HYDRODYNAMIKI ---
            visc_avg_pas = ((visc_max_cst + visc_min_cst) / 2.0 / 1_000_000.0) * rho_product
            D_vessel = 2.2 * ((v_working / 10.0) ** (1/3))
            d_impeller = D_vessel / 3.0
            Re_mixing = ((obroty_rpm / 60.0) * (d_impeller ** 2) * rho_product) / max(visc_avg_pas, 0.0001)
            Ne_power = AGITATOR_TYPES[typ_wirnika]["laminar_C"] / Re_mixing if Re_mixing < 50 else AGITATOR_TYPES[typ_wirnika]["turbulent_Ne"]
            power_shaft_w = Ne_power * ((obroty_rpm / 60.0) ** 3) * (d_impeller ** 5) * rho_product
            power_mix_kw = max((power_shaft_w / (motor_efficiency / 100.0) * 1.25) / 1000.0, 1.5)

            # --- OBLICZENIA POMPY ---
            D_pipe_m = pipe_d_mm / 1000.0
            velocity_m_s = (q_user_m3_h / 3600.0) / ((math.pi * (D_pipe_m ** 2)) / 4.0)
            Re_pipe_max = (velocity_m_s * D_pipe_m) / max(visc_max_cst / 1_000_000.0, 0.00001)
            lambda_max = 64.0 / max(Re_pipe_max, 1.0) if Re_pipe_max < 2100 else (0.3164 / (Re_pipe_max ** 0.25))
            press_bar_max = (rho_product * 9.81 * (h_static_m + (lambda_max * (pipe_l_m / D_pipe_m) * ((velocity_m_s ** 2) / (2.0 * 9.81))))) / 100000.0
            power_pump_kw = max((q_user_m3_h * press_bar_max) / (36.0 * 0.65) * 1.25, 0.75)
            time_pumping_h = v_working / q_user_m3_h

            st.session_state.calculated_times[tag] = {
                "heating": total_thermal_time, "pumping": time_pumping_h,
                "power_mix_kw": power_mix_kw, "power_pump_kw": power_pump_kw,
                "t_max_mix": T2_final, "t_rozlew": T3_rozlew if medium_chl != "Brak (Zrzut na gorąco)" else T2_final
            }

            spec_rows.append({
                "Nazwa 🔒": tag, "Pojemność [m³]": round(v_working, 1),
                "Grzanie [kWh] 🔥": int(Q_grz_kwh), "Chłodzenie [kWh] ❄️": int(Q_chl_kwh),
                "Czas Termiki [h] ⏱️": round(total_thermal_time, 2), "Mieszanie [kW] ⚙️": round(power_mix_kw, 1),
                "Ciśnienie MAX [bar]": round(press_bar_max, 1), "Moc Pompy [kW] ⚡": round(power_pump_kw, 1),
                "Prędkość cieczy [m/s]": round(velocity_m_s, 2), "Status pompy": "❌ Za wysoka prędk." if velocity_m_s > 2.0 else "✅ OK"
            })

        st.markdown("### 📊 Zbiorcza Karta Specyfikacji Technicznej")
        st.dataframe(pd.DataFrame(spec_rows), hide_index=True, width="stretch")

# ==========================================
# ZAKŁADKA 3: LOGISTYKA I SPECYFIKA ROZLEWU
# ==========================================
with tab3:
    st.header("📦 Analiza Logistyczna, Czas Rozlewu i Gospodarka Paletowa")
    if not st.session_state.confirmed_mixers:
        st.info("💡 Najpierw zatwierdź konfigurację floty w **Zakładce 1**.")
    else:
        mixers_fleet = st.session_state.confirmed_mixers
        opakowania_podzial = st.session_state.get("opakowania_podzial", {})
        
        tonaz_miesieczny_per_rodzina = {}
        for m in mixers_fleet:
            kat = m["product_family"]
            tonaz_miesieczny_per_rodzina[kat] = tonaz_miesieczny_per_rodzina.get(kat, 0) + (m["batches_count"] * m["mass_per_batch"])

        aktywne_opakowania = set()
        for kat in wybrane_kategorie:
            for p in st.session_state.get(f"packs_{kat}", []): aktywne_opakowania.add(p)
        if not aktywne_opakowania: aktywne_opakowania = set(PACK_CONFIGS.keys())

        if "filling_lines_config" not in st.session_state: st.session_state.filling_lines_config = {}
        for p in aktywne_opakowania:
            if p not in st.session_state.filling_lines_config:
                st.session_state.filling_lines_config[p] = {"nozzles": 4, "speed_kg_min": 15.0} if "5l" in p.lower() or "1l" in p.lower() else {"nozzles": 1, "speed_kg_min": 60.0}

        filling_table_rows = []
        for p in aktywne_opakowania:
            cfg = st.session_state.filling_lines_config[p]
            filling_table_rows.append({
                "Typ Opakowania 🔒": p, "Liczba głowic nalewaka [szt] 🟦": int(cfg["nozzles"]), "Wydajność 1 głowicy [kg/min] 🟦": float(cfg["speed_kg_min"])
            })

        st.markdown("##### Konfiguracja Sekcji Głowic Rozlewniczych")
        st.data_editor(pd.DataFrame(filling_table_rows), hide_index=True, width="stretch", disabled=["Typ Opakowania 🔒"], key="filling_editor")

        czas_skladowania_dni = st.number_input("Czas składowania palety (Rotacja) [dni]:", min_value=1, value=14)
        dni_robocze_miesiac = 250.0 / 12.0

        real_split_rows = []
        for kat, total_mass_month in tonaz_miesieczny_per_rodzina.items():
            rho_linii = FUCHS_PORTFOLIO[kat]["density"]
            for p in st.session_state.get(f"packs_{kat}", []):
                udzial_pct = opakowania_podzial.get(f"pct_{kat}_{p}", 0.0)
                if udzial_pct > 0:
                    masa_opakowania_month = total_mass_month * (udzial_pct / 100.0)
                    pack_capacity_kg = PACK_CONFIGS[p]["size_l"] * rho_linii
                    liczba_sztuk_month = math.ceil(masa_opakowania_month / pack_capacity_kg) if pack_capacity_kg > 0 else 0
                    
                    cfg_fill = st.session_state.filling_lines_config.get(p, {"nozzles": 1, "speed_kg_min": 30.0})
                    sekcja_nalewania_m3_h = (cfg_fill["nozzles"] * cfg_fill["speed_kg_min"] * 60.0) / (rho_linii * 1000.0)
                    m_parent = next((mx for mx in mixers_fleet if mx["product_family"] == kat), None)
                    q_pump_m3h = st.session_state.get("pump_flows", {}).get(m_parent["tag"], 15.0) if m_parent else 15.0

                    q_effective_flow_m3h = min(q_pump_m3h, sekcja_nalewania_m3_h)
                    czas_rozlewu_h = (masa_opakowania_month / (rho_linii * 1000.0)) / q_effective_flow_m3h if q_effective_flow_m3h > 0 else 0.0
                    liczba_palet_month = math.ceil(liczba_sztuk_month / PACK_CONFIGS[p]["per_pallet"])
                    miejsca_paletowe = math.ceil((liczba_palet_month / dni_robocze_miesiac) * czas_skladowania_dni)

                    real_split_rows.append({
                        "Linia 🔒": kat, "Opakowanie 📦": p, "Udział": f"{udzial_pct:.1f}%",
                        "Opakowań [/mies]": int(liczba_sztuk_month), "Palet [/mies] 🧱": int(liczba_palet_month),
                        "Miejsca magazynowe [szt] 📐": int(miejsca_paletowe), "Czas rozlewu strumienia [h] ⏱️": round(czas_rozlewu_h, 1)
                    })

        if real_split_rows:
            st.markdown("##### 🔀 Wyniki Symulacji Logistyczno-Magazynowej")
            st.dataframe(pd.DataFrame(real_split_rows), hide_index=True, width="stretch")

# ==========================================
# ZAKŁADKA 4: ANALIZA FINANSOWA I KOSZTY
# ==========================================
with tab4:
    st.header("💰 Optymalizacja Kosztów Energii i Bilans Finansowy")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Najpierw zatwierdź flotę w Zakładce 1.")
    else:
        waluta = st.selectbox("Wybierz walutę operacyjną:", ["PLN", "EUR", "USD"])
        manuf_cost_per_kg = st.number_input(f"Bazowy Manufacturing Cost [za kg] w {waluta}:", min_value=0.01, value=2.12, format="%.3f")
        cena_mwh = st.number_input(f"Cena energii elektrycznej i cieplnej [{waluta}/MWh]:", min_value=1.0, value=750.0)
        
        financial_summary = []
        total_monthly_saving_thermal = 0.0
        total_base_manuf_cost = 0.0
        total_energy_cost_el = 0.0
        calculated_times = st.session_state.get("calculated_times", {})

        for mixer in st.session_state.confirmed_mixers:
            tag = mixer["tag"]
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            m_monthly_kg = mixer["annual_volume"] / 12
            batches_per_month = mixer["batches_count"]
            
            m_data = calculated_times.get(tag, {"power_mix_kw": 5.5, "power_pump_kw": 1.5, "heating": 1.5, "pumping": 0.75, "t_max_mix": 60.0, "t_rozlew": 30.0})
            
            mixing_energy = m_data["power_mix_kw"] * prod_info["cycle_h"] * batches_per_month
            pumping_energy = m_data["power_pump_kw"] * m_data["pumping"] * batches_per_month
            cost_el = ((mixing_energy + pumping_energy) / 1000.0) * cena_mwh
            total_energy_cost_el += cost_el

            base_manuf_cost_monthly = m_monthly_kg * manuf_cost_per_kg
            total_base_manuf_cost += base_manuf_cost_monthly
            
            oszczednosc_cieplna = 0.0
            if m_data["t_rozlew"] < m_data["t_max_mix"]:
                oszczednosc_cieplna = ((m_monthly_kg * prod_info["cp"] * (m_data["t_max_mix"] - m_data["t_rozlew"])) / 3_600_000.0) * cena_mwh
                total_monthly_saving_thermal += oszczednosc_cieplna
                
            financial_summary.append({
                "Reaktor": tag, "Miesięczny tonaż [kg]": int(m_monthly_kg),
                "Energia Mieszania [kWh]": round(mixing_energy, 1), "Energia Pompowania [kWh]": round(pumping_energy, 1),
                "Koszt prądu": f"{cost_el:.2f} {waluta}", "Odzysk ciepła": f"- {oszczednosc_cieplna:.2f} {waluta}"
            })
            
        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, width="stretch")
        final_cost = total_base_manuf_cost + total_energy_cost_el - total_monthly_saving_thermal
        st.metric(label="🚀 ZOPTYMALIZOWANY REALNY KOSZT WYTWORZENIA (Miesięcznie)", value=f"{final_cost:,.2f} {waluta}")

        st.markdown("### ⏱️ 2. Pełna Analiza Czasu Cyklu Szarży")
        time_analysis_rows = []
        for mixer in st.session_state.confirmed_mixers:
            tag = mixer["tag"]
            kat = mixer["product_family"]
            m_data = calculated_times.get(tag, {"heating": 1.5, "pumping": 0.75})
            
            with st.expander(f"⏱️ Składniki czasu operacyjnego dla: {tag}", expanded=False):
                t_dosing = st.number_input("Dozowanie surowców [h]:", min_value=0.1, value=1.0, key=f"tdos_{tag}")
                t_homog = st.number_input("Homogenizacja właściwa [h]:", min_value=0.1, value=2.0, key=f"thom_{tag}")
                t_qc = st.number_input("Zwolnienie laboratoryjne QC [h]:", min_value=0.1, value=1.0, key=f"tqc_{tag}")

            t_total_chain = t_dosing + m_data["heating"] + t_homog + t_qc + m_data["pumping"]
            time_analysis_rows.append({
                "ID Mieszalnika": tag, "Linia": kat, "Pełny łańcuch szarży [h]": round(t_total_chain, 2),
                "Rekomendacja operacyjna": "🟢 Dwuzmianowa (Cykl <= 8h)" if t_total_chain <= 8.0 else "🔴 Jednozmianowa (Wymagany nadzór nocny)"
            })
        st.dataframe(pd.DataFrame(time_analysis_rows), hide_index=True, width="stretch")

# ==========================================
# ZAKŁADKA 5: PARK ZBIORNIKÓW (TANK FARM)
# ==========================================
with tab5:
    st.header("🛢️ Logistyka Surowcowa i Grupy Magazynowe (Tank Farm)")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych technicznych. Uruchom konfigurację w Zakładce 1.")
    else:
        active_chemical_ratio = st.slider("Średni udział fazy ciekłej (baza + woda) w recepturze [%]:", 50, 95, 85) / 100.0
        days_of_stock = st.number_input("Wymagany zapas bezpieczeństwa surowca [dni]:", min_value=5, value=14)
        
        raw_material_summary = []
        silos_aggregation = {"Mineralne (Gr. I/II)": 0.0, "Syntetyczne (Gr. III/IV)": 0.0, "Woda Procesowa DEMI": 0.0, "Inne / Pakiety płynne": 0.0}
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            total_liquid_tony = (mixer["annual_volume"] / 1000.0) * active_chemical_ratio
            
            water_annual = total_liquid_tony * prod_info["water_content"]
            oil_annual = total_liquid_tony * (1.0 - prod_info["water_content"]) if prod_info["oil_group"] != "Brak (Specjalistyczne)" else 0.0
            other_liquid = total_liquid_tony - water_annual - oil_annual
            
            silos_aggregation["Woda Procesowa DEMI"] += water_annual
            if oil_annual > 0: silos_aggregation[prod_info["oil_group"]] += oil_annual
            silos_aggregation["Inne / Pakiety płynne"] += other_liquid

            raw_material_summary.append({
                "ID Reaktora 🔒": mixer["tag"], "Linia 🔒": kat, "Typ Bazy": prod_info["oil_group"],
                "Produkcja [t/rok]": round(mixer["annual_volume"]/1000.0, 1), "Baza Olejowa [t/rok]": round(oil_annual, 1), "Woda DEMI [t/rok]": round(water_annual, 1)
            })
            
        st.dataframe(pd.DataFrame(raw_material_summary), hide_index=True, use_container_width=True)
        
        st.markdown("### 🏢 Wymiarowanie Silosów Magazynowych")
        selected_tank_capacity_m3 = st.selectbox("Wybierz pojemność pojedynczego silosu [m³]:", [30, 50, 60, 80, 100, 150, 200], index=4)
        
        silos_rows = []
        total_tanks = 0
        for group_name, annual_tony in silos_aggregation.items():
            if annual_tony > 0:
                daily_t = annual_tony / 250.0
                required_m3 = (daily_t * days_of_stock) / (1.00 if "Woda" in group_name else 0.88)
                needed_tanks = math.ceil(required_m3 / (selected_tank_capacity_m3 * 0.85))
                total_tanks += needed_tanks
                silos_rows.append({
                    "Grupa Surowcowa": group_name, "Konsumpcja [t/rok]": round(annual_tony, 1), "Wymagany Bufor [m³]": round(required_m3, 1), "Liczba silosów": f"{needed_tanks} szt."
                })
        st.dataframe(pd.DataFrame(silos_rows), hide_index=True, use_container_width=True)
        st.metric("🧱 Całkowita wymagana liczba silosów surowcowych", f"{total_tanks} szt.")
