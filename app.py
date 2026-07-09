import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Kompletna Platforma Wymiarowania Linii, Reologii, Logistyki i Surowców")
st.markdown("---")

# --- 1. BAZA DANYCH PROCESOWYCH I FIZYKOCHEMICZNYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Hydraulic Oils (RENOLIN)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0},
    "Gear & Turbine Oils (RENOLIN)": {"material": "Stal zwykła", "density": 0.89, "cycle_h": 5, "cp": 1.9},
    "Slideway & Machine Oils (RENAX)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 4, "cp": 2.0},
    "Engine Oils (TITAN)": {"material": "Stal zwykła", "density": 0.87, "cycle_h": 5, "cp": 2.1},
    "Gear & Transmission Oils (TITAN)": {"material": "Stal zwykła", "density": 0.88, "cycle_h": 5, "cp": 2.0},
    "Water-miscible (ECOCOOL)": {"material": "Stal nierdzewna", "density": 0.99, "cycle_h": 6, "cp": 3.8},
    "Non-water-miscible (ECOCUT)": {"material": "Stal zwykła", "density": 0.87, "cycle_h": 4, "cp": 2.0},
    "Cleaners (RENOCLEAN)": {"material": "Stal nierdzewna", "density": 1.01, "cycle_h": 4, "cp": 3.9}
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

# --- BEZPIECZNA INICJALIZACJA STRUKTUR W SESJI ---
if "prod_dict" not in st.session_state:
    st.session_state.prod_dict = {
        k: {"roczna": 1200000, "utilization": 75.0} for k in FUCHS_PORTFOLIO.keys()
    }

if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

# Definiowanie domyślnych wartości struktur temperatur
if "heat_temps" not in st.session_state:
    st.session_state.heat_temps = {f"MT-{i}": 60.0 for i in range(101, 120)}
    for i in range(101, 120):
        st.session_state.heat_temps[f"MT-{i}A"] = 60.0
        st.session_state.heat_temps[f"MT-{i}B"] = 60.0

if "filling_temps" not in st.session_state:
    st.session_state.filling_temps = {f"MT-{i}": 30.0 for i in range(101, 120)}
    for i in range(101, 120):
        st.session_state.filling_temps[f"MT-{i}A"] = 30.0
        st.session_state.filling_temps[f"MT-{i}B"] = 30.0

# --- FUNKCJA CALLBACK BEZ ZALEŻNOŚCI OD ZMIENNYCH LOKALNYCH ---
def sync_production_data():
    if "main_production_editor" in st.session_state:
        edits = st.session_state.main_production_editor.get("edited_rows", {})
        active_families = [k for k in FUCHS_PORTFOLIO.keys() if k in wybrane_kategorie]
        for idx, changes in edits.items():
            if idx < len(active_families):
                family_name = active_families[idx]
                if "2. Roczna produkcja [kg] 🟦" in changes:
                    st.session_state.prod_dict[family_name]["roczna"] = changes["2. Roczna produkcja [kg] 🟦"]
                if "3. Utilization % 🟦" in changes:
                    st.session_state.prod_dict[family_name]["utilization"] = changes["3. Utilization % 🟦"]

# --- STRUKTURA PIĘCIU KART INTERFEJSU ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 1. Główne Zestawienie i Utylizacja", 
    "📐 2. Karta Maszyn i Dobór Pomp", 
    "📦 3. Logistyka i Czas Rozlewu",
    "💰 4. Analiza Finansowa i Koszty Produkcji",
    "🛢️ 5. Surowce i Park Zbiorników"
])

# ==========================================
# ZAKŁADKA 1: POWRÓT DO STANDARDU + SKUs + PODZIAŁ NA ZBIORNIKI + WALIDACJA TYPOSZEREGU
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych (Baza: {godziny_dziennie:.1f}h/dzień)")
    
    # Definicja dopuszczalnego typoszeregu pojemności mikserów
    TYPOSZEREG_MIKSEROW = [5, 7, 10, 15, 18, 21, 25, 31]
    
    if wybrane_kategorie:
        # Inicjalizacja struktur w session_state (zachowanie edycji użytkownika)
        for kat in wybrane_kategorie:
            if kat not in st.session_state.prod_dict:
                st.session_state.prod_dict[kat] = {"roczna": 1200000, "utilization": 75.0, "skus": 1, "num_tanks": 1}
            if "skus" not in st.session_state.prod_dict[kat]:
                st.session_state.prod_dict[kat]["skus"] = 1
            if "num_tanks" not in st.session_state.prod_dict[kat]:
                st.session_state.prod_dict[kat]["num_tanks"] = 1

        # Funkcja synchronizacji po edycji tabeli st.data_editor
        def sync_tab1_data():
            if "tab1_editor" in st.session_state:
                edits = st.session_state.tab1_editor.get("edited_rows", {})
                active_families = [k for k in FUCHS_PORTFOLIO.keys() if k in wybrane_kategorie]
                for idx, changes in edits.items():
                    if idx < len(active_families):
                        family_name = active_families[idx]
                        if "2. Roczna produkcja [kg] 🟦" in changes:
                            st.session_state.prod_dict[family_name]["roczna"] = changes["2. Roczna produkcja [kg] 🟦"]
                        if "3. Docelowa Utylizacja [%] 🟦" in changes:
                            st.session_state.prod_dict[family_name]["utilization"] = float(changes["3. Docelowa Utylizacja [%] 🟦"])
                        if "4. Liczba SKUs 🟦" in changes:
                            st.session_state.prod_dict[family_name]["skus"] = int(changes["4. Liczba SKUs 🟦"])

        calculated_matrix_rows = []
        oversized_reactors = {}

        # Przetwarzanie matematyczne każdej rodziny produktowej
        for kat in wybrane_kategorie:
            m_annual = st.session_state.prod_dict[kat]["roczna"]
            util_target = st.session_state.prod_dict[kat]["utilization"]
            skus = st.session_state.prod_dict[kat]["skus"]
            
            dens = FUCHS_PORTFOLIO[kat]["density"]
            cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            m_monthly = m_annual / 12
            allocated_hours = AVAILABLE_HOURS_MONTH * (util_target / 100.0)
            
            # Wyznaczenie liczby szarż i gabarytu
            needed_batches = math.ceil(allocated_hours / cyc) if allocated_hours > 0 else 1
            batch_size_kg = math.ceil(m_monthly / needed_batches) if needed_batches > 0 else 0
            calculated_vol_m3 = batch_size_kg / (dens * 1000.0) if batch_size_kg > 0 else 0.0

            # Dopasowanie do najbliższego wyższego typoszeregu mikserów
            sug_vol = 0
            for v in TYPOSZEREG_MIKSEROW:
                if v >= calculated_vol_m3:
                    sug_vol = v
                    break
            if sug_vol == 0 and calculated_vol_m3 > 0:
                sug_vol = 31  # Limit górny konstrukcji

            if calculated_vol_m3 > 31.0:
                oversized_reactors[kat] = calculated_vol_m3

            calculated_matrix_rows.append({
                "1. Nazwa rodziny 🔒": kat,
                "2. Roczna produkcja [kg] 🟦": int(m_annual),
                "3. Docelowa Utylizacja [%] 🟦": float(util_target),
                "4. Liczba SKUs 🟦": int(skus),
                "5. Wyliczony gabaryt reaktora 🔒": round(calculated_vol_m3, 2),
                "6. Sugerowany Mikser (Typoszereg) 🔒": f"{sug_vol} m³" if sug_vol > 0 else "Poniżej minimum (<5 m³)",
                "h_vol": calculated_vol_m3, "h_batches": needed_batches, "h_kg": batch_size_kg, "h_annual": m_annual
            })

        df_complete_matrix = pd.DataFrame(calculated_matrix_rows)

        st.markdown("##### 📥 Krok A: Parametryzacja Tonażu, Utylizacji oraz SKUs")
        
        # Funkcja podświetlająca komórki, gdzie gabaryt jest mniejszy niż 5 m³
        def style_small_volumes(row):
            styles = [''] * len(row)
            val = row["5. Wyliczony gabaryt reaktora 🔒"]
            if isinstance(val, (int, float)) and val < 5.0:
                idx = row.index.get_loc("5. Wyliczony gabaryt reaktora 🔒")
                styles[idx] = 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
            return styles

        styled_matrix = df_complete_matrix.style.apply(style_small_volumes, axis=1)

        # Wyświetlenie tabeli edytowalnej
        edited_table = st.data_editor(
            styled_matrix,
            hide_index=True,
            use_container_width=True,
            disabled=["1. Nazwa rodziny 🔒", "5. Wyliczony gabaryt reaktora 🔒", "6. Sugerowany Mikser (Typoszereg) 🔒"],
            column_config={
                "2. Roczna produkcja [kg] 🟦": st.column_config.NumberColumn(min_value=0, step=50000, format="%d"),
                "3. Docelowa Utylizacja [%] 🟦": st.column_config.NumberColumn(min_value=1.0, max_value=100.0, step=5.0, format="%.1f%%"),
                "4. Liczba SKUs 🟦": st.column_config.NumberColumn(min_value=1, step=1),
                "5. Wyliczony gabaryt reaktora 🔒": st.column_config.NumberColumn(format="%.2f m³"),
                "h_vol": None, "h_batches": None, "h_kg": None, "h_annual": None
            },
            key="tab1_editor",
            on_change=sync_tab1_data
        )

        # Krok B: Dynamiczne pytania o przydział fizycznych zbiorników dla rodzin posiadających SKUs > 1
        st.markdown("<br>", unsafe_allow_html=True)
        any_sku_trigger = False
        for kat in wybrane_kategorie:
            current_skus = st.session_state.prod_dict[kat]["skus"]
            if current_skus > 1:
                if not any_sku_trigger:
                    st.markdown("##### 🛢️ Krok B: Przydział zbiorników dla rodzin z wieloma SKUs")
                    any_sku_trigger = True
                
                # Ograniczamy maksymalną liczbę zbiorników do liczby posiadanych SKUs
                st.session_state.prod_dict[kat]["num_tanks"] = st.number_input(
                    f"Wykryto **{current_skus} SKUs** dla linii **{kat}**. Do ilu osobnych zbiorników przypisać tę rodzinę?",
                    min_value=1,
                    max_value=int(current_skus),
                    value=min(int(st.session_state.prod_dict[kat].get("num_tanks", 1)), int(current_skus)),
                    key=f"tanks_input_{kat}"
                )

        # Krok C: Obsługa sytuacji awaryjnej (przekroczenie gabarytu transportowego 31 m³)
        split_decisions = {}
        if oversized_reactors:
            st.warning("⚠️ **Wykryto przekroczenie dopuszczalnych gabarytów transportowych pojedynczego zbiornika (> 31 m³)!**")
            chk_cols = st.columns(len(oversized_reactors))
            for idx, (kat_over, vol_over) in enumerate(oversized_reactors.items()):
                with chk_cols[idx]:
                    split_decisions[kat_over] = st.checkbox(
                        f"Rozbij reaktor {kat_over} ({vol_over:.1f} m³) na mniejsze jednostki?",
                        value=True, key=f"chk_split_{kat_over}"
                    )

        # Krok D: Generowanie Końcowej Floty Mieszalników
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🏭 3. Skorygowana i Zweryfikowana Flota Mieszalników")
        
        final_fleet_rows = []
        total_annual_production = 0
        total_batches_per_month = 0
        total_calculated_volume_m3 = 0.0
        confirmed_mixers_blueprint = []
        tag_counter = 101

        for idx, r in df_complete_matrix.iterrows():
            kat = r["1. Nazwa rodziny 🔒"]
            vol_base = r["h_vol"]
            total_batches = r["h_batches"]
            total_annual = r["h_annual"]
            
            # Pobieramy zdefiniowaną przez użytkownika liczbę fizycznych zbiorników wynikającą z SKUs
            tanks_count = st.session_state.prod_dict[kat]["num_tanks"]
            
            # Dzielimy parametry bazowe rodziny na liczbę dedykowanych maszyn
            vol_per_tank = vol_base / tanks_count if tanks_count > 0 else vol_base
            batches_per_tank = math.ceil(total_batches / tanks_count) if tanks_count > 0 else total_batches
            annual_per_tank = total_annual / tanks_count

            # Jeśli nawet po podziale na SKUs zbiornik przekracza 31m³, wykonujemy rozbicie technologiczne
            if split_decisions.get(kat, False) and vol_per_tank > 31.0:
                remaining_vol = vol_per_tank
                sub_letter_ascii = 65 
                while remaining_vol > 62.0:
                    weight_fraction = 31.0 / vol_per_tank
                    mixer_annual = annual_per_tank * weight_fraction
                    mixer_batches = math.ceil(batches_per_tank * weight_fraction)
                    mixer_mass_batch = math.ceil((r["h_kg"]/tanks_count) * (31.0 / vol_per_tank))
                    
                    for t_idx in range(tanks_count):
                        tag_id = f"MT-{tag_counter}{chr(sub_letter_ascii)}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                        final_fleet_rows.append({
                            "ID Urządzenia 🔒": tag_id, "Przypisana Linia 🔒": kat,
                            "Liczba szarż [/mies] 🔒": int(mixer_batches), "Realna Pojemność [m³] 🔒": 31.0,
                            "Masa Szarży [kg] 🔒": int(mixer_mass_batch), "Status 🔒": "🧱 Max Gabaryt (31.0 m³)"
                        })
                        confirmed_mixers_blueprint.append({
                            "tag": tag_id, "product_family": kat, "capacity_m3": 31.0,
                            "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": mixer_batches,
                            "mass_per_batch": mixer_mass_batch, "annual_volume": mixer_annual
                        })
                        total_calculated_volume_m3 += 31.0
                        total_batches_per_month += mixer_batches
                    
                    remaining_vol -= 31.0
                    sub_letter_ascii += 1
                
                if remaining_vol > 0:
                    split_tail_vol = remaining_vol / 2.0
                    weight_fraction_tail = split_tail_vol / vol_per_tank
                    tail_annual = annual_per_tank * weight_fraction_tail
                    tail_batches = math.ceil(batches_per_tank * weight_fraction_tail)
                    tail_mass_batch = math.ceil((r["h_kg"]/tanks_count) * (split_tail_vol / vol_per_tank))
                    
                    for t_idx in range(tanks_count):
                        for _ in range(2):
                            tag_id = f"MT-{tag_counter}{chr(sub_letter_ascii)}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                            final_fleet_rows.append({
                                "ID Urządzenia 🔒": tag_id, "Przypisana Linia 🔒": kat,
                                "Liczba szarż [/mies] 🔒": int(tail_batches), "Realna Pojemność [m³] 🔒": round(split_tail_vol, 1),
                                "Masa Szarży [kg] 🔒": int(tail_mass_batch), "Status 🔒": "🟢 Bliźniak Konstrukcyjny"
                            })
                            confirmed_mixers_blueprint.append({
                                "tag": tag_id, "product_family": kat, "capacity_m3": max(split_tail_vol, 0.5),
                                "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": tail_batches,
                                "mass_per_batch": tail_mass_batch, "annual_volume": tail_annual
                            })
                            total_calculated_volume_m3 += split_tail_vol
                            total_batches_per_month += tail_batches
                            sub_letter_ascii += 1
            else:
                # Scenariusz standardowy (wielkość optymalna lub wynikająca bezpośrednio z podziału na zbiorniki SKUs)
                if vol_per_tank < 5.0:
                    status_txt = "⚠️ Poniżej minimum typoszeregu"
                elif vol_per_tank > 31.0:
                    status_txt = "🔴 Za duży (>31 m³)"
                else:
                    status_txt = "✅ Przydział SKUs" if tanks_count > 1 else "✅ Optymalny"
                
                for t_idx in range(tanks_count):
                    tag_id = f"MT-{tag_counter}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                    mass_batch = math.ceil(r["h_kg"] / tanks_count)
                    
                    final_fleet_rows.append({
                        "ID Urządzenia 🔒": tag_id, "Przypisana Linia 🔒": kat,
                        "Liczba szarż [/mies] 🔒": int(batches_per_tank), "Realna Pojemność [m³] 🔒": round(vol_per_tank, 1),
                        "Masa Szarży [kg] 🔒": int(mass_batch), "Status 🔒": status_txt
                    })
                    confirmed_mixers_blueprint.append({
                        "tag": tag_id, "product_family": kat, "capacity_m3": max(vol_per_tank, 0.5),
                        "material": FUCHS_PORTFOLIO[kat]["material"], "batches_count": batches_per_tank,
                        "mass_per_batch": mass_batch, "annual_volume": annual_per_tank
                    })
                    total_calculated_volume_m3 += vol_per_tank
                    total_batches_per_month += batches_per_tank

            total_annual_production += total_annual
            tag_counter += 1

        df_final_fleet = pd.DataFrame(final_fleet_rows)
        st.dataframe(
            df_final_fleet,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Realna Pojemność [m³] 🔒": st.column_config.NumberColumn(format="%.1f m³"),
                "Masa Szarży [kg] 🔒": st.column_config.NumberColumn(format="%d kg")
            }
        )

        # Podsumowania KPI na dole zakładki
        st.markdown("<br>", unsafe_allow_html=True)
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        with sum_col1: st.metric(label="📈 Sumaryczny tonaż roczny", value=f"{total_annual_production:,} kg")
        with sum_col2: st.metric(label="🔄 Całkowita liczba szarż / miesiąc", value=f"{total_batches_per_month} szarż")
        with sum_col3: st.metric(label="📐 Sumaryczna pojemność floty", value=f"{total_calculated_volume_m3:.1f} m³")
            
        st.markdown("---")
        if st.button("📥 Zatwierdź i wyślij konfigurację do kolejnych kroków", type="primary", use_container_width=True):
            st.session_state.confirmed_mixers = confirmed_mixers_blueprint
            if "master_logistics_df" in st.session_state:
                del st.session_state["master_logistics_df"]
            st.success(f"🎉 Sukces! Zapisano stabilną strukturę floty złożoną z {len(confirmed_mixers_blueprint)} urządzeń.")
# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA APARATURY I ANALIZA TERMICZNA (MODEL ANALITYCZNY)
# ==========================================
with tab2:
    st.header("📋 Specyfikacja Aparatury i Analiza Termodynamiczna")

    # Sprawdzenie dostępności danych z pierwszej zakładki
    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.info("💡 Aby wygenerować specyfikację aparatury, najpierw zatwierdź konfigurację floty w **Zakładce 1** (przycisk na dole strony).")
    else:
        st.markdown("### 🛠️ 1. Parametry Projektowe i Analityczny Model Wymiany Ciepła")
        st.caption("Wymiary konstrukcyjne skalowane automatycznie względem danych referencyjnych reaktora T5 (V_robocza = 10m³, A = 17m², Masa = 4118kg).")

        # --- DANE BAZOWE REAKTORA REFERENCYJNEGO (T5 DESIGN DATA) ---
        V_WORKING_BASE = 10.0
        V_TOTAL_BASE = 15.17
        A_BASE = 17.0
        W_BASE = 4118.0

        # --- SIDEBAR / PANEL KONTROLNY PARAMETRÓW CIEPLNYCH ---
        st.sidebar.markdown("### 🌡️ Parametry Procesu Termicznego")
        tryb_procesu = st.sidebar.selectbox("Tryb pracy termicznej", ["Grzanie wkładu", "Chłodzenie wkładu"])
        
        # Dynamiczne ustawienie domyślnych temperatur w zależności od wybranego procesu
        if tryb_procesu == "Grzanie wkładu":
            T1_init = st.sidebar.number_input("Początkowa temp. produktu (T1) [°C]", value=20.0, step=5.0)
            T2_final = st.sidebar.number_input("Docelowa temp. produktu (T2) [°C]", value=70.0, step=5.0)
            t1_carrier = st.sidebar.number_input("Temp. nośnika na wlocie (t1) [°C]", value=120.0, step=5.0)
            c_product = st.sidebar.number_input("Ciepło właściwe produktu (c) [kJ/(kg·K)]", value=2.00, step=0.1) # Domyślnie olej smarowy
        else: # Chłodzenie (odzwierciedlenie wartości z arkusza kalkulatora chłodzenia)
            T1_init = st.sidebar.number_input("Początkowa temp. produktu (T1) [°C]", value=80.0, step=5.0)
            T2_final = st.sidebar.number_input("Docelowa temp. produktu (T2) [°C]", value=40.0, step=5.0)
            t1_carrier = st.sidebar.number_input("Temp. wody chłodzącej na wlocie (t1) [°C]", value=15.0, step=5.0)
            c_product = st.sidebar.number_input("Ciepło właściwe produktu (c) [kJ/(kg·K)]", value=3.66, step=0.1)

        k_coefficient = st.sidebar.number_input("Współczynnik przenikania ciepła (k) [kW/(m²·K)]", value=0.80, step=0.05)
        v_flow_rate = st.sidebar.number_input("Strumień objętościowy nośnika [l/min]", value=410.0, step=10.0)
        c_carrier = st.sidebar.number_input("Ciepło właściwe nośnika (c_wody) [kJ/(kg·K)]", value=4.184, step=0.01)
        density_carrier = 1.0 # kg/l dla wody/pary kondensującej w przybliżeniu

        # --- OBLICZENIA Z JEDNOSTEK LITERATUROWYCH ---
        # Strumień masowy nośnika w kg/s: V_wody / 60 * gęstość
        w_flow_mass = (v_flow_rate / 60.0) * density_carrier 
        # Pojemność cieplna strumienia w kW/K: w = m_kropka * c_wody
        w_heat_capacity = w_flow_mass * c_carrier 

        # Walidacja matematyczna temperatur przed uruchomieniem logarytmów
        valid_physics = True
        if tryb_procesu == "Grzanie wkładu" and (t1_carrier <= T1_init or t1_carrier <= T2_final or T2_final <= T1_init):
            valid_physics = False
        elif tryb_procesu == "Chłodzenie wkładu" and (t1_carrier >= T1_init or t1_carrier >= T2_final or T2_final >= T1_init):
            valid_physics = False

        spec_rows = []
        mixers_fleet = st.session_state.confirmed_mixers

        for m in mixers_fleet:
            v_working = m["capacity_m3"]
            mass_batch_kg = m["mass_per_batch"]
            
            # 1. Skalowanie parametrów fizycznych aparatu
            v_total = v_working * (V_TOTAL_BASE / V_WORKING_BASE)
            scaled_area = A_BASE * ((v_working / V_WORKING_BASE) ** (2/3))
            scaled_weight = W_BASE * (v_total / V_TOTAL_BASE)
            
            # 2. Analityczne wyznaczenie czasu procesu termicznego (tau) ze wzoru różniczkowego
            if valid_physics and w_heat_capacity > 0:
                # Wyznaczenie wskaźnika efektywności wymiennika: 1 - 1/exp(k*F/w)
                efficiency_factor = 1.0 - (1.0 / math.exp((k_coefficient * scaled_area) / w_heat_capacity))
                
                # Składnik logarytmiczny: ln((T1 - t1)/(T2 - t1))
                ln_numerator = T1_init - t1_carrier
                ln_denominator = T2_final - t1_carrier
                
                ln_value = math.log(abs(ln_numerator / ln_denominator))
                
                # Przekształcenie wzoru literaturowego na czas tau (w sekundach)
                # tau = ln_value / [ efficiency_factor * (w / (M * c)) ]
                tau_seconds = ln_value / (efficiency_factor * (w_heat_capacity / (mass_batch_kg * c_product)))
                tau_hours = tau_seconds / 3600.0
            else:
                tau_hours = 0.0

            # 3. Wyznaczenie LMTD dla celów weryfikacyjnych i informacyjnych
            # Dla uproszczenia bilansu przyjmujemy deltę sprawnościową na wylocie strumienia nośnika
            t2_carrier_approx = t1_carrier + (mass_batch_kg * c_product * (T2_final - T1_init)) / (w_heat_capacity * max(tau_seconds, 1.0)) if tau_hours > 0 else t1_carrier
            dt1 = abs(t1_carrier - T1_init)
            dt2 = abs(t2_carrier_approx - T2_final)
            if dt1 == dt2 or dt2 == 0:
                lmtd = dt1
            else:
                lmtd = (dt1 - dt2) / math.log(dt1 / dt2) if (dt1 > 0 and dt2 > 0) else 0.0

            spec_rows.append({
                "Tag urządzenia 🔒": m["tag"],
                "Przypisana linia 🔒": m["product_family"],
                "Pojemność robocza [m³]": round(v_working, 1),
                "Pojemność całkowita [m³]": round(v_total, 2),
                "Powierzchnia wymiany ciepła [m²] 📐": round(scaled_area, 2),
                "Masa własna (pusty) [kg]": int(scaled_weight),
                "Wielkość szarży [kg]": int(mass_batch_kg),
                "Średnia delta LMTD [°C]": round(lmtd, 1),
                "Czas operacji termicznej [h] ⏱️": round(tau_hours, 2),
                "Status wydajności": "✅ W normie procesowej" if tau_hours <= 4.0 else "⚠️ Wymaga optymalizacji mediów"
            })

        df_spec = pd.DataFrame(spec_rows)

        # Wyświetlenie tabeli wynikowej specyfikacji technicznej aparatury
        st.dataframe(
            df_spec,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Pojemność robocza [m³]": st.column_config.NumberColumn(format="%.1f m³"),
                "Pojemność całkowita [m³]": st.column_config.NumberColumn(format="%.2f m³"),
                "Powierzchnia wymiany ciepła [m²] 📐": st.column_config.NumberColumn(format="%.2f m²"),
                "Masa własna (pusty) [kg]": st.column_config.NumberColumn(format="%d kg"),
                "Wielkość szarży [kg]": st.column_config.NumberColumn(format="%d kg"),
                "Średnia delta LMTD [°C]": st.column_config.NumberColumn(format="%.1f °C"),
                "Czas operacji termicznej [h] ⏱️": st.column_config.NumberColumn(format="%.2f h")
            }
        )

        # Przeprowadzenie walidacji błędów fizycznych w panelu bocznym
        if not valid_physics:
            st.error("🚨 Wykryto błąd krytyczny w założeniach temperaturowych! Temperatura nośnika (t1) musi pozwalać na realizację procesu wymiany ciepła w wybranym kierunku.")

        # --- SEKCJA INFORMACJI STAŁYCH Z KARTY PROJEKTOWEJ T5 ---
        st.markdown("### 🌡️ 2. Warunki brzegowe i wytrzymałościowe (T5 Design Data)")
        
        inf_col1, inf_col2 = st.columns(2)
        with inf_col1:
            st.info("""
            **Specyfikacja konstrukcyjna zbiornika (Vessel):**
            * Ciśnienie projektowe: `0 / +0,5 barg`
            * Temperatura projektowa: `120 °C`
            * Naddatek na korozję: `0 mm`
            * Izolacja termiczna: `150 mm`
            * Projektowe medium wewnętrzne: `Lubricants (Oleje)`
            """)
        with inf_col2:
            st.info("""
            **Specyfikacja układu wymiany ciepła (Coil):**
            * Ciśnienie projektowe wężownicy: `0 / +10 barg`
            * Temperatura projektowa wężownicy: `120 °C`
            * Lepkość projektowa produktu: `500 cst`
            * Współczynnik sprawności hydrodynamicznej: `Wyznaczany z liczby Reynoldsa (Re)`
            """)
# ==========================================
# ZAKŁADKA 3: LOGISTYKA OPAKOWAŃ (JEDNA, W PEŁNI INTERAKTYWNA TABELA ZBIORCZA)
# ==========================================
with tab3:
    st.header("📦 Harmonogramowanie i Zbiorczy Bilans Rozlewu Opakowań")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak zatwierdzonych danych z Zakładki 1. Uruchom konfigurację i kliknij przycisk zatwierdzenia.")
    else:
        st.markdown("### 🛠️ 1. Parametry Sterowania Rozlewem")
        
        # Konfiguracja temperatur rozlewu w kolumnach
        temp_cols = st.columns(min(len(st.session_state.confirmed_mixers), 4))
        for idx, mixer in enumerate(st.session_state.confirmed_mixers):
            with temp_cols[idx % min(len(st.session_state.confirmed_mixers), 4)]:
                t_filling = st.number_input(
                    f"Temp. rozlewu {mixer['tag']} [°C]:", 
                    min_value=10.0, max_value=120.0, 
                    value=float(min(30.0, st.session_state.heat_temps.get(mixer["tag"], 60.0))), 
                    key=f"t_fill_{mixer['tag']}"
                )
                st.session_state.filling_temps[mixer["tag"]] = t_filling

        st.markdown("---")
        st.markdown("### 📊 2. Zbiorcze Zestawienie Strumieni Logistycznych Zakładu")
        st.info("💡 **Instrukcja:** Kolumna **'Zastosowany Udział % 🟦'** jest w pełni edytowalna. Możesz modyfikować udziały opakowań bezpośrednio w głównej tabeli – system natychmiast przeliczy logistykę na żywo.")
        
        # KROK A: Inicjalizacja stałej bazy danych w session_state (jeśli nie istnieje)
        if "master_logistics_df" not in st.session_state:
            init_rows = []
            for mixer in st.session_state.confirmed_mixers:
                kat = mixer["product_family"]
                chosen_packs = input_packs.get(kat, [])
                if mixer["annual_volume"] > 0 and chosen_packs:
                    # Domyślny równomierny podział procentowy
                    default_pct = round(100.0 / len(chosen_packs), 1)
                    for p_name in chosen_packs:
                        init_rows.append({
                            "ID Reaktora 🔒": mixer["tag"],
                            "Linia Produktowa 🔒": kat,
                            "Typ Opakowania 🔒": p_name,
                            "Zastosowany Udział % 🟦": default_pct
                        })
            st.session_state.master_logistics_df = pd.DataFrame(init_rows)

        # KROK B: Pobieramy dane z sesji i w locie obliczamy kolumny pochodne (szt., palety, czas)
        df_calc = st.session_state.master_logistics_df.copy()
        
        calculated_liters_list = []
        calculated_szt_list = []
        calculated_pallets_list = []
        calculated_hours_list = []
        
        for _, row in df_calc.iterrows():
            r_id = row["ID Reaktora 🔒"]
            kat = row["Linia Produktowa 🔒"]
            p_name = row["Typ Opakowania 🔒"]
            pct = row["Zastosowany Udział % 🟦"] / 100.0
            
            # Pobieramy dane wejściowe dla danego reaktora z Zakładki 1
            mixer_meta = next((m for m in st.session_state.confirmed_mixers if m["tag"] == r_id), None)
            if mixer_meta:
                m_monthly_kg = mixer_meta["annual_volume"] / 12
                dens = FUCHS_PORTFOLIO[kat]["density"]
                total_volume_l = m_monthly_kg / dens
                config = PACK_CONFIGS[p_name]
                
                allocated_liters = total_volume_l * pct
                total_szt = math.ceil(allocated_liters / config["size_l"]) if allocated_liters > 0 else 0
                needed_pallets = math.ceil(total_szt / config["per_pallet"]) if total_szt > 0 else 0
                filling_hours = total_szt / config["rate_szt_h"] if total_szt > 0 else 0.0
            else:
                allocated_liters, total_szt, needed_pallets, filling_hours = 0, 0, 0, 0.0
                
            calculated_liters_list.append(int(allocated_liters))
            calculated_szt_list.append(int(total_szt))
            calculated_pallets_list.append(int(needed_pallets))
            calculated_hours_list.append(round(filling_hours, 1))
            
        df_calc["Objętość Strumienia [l] 🔒"] = calculated_liters_list
        df_calc["Zapotrzebowanie [szt./mies] 🔒"] = calculated_szt_list
        df_calc["Palety [EPAL/mies] 🔒"] = calculated_pallets_list
        df_calc["Czas pracy linii rozlewu [h] 🔒"] = calculated_hours_list

        # KROK C: Renderowanie JEDNEGO, zintegrowanego edytora tabeli
        edited_master_df = st.data_editor(
            df_calc,
            hide_index=True,
            use_container_width=True,
            disabled=[
                "ID Reaktora 🔒", "Linia Produktowa 🔒", "Typ Opakowania 🔒", 
                "Objętość Strumienia [l] 🔒", "Zapotrzebowanie [szt./mies] 🔒", 
                "Palety [EPAL/mies] 🔒", "Czas pracy linii rozlewu [h] 🔒"
            ],
            column_config={
                "Zastosowany Udział % 🟦": st.column_config.NumberColumn(
                    min_value=0.0, max_value=100.0, step=1.0, format="%.1f%%"
                ),
                "Objętość Strumienia [l] 🔒": st.column_config.NumberColumn(format="%d"),
                "Zapotrzebowanie [szt./mies] 🔒": st.column_config.NumberColumn(format="%d"),
                "Palety [EPAL/mies] 🔒": st.column_config.NumberColumn(format="%d"),
                "Czas pracy linii rozlewu [h] 🔒": st.column_config.NumberColumn(format="%.1f h")
            },
            key="global_logistics_data_editor"
        )

        # KROK D: Zapisujemy zaktualizowane procenty z powrotem do sesji, by nie zniknęły przy odświeżeniu
        st.session_state.master_logistics_df["Zastosowany Udział % 🟦"] = edited_master_df["Zastosowany Udział % 🟦"]

        # KROK E: Walidacja matematyczna sumy 100% dla poszczególnych maszyn
        for mixer in st.session_state.confirmed_mixers:
            r_id = mixer["tag"]
            sub_df = edited_master_df[edited_master_df["ID Reaktora 🔒"] == r_id]
            current_sum = sub_df["Zastosowany Udział % 🟦"].sum()
            if not math.isclose(current_sum, 100.0, abs_tol=0.1):
                st.error(f"❌ **Błąd bilansu:** Suma udziałów dla reaktora **{r_id}** wynosi **{current_sum:.1f}%**. Zmodyfikuj wiersze, aby suma wynosiła równo 100%!")

        # --- SEKCJA GLOBALNYCH METRYK KPI POD TABELĄ ---
        st.markdown("<br>", unsafe_allow_html=True)
        total_factory_hours = edited_master_df["Czas pracy linii rozlewu [h] 🔒"].sum()
        total_factory_pallets = edited_master_df["Palety [EPAL/mies] 🔒"].sum()
        total_factory_szt = edited_master_df["Zapotrzebowanie [szt./mies] 🔒"].sum()
        
        st.subheader("📦 Łączne podsumowanie potoku logistycznego fabryki:")
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        with sum_col1:
            st.metric(label="🔄 Sumaryczny wolumen opakowań", value=f"{total_factory_szt:,} szt./miesiąc")
        with sum_col2:
            st.metric(label="🧱 Całkowity obrót magazynowy palet", value=f"{total_factory_pallets} EPAL/miesiąc")
        with sum_col3:
            factory_days = total_factory_hours / godziny_dziennie if godziny_dziennie > 0 else 0
            st.metric(
                label="⏱ ... Globalny czas pracy konfekcji", 
                value=f"{total_factory_hours:.1f} h/miesiąc",
                delta=f"Obciążenie: {factory_days:.1f} dni roboczych"
            )
# ==========================================
# ZAKŁADKA 4: FINANSE - BILANSE MOCY ELEKTRYCZNEJ
# ==========================================
with tab4:
    st.header("💰 Optymalizacja Kosztów Energii i Bilans Finansowy")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych. Uruchom konfigurację w Zakładce 1.")
    else:
        st.markdown("### ⚡ 1. Taryfy i Parametry Ekonomiczne")
        waluta = st.selectbox("Wybierz walutę operacyjną:", ["PLN", "EUR", "USD"])
        default_cost = 2.119 if waluta == "PLN" else 0.535
        default_energy_rate = 750.0 if waluta == "PLN" else 160.0 
        
        c_fin1, c_fin2 = st.columns(2)
        with c_fin1: manuf_cost_per_kg = st.number_input(f"Bazowy Manufacturing Cost [za kg] w {waluta}:", min_value=0.01, value=default_cost, format="%.3f")
        with c_fin2: cena_mwh = st.number_input(f"Cena energii elektrycznej i cieplnej [{waluta}/MWh]:", min_value=1.0, value=default_energy_rate, format="%.2f")
        
        financial_summary = []
        total_monthly_saving_thermal = 0.0
        total_base_manuf_cost = 0.0
        total_mixing_energy_kwh = 0.0
        total_pumping_energy_kwh = 0.0
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            m_monthly_kg = mixer["annual_volume"] / 12
            batches_per_month = mixer["batches_count"]
            
            # Rekonstrukcja dynamiczna mocy i energii pobieranej z Zakładki 2
            d_agitor = round(round(2.2 * ((mixer["capacity_m3"] / 10.0) ** (1/3)), 2) / 3, 2)
            P_max_w = 2.5 * (1.5 ** 3) * (d_agitor ** 5) * (prod_info["density"] * 1000.0)
            motor_power_kw = max((P_max_w / 0.85 * 1.20) / 1000.0, 0.75)
            mixing_energy_month_kwh = motor_power_kw * prod_info["cycle_h"] * batches_per_month
            
            default_q_pump = float(max(round((mixer["capacity_m3"] / 0.75) * 1.25, 1), 5.0))
            pump_power_kw = max((default_q_pump * 2.5) / (36.0 * 0.60) * 1.15, 0.37)
            pumping_energy_month_kwh = pump_power_kw * (mixer["capacity_m3"] / default_q_pump) * batches_per_month
            
            total_mixing_energy_kwh += mixing_energy_month_kwh
            total_pumping_energy_kwh += pumping_energy_month_kwh
            cost_el_node = ((mixing_energy_month_kwh + pumping_energy_month_kwh) / 1000.0) * cena_mwh
            
            t_max_mix = st.session_state.heat_temps.get(mixer["tag"], 60.0)
            t_rozlew = st.session_state.filling_temps.get(mixer["tag"], 30.0)
            base_manuf_cost_monthly = m_monthly_kg * manuf_cost_per_kg
            total_base_manuf_cost += base_manuf_cost_monthly
            
            oszczednosc_cieplna_mies = 0.0
            energia_cieplna_mwh_mies = 0.0
            if t_rozlew < t_max_mix:
                energia_cieplna_mwh_mies = (m_monthly_kg * prod_info["cp"] * (t_max_mix - t_rozlew)) / 3_600_000.0
                oszczednosc_cieplna_mies = energia_cieplna_mwh_mies * cena_mwh
                total_monthly_saving_thermal += oszczednosc_cieplna_mies
                
            financial_summary.append({
                "Reaktor": mixer["tag"], "Miesięczny tonaż [kg]": int(m_monthly_kg),
                "Energia Mieszania [kWh/m]": round(mixing_energy_month_kwh, 1), "Energia Pompowania [kWh/m]": round(pumping_energy_month_kwh, 1),
                "Koszt energii el.": f"{cost_el_node:.2f} {waluta}", "Oszczędność termiczna": f"- {oszczednosc_cieplna_mies:.2f} {waluta}"
            })
            
        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("⚡ Globalne koszty zużycia prądu fabryki:")
        cost_total_el = ((total_mixing_energy_kwh + total_pumping_energy_kwh) / 1000.0) * cena_mwh
        
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1: st.metric("⚙️ Zużycie: Mieszanie", f"{total_mixing_energy_kwh:,.1f} kWh/m")
        with s_col2: st.metric("🔄 Zużycie: Przepompowanie", f"{total_pumping_energy_kwh:,.1f} kWh/m")
        with s_col3: st.metric("🔌 Łączny koszt energii el.", f"{cost_total_el:,.2f} {waluta}/mies")
        
        st.markdown("---")
        final_manufacturing_cost = total_base_manuf_cost + cost_total_el - total_monthly_saving_thermal
        st.metric(label="🚀 ZOPTYMALIZOWANY REALNY KOSZT WYTWORZENIA (Miesięcznie)", value=f"{final_manufacturing_cost:,.2f} {waluta}")

# ==========================================
# ZAKŁADKA 5: RAW MATERIAL (SUROWCE I TANK FARM)
# ==========================================
with tab5:
    st.header("🛢️ Logistyka Surowcowa i Wymiarowanie Parku Zbiorników")
    if not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych technicznych. Uruchom konfigurację w Zakładce 1.")
    else:
        st.markdown("### ⚙️ 1. Parametry Strategii Zaopatrzenia")
        c_raw1, c_raw2 = st.columns(2)
        with c_raw1: base_oil_ratio = st.slider("Udział oleju bazowego w recepturze [%]:", min_value=50, max_value=95, value=80, step=5) / 100.0
        with c_raw2: days_of_stock = st.number_input("Wymagany zapas bezpieczeństwa surowca [dni]:", min_value=5, max_value=60, value=14, step=1)
            
        st.markdown("---")
        st.markdown("### 📊 2. Bilans Zapotrzebowania na Oleje Bazowe")
        
        raw_material_summary = []
        total_annual_base_oil_kg = 0.0
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            v_annual_product_tony = mixer["annual_volume"] / 1000.0
            base_oil_annual_tony = v_annual_product_tony * base_oil_ratio
            base_oil_monthly_tony = (v_annual_product_tony / 12.0) * base_oil_ratio
            base_oil_monthly_m3 = (base_oil_monthly_tony * 1000.0) / (0.88 * 1000.0)
            total_annual_base_oil_kg += (base_oil_annual_tony * 1000.0)
            
            raw_material_summary.append({
                "ID Reaktora 🔒": mixer["tag"], "Rodzina Produktu 🔒": kat, "Produkcja [t/rok] 🔒": round(v_annual_product_tony, 1),
                "Baza [t/rok] 🔒": round(base_oil_annual_tony, 1), "Baza [t/mies] 🔒": round(base_oil_monthly_tony, 1), "Objętość Bazy [m³/mies] 🔒": round(base_oil_monthly_m3, 1)
            })
            
        st.dataframe(pd.DataFrame(raw_material_summary), hide_index=True, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("🏢 3. Wymiarowanie Infrastruktury Magazynowej (Tank Farm)")
        
        total_annual_base_oil_tony = total_annual_base_oil_kg / 1000.0
        daily_base_oil_consumption_tony = total_annual_base_oil_tony / 250.0
        required_stock_m3 = (daily_base_oil_consumption_tony * days_of_stock) / 0.88
        
        c_tank1, c_tank2 = st.columns(2)
        with c_tank1: selected_tank_capacity_m3 = st.selectbox("Wybierz typową pojemność pojedynczego silosu [m³]:", [30, 50, 60, 80, 100, 150, 200], index=3)
        with c_tank2:
            needed_tanks_count = math.ceil(required_stock_m3 / (selected_tank_capacity_m3 * 0.85)) if required_stock_m3 > 0 else 0
            st.metric(label="🧱 Wymagana liczba silosów surowca", value=f"{needed_tanks_count} szt.", delta=f"Zapas na {days_of_stock} dni")
            
        st.markdown("<br>", unsafe_allow_html=True)
        raw_kpi1, raw_kpi2, raw_kpi3 = st.columns(3)
        with raw_kpi1: st.metric(label="📈 Zapotrzebowanie całkowite na bazę", value=f"{total_annual_base_oil_tony:,.1f} t/rok")
        with raw_kpi2: st.metric(label="🔀 Średnie zużycie dobowe", value=f"{daily_base_oil_consumption_tony:.1f} t/dzień")
        with raw_kpi3: st.metric(label="📐 Minimalna pojemność parku zbiorników", value=f"{required_stock_m3:,.1f} m³")
        
        st.warning(f"🚚 **Logistyka:** Wymaga to dostarczenia średnio **{((total_annual_base_oil_tony / 12.0) / 24.0):.1f} cystern (24t) na miesiąc**.")
