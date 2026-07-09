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

# ==========================================
# ZINTEGROWANY PANEL BOCZNY (WYBÓR OPAKOWAŃ I PROCENTÓW RAZEM)
# ==========================================

# KROK 1: Wybór Rodzin Produktowych
st.sidebar.header("📋 KROK 1: Wybór Rodzin")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz aktywne linie produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Hydraulic Oils (RENOLIN)", "Engine Oils (TITAN)", "Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")

# KROK 2: Założenia Czasu Pracy
st.sidebar.header("⏱️ KROK 2: Założenia Czasu Pracy")
liczba_zmian = st.sidebar.slider("Liczba zmian produkcyjnych:", min_value=1.0, max_value=3.0, value=1.0, step=0.5)
godziny_na_zmiane = st.sidebar.slider("Liczba godzin na jedną zmianę:", min_value=4.0, max_value=12.0, value=8.0, step=0.5)

godziny_dziennie = liczba_zmian * godziny_na_zmiane
AVAILABLE_HOURS_MONTH = (250 * godziny_dziennie) / 12  

st.sidebar.markdown("---")

# KROK 3: Zintegrowany Wybór Opakowań i Procentów (Linia po Linii)
st.sidebar.header("⚙️ KROK 3: Konfiguracja i Split Opakowań")

input_packs = {}
# Słownik przechowujący udziały procentowe przypisane do konkretnej rodziny i opakowania
if "opakowania_podzial" not in st.session_state:
    st.session_state.opakowania_podzial = {}

for kat in wybrane_kategorie:
    st.sidebar.markdown(f"##### 🏭 Linia: **{kat}**")
    
    # Wybór opakowań dla danej rodziny
    packs = st.sidebar.multiselect(
        f"Dostępne opakowania:", 
        list(PACK_CONFIGS.keys()), 
        default=["5l (Karton)", "200l (Beczka)", "1000l (IBC)"], 
        key=f"packs_{kat}"
    )
    input_packs[kat] = packs
    
    # Jeśli użytkownik wybrał jakiekolwiek opakowanie, od razu pod spodem wyświetlamy pola %
    if packs:
        domyslny_procent = round(100.0 / len(packs), 1)
        suma_procentow_linii = 0.0
        
        for p in packs:
            # Unikalny klucz dla kombinacji: Rodzina + Opakowanie
            key_id = f"pct_{kat}_{p}"
            current_val = st.session_state.opakowania_podzial.get(key_id, domyslny_procent)
            
            val = st.sidebar.number_input(
                f"   ↳ Udział {p} [%]",
                min_value=0.0,
                max_value=100.0,
                value=float(current_val),
                step=5.0,
                key=key_id
            )
            st.session_state.opakowania_podzial[key_id] = val
            suma_procentow_linii += val
        
        # Walidacja sumy 100% niezależnie dla KAŻDEJ linii produktowej
        if round(suma_procentow_linii, 1) == 100.0:
            st.sidebar.success(f"   ✅ Bilans {kat}: 100%")
        else:
            st.sidebar.error(f"   ❌ Suma dla {kat}: {suma_procentow_linii}% (Musi być 100%!)")
    else:
        st.sidebar.info("   ⚠️ Wybierz min. jedno opakowanie dla tej linii.")
    
    st.sidebar.markdown("---")
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
# ZAKŁADKA 1: OPCJA AKCEPTACJI TYPOSZEREGU + SKUs + PODZIAŁ NA ZBIORNIKI
# ==========================================
with tab1:
    st.header(f"Zintegrowane Zestawienie Parametrów Procesowych (Baza: {godziny_dziennie:.1f}h/dzień)")
    
    # Definicja dopuszczalnego typoszeregu pojemności mikserów fabryki
    TYPOSZEREG_MIKSEROW = [5, 7, 10, 15, 18, 21, 25, 31]
    
    if wybrane_kategorie:
        # Inicjalizacja struktur w session_state (zachowanie edycji użytkownika)
        for kat in wybrane_kategorie:
            if kat not in st.session_state.prod_dict:
                st.session_state.prod_dict[kat] = {"roczna": 1200000, "utilization": 75.0, "skus": 1, "num_tanks": 1, "use_typoszereg": False}
            if "skus" not in st.session_state.prod_dict[kat]:
                st.session_state.prod_dict[kat]["skus"] = 1
            if "num_tanks" not in st.session_state.prod_dict[kat]:
                st.session_state.prod_dict[kat]["num_tanks"] = 1
            if "use_typoszereg" not in st.session_state.prod_dict[kat]:
                st.session_state.prod_dict[kat]["use_typoszereg"] = False

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
                        if "5. Użyj Typoszeregu 🟦" in changes:
                            st.session_state.prod_dict[family_name]["use_typoszereg"] = bool(changes["5. Użyj Typoszeregu 🟦"])

        calculated_matrix_rows = []
        oversized_reactors = {}

        # Przetwarzanie matematyczne każdej rodziny produktowej
        for kat in wybrane_kategorie:
            m_annual = st.session_state.prod_dict[kat]["roczna"]
            util_target = st.session_state.prod_dict[kat]["utilization"]
            skus = st.session_state.prod_dict[kat]["skus"]
            use_typo = st.session_state.prod_dict[kat]["use_typoszereg"]
            
            dens = FUCHS_PORTFOLIO[kat]["density"]
            cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            m_monthly = m_annual / 12
            allocated_hours = AVAILABLE_HOURS_MONTH * (util_target / 100.0)
            
            # Wyznaczenie bazowego gabarytu z docelowej utylizacji czasu
            raw_batches = math.ceil(allocated_hours / cyc) if allocated_hours > 0 else 1
            raw_batch_size_kg = math.ceil(m_monthly / raw_batches) if raw_batches > 0 else 0
            calculated_vol_m3 = raw_batch_size_kg / (dens * 1000.0) if raw_batch_size_kg > 0 else 0.0

            # Dopasowanie do najbliższego wyższego typoszeregu mikserów
            sug_vol = 0
            for v in TYPOSZEREG_MIKSEROW:
                if v >= calculated_vol_m3:
                    sug_vol = v
                    break
            if sug_vol == 0 and calculated_vol_m3 > 0:
                sug_vol = 31  # Limit górny konstrukcji transportowej

            # REAKCJA NA AKCEPTACJĘ TYPOSZEREGU:
            if use_typo and sug_vol > 0:
                final_vol_m3 = sug_vol
                batch_size_kg = final_vol_m3 * (dens * 1000.0)
                needed_batches = math.ceil(m_monthly / batch_size_kg) if batch_size_kg > 0 else 1
            else:
                final_vol_m3 = calculated_vol_m3
                batch_size_kg = raw_batch_size_kg
                needed_batches = raw_batches

            if final_vol_m3 > 31.0:
                oversized_reactors[kat] = final_vol_m3

            calculated_matrix_rows.append({
                "1. Nazwa rodziny 🔒": kat,
                "2. Roczna produkcja [kg] 🟦": int(m_annual),
                "3. Docelowa Utylizacja [%] 🟦": float(util_target),
                "4. Liczba SKUs 🟦": int(skus),
                "5. Użyj Typoszeregu 🟦": bool(use_typo),
                "6. Wyliczony gabaryt reaktora 🔒": round(calculated_vol_m3, 2),
                "7. Sugerowany Mikser (Typoszereg) 🔒": f"{sug_vol} m³" if sug_vol > 0 else "Poniżej minimum (<5 m³)",
                "h_vol": final_vol_m3, "h_batches": needed_batches, "h_kg": batch_size_kg, "h_annual": m_annual
            })

        df_complete_matrix = pd.DataFrame(calculated_matrix_rows)

        st.markdown("##### 📥 Krok A: Parametryzacja Tonażu, Utylizacji oraz SKUs")
        
        # Funkcja podświetlająca komórki, gdzie gabaryt jest mniejszy niż 5 m³
        def style_small_volumes(row):
            styles = [''] * len(row)
            val = row["6. Wyliczony gabaryt reaktora 🔒"]
            if isinstance(val, (int, float)) and val < 5.0:
                idx = row.index.get_loc("6. Wyliczony gabaryt reaktora 🔒")
                styles[idx] = 'background-color: #ffcccc; color: #cc0000; font-weight: bold;'
            return styles

        styled_matrix = df_complete_matrix.style.apply(style_small_volumes, axis=1)

        # Wyświetlenie tabeli edytowalnej w standardzie Streamlit v2026
        edited_table = st.data_editor(
            styled_matrix,
            hide_index=True,
            width="stretch",
            disabled=["1. Nazwa rodziny 🔒", "6. Wyliczony gabaryt reaktora 🔒", "7. Sugerowany Mikser (Typoszereg) 🔒"],
            column_config={
                "2. Roczna produkcja [kg] 🟦": st.column_config.NumberColumn(min_value=0, step=50000, format="%d"),
                "3. Docelowa Utylizacja [%] 🟦": st.column_config.NumberColumn(min_value=1.0, max_value=100.0, step=5.0, format="%.1f%%"),
                "4. Liczba SKUs 🟦": st.column_config.NumberColumn(min_value=1, step=1),
                "5. Użyj Typoszeregu 🟦": st.column_config.CheckboxColumn(),
                "6. Wyliczony gabaryt reaktora 🔒": st.column_config.NumberColumn(format="%.2f m³"),
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

        # Krok D: Generowanie Końcowej Floty Mieszalników (z uwzględnieniem realnej utylizacji)
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
            cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            tanks_count = st.session_state.prod_dict[kat]["num_tanks"]
            vol_per_tank = vol_base / tanks_count if tanks_count > 0 else vol_base
            batches_per_tank = math.ceil(total_batches / tanks_count) if tanks_count > 0 else total_batches
            annual_per_tank = total_annual / tanks_count

            if AVAILABLE_HOURS_MONTH > 0:
                real_utilization = (batches_per_tank * cyc) / AVAILABLE_HOURS_MONTH * 100.0
            else:
                real_utilization = 0.0

            if split_decisions.get(kat, False) and vol_per_tank > 31.0:
                remaining_vol = vol_per_tank
                sub_letter_ascii = 65 
                while remaining_vol > 62.0:
                    weight_fraction = 31.0 / vol_per_tank
                    mixer_annual = annual_per_tank * weight_fraction
                    mixer_batches = math.ceil(batches_per_tank * weight_fraction)
                    mixer_mass_batch = math.ceil((r["h_kg"]/tanks_count) * (31.0 / vol_per_tank))
                    
                    if AVAILABLE_HOURS_MONTH > 0:
                        split_util = (mixer_batches * cyc) / AVAILABLE_HOURS_MONTH * 100.0
                    else:
                        split_util = 0.0
                    
                    for t_idx in range(tanks_count):
                        tag_id = f"MT-{tag_counter}{chr(sub_letter_ascii)}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                        final_fleet_rows.append({
                            "ID Urządzenia 🔒": tag_id, "Przypisana Linia 🔒": kat,
                            "Liczba szarż [/mies] 🔒": int(mixer_batches), "Realna Utylizacja [%] 🔒": round(split_util, 1),
                            "Realna Pojemność [m³] 🔒": 31.0, "Masa Szarży [kg] 🔒": int(mixer_mass_batch), 
                            "Status 🔒": "🧱 Max Gabaryt (31.0 m³)"
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
                    
                    if AVAILABLE_HOURS_MONTH > 0:
                        tail_util = (tail_batches * cyc) / AVAILABLE_HOURS_MONTH * 100.0
                    else:
                        tail_util = 0.0
                    
                    for t_idx in range(tanks_count):
                        for _ in range(2):
                            tag_id = f"MT-{tag_counter}{chr(sub_letter_ascii)}" + (f"-Z{t_idx+1}" if tanks_count > 1 else "")
                            final_fleet_rows.append({
                                "ID Urządzenia 🔒": tag_id, "Przypisana Linia 🔒": kat,
                                "Liczba szarż [/mies] 🔒": int(tail_batches), "Realna Utylizacja [%] 🔒": round(tail_util, 1),
                                "Realna Pojemność [m³] 🔒": round(split_tail_vol, 1), "Masa Szarży [kg] 🔒": int(tail_mass_batch), 
                                "Status 🔒": "🟢 Bliźniak Konstrukcyjny"
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
                        "Liczba szarż [/mies] 🔒": int(batches_per_tank), "Realna Utylizacja [%] 🔒": round(real_utilization, 1),
                        "Realna Pojemność [m³] 🔒": round(vol_per_tank, 1), "Masa Szarży [kg] 🔒": int(mass_batch), 
                        "Status 🔒": status_txt
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
            width="stretch",
            column_config={
                "Realna Utylizacja [%] 🔒": st.column_config.NumberColumn(format="%.1f%%"),
                "Realna Pojemność [m³] 🔒": st.column_config.NumberColumn(format="%.1f m³"),
                "Masa Szarży [kg] 🔒": st.column_config.NumberColumn(format="%d kg")
            }
        )

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
# ZAKŁADKA 2: ZAAWANSOWANY KONFIGURATOR (ZINTEGROWANY PROFIL TERMICZNY)
# ==========================================
with tab2:
    st.header("📐 Specyfikacja Maszyn, Reologii i Dynamicznej Termodynamiki")

    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.info("💡 Aby wygenerować specyfikację, najpierw zatwierdź konfigurację floty w **Zakładce 1** (przycisk na dole strony).")
    else:
        st.markdown("### 🛠️ Szczegółowe Dostrajanie Parametrów Konstrukcyjno-Procesowych")
        st.caption("Każdy reaktor posiada osobny panel konfiguracyjny. Zwróć uwagę na zintegrowany profil grzania i chłodzenia.")

        mixers_fleet = st.session_state.confirmed_mixers
        spec_rows = []
        
        if "calculated_times" not in st.session_state:
            st.session_state.calculated_times = {}
        if "pump_flows" not in st.session_state:
            st.session_state.pump_flows = {}

        # Referencyjne dane geometryczne
        V_WORKING_BASE = 10.0
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
                sub_t1, sub_t2, sub_t3 = st.tabs([
                    "🔥❄️ 1. Układ Termiczny (Grzanie i Chłodzenie)", 
                    "⚙️ 2. Kinematyka i Moc Mieszadła", 
                    "🔄 3. Układ Hydrauliczny i Pompa"
                ])
                
                # ---------------------------------------------------------
                # SUB-ZAKŁADKA 1: ZINTEGROWANY PROFIL TERMICZNY
                # ---------------------------------------------------------
                with sub_t1:
                    st.markdown(f"##### Parametry Bazowe Wymiennika Ciepła ({tag})")
                    c_h1, c_h2, c_h3, c_h4 = st.columns(4)
                    with c_h1:
                        mat_reaktora = st.selectbox("Materiał korpusu:", ["Stal węglowa", "Stal nierdzewna"], index=0 if "zwykła" in default_mat else 1, key=f"mat_{tag}", help="Wpływa na współczynnik przenikania ciepła wężownicy/płaszcza.")
                    with c_h2:
                        v_flow_l_min = st.number_input("Przepływ nośników [l/min]:", min_value=10.0, max_value=2000.0, value=410.0, step=10.0, key=f"vflow_{tag}", help="Wspólny strumień dla nośnika grzewczego i chłodzącego.")
                    with c_h3:
                        c_p_product = st.number_input("Ciepło wł. produktu [kJ/kgK]:", value=c_p_default, step=0.1, key=f"cpprod_{tag}")
                    with c_h4:
                        fouling_factor = st.slider("Fouling (Zabrudzenie) [%]:", 0, 40, 15, step=5, key=f"foul_{tag}", help="Spadek sprawności wężownicy z powodu osadów.")

                    st.markdown("###### 🔥 Faza Grzania (Rozruch i topienie dodatków)")
                    c_g1, c_g2, c_g3, c_g4 = st.columns(4)
                    with c_g1:
                        medium_term = st.selectbox("Nośnik grzewczy:", ["Para wodna", "Olej termalny", "Gorąca woda"], key=f"medg_{tag}")
                    with c_g2:
                        T1_init = st.number_input("Temp. początkowa [°C]:", value=20.0, step=5.0, key=f"t1_{tag}")
                    with c_g3:
                        T2_final = st.number_input("Temp. procesu MAX [°C]:", value=70.0, step=5.0, key=f"t2_{tag}", help="Docelowa temperatura do rozpuszczenia pakietów.")
                    with c_g4:
                        t_in_carrier = st.number_input("Temp. nośnika grz. [°C]:", value=120.0, step=5.0, key=f"t_car_{tag}")

                    st.markdown("###### ❄️ Faza Chłodzenia (Przygotowanie do rozlewu)")
                    c_c1, c_c2, c_c3, c_c4 = st.columns(4)
                    with c_c1:
                        medium_chl = st.selectbox("Nośnik chłodzący:", ["Brak (Zrzut na gorąco)", "Woda z wieży (ok. 20°C)", "Woda z chillera (ok. 7°C)"], key=f"medc_{tag}")
                    with c_c2:
                        T3_rozlew = st.number_input("Temp. rozlewu [°C]:", value=40.0, step=5.0, key=f"t3_{tag}", disabled=(medium_chl=="Brak (Zrzut na gorąco)"), help="Oczekiwana temperatura produktu podczas odpompowywania.")
                    with c_c3:
                        t_in_chl = st.number_input("Temp. nośnika chł. [°C]:", value=15.0, step=1.0, key=f"tinc_{tag}", disabled=(medium_chl=="Brak (Zrzut na gorąco)"))
                    with c_c4:
                        st.write("") # Puste miejsce dla równego układu

                # ---------------------------------------------------------
                # SUB-ZAKŁADKA 2: MIESZADŁO
                # ---------------------------------------------------------
                with sub_t2:
                    st.markdown(f"##### Specyfikacja Hydrodynamiczna Wirnika ({tag})")
                    c_m1, c_m2, c_m3 = st.columns(3)
                    with c_m1:
                        typ_wirnika = st.selectbox("Geometria wirnika:", list(AGITATOR_TYPES.keys()), index=1, key=f"agit_type_{tag}")
                    with c_m2:
                        obroty_rpm = st.number_input("Obroty [RPM]:", min_value=10, max_value=500, value=90, step=10, key=f"rpm_{tag}")
                    with c_m3:
                        motor_efficiency = st.slider("Sprawność napędu [%]:", min_value=50, max_value=98, value=85, step=1, key=f"eff_mot_{tag}")

                # ---------------------------------------------------------
                # SUB-ZAKŁADKA 3: POMPA I RUROCIĄGI
                # ---------------------------------------------------------
                with sub_t3:
                    st.markdown(f"##### Wymiarowanie Linii i Zakres Reologiczny ({tag})")
                    c_p1, c_p2, c_p3 = st.columns(3)
                    with c_p1:
                        q_user_m3_h = st.number_input("Wydajność Q [m³/h]:", min_value=1.0, value=float(round(v_working / 0.75, 1)), key=f"qp_{tag}", help="Nominalny strumień objętościowy rozładunku.")
                        pipe_l_m = st.number_input("Długość rury L [m]:", min_value=1.0, value=15.0, key=f"pl_{tag}")
                    with c_p2:
                        pipe_d_mm = st.number_input("Średnica wewn. D [mm]:", min_value=25, max_value=300, value=80, step=5, key=f"pd_{tag}")
                        visc_max_cst = st.number_input("Lepkość MAX (Zimny) [cSt]:", min_value=10.0, max_value=5000.0, value=800.0, step=50.0, key=f"vmax_{tag}", help="Lepkość w momencie rozruchu (najwyższa).")
                    with c_p3:
                        h_static_m = st.number_input("Wysokość H_stat [m]:", value=3.0, key=f"ph_{tag}")
                        visc_min_cst = st.number_input("Lepkość MIN (Ciepły) [cSt]:", min_value=1.0, max_value=1000.0, value=100.0, step=10.0, key=f"vmin_{tag}", help="Lepkość podczas ciepłego rozlewu (najniższa).")

            # =========================================================
            # OBLICZENIA MATEMATYCZNO-FIZYCZNE DLA KONFIGURATORA
            # =========================================================
            st.session_state.pump_flows[tag] = q_user_m3_h
            scaled_area_m2 = A_BASE * ((v_working / 10.0) ** (2/3))

            # --- A1. OBLICZENIA FAZY GRZANIA ---
            k_base_grz = 0.55 if "Para" in medium_term else 0.40 if "nierdzewna" in mat_reaktora else (0.95 if "Para" in medium_term else 0.60)
            k_act_grz = k_base_grz * (1.0 - (fouling_factor / 100.0))
            c_p_carrier_grz = 4.184 if "woda" in medium_term.lower() else (2.1 if "olej" in medium_term.lower() else 4.2)
            w_cap_grz = ((v_flow_l_min / 60.0) * 1.0) * c_p_carrier_grz

            if (t_in_carrier > T1_init and t_in_carrier > T2_final and T2_final > T1_init) and w_cap_grz > 0:
                ntu_g = (k_act_grz * scaled_area_m2) / w_cap_grz
                eff_g = (1.0 - math.exp(-ntu_g)) / ntu_g if ntu_g > 0 else 1.0
                dT1_g = abs(t_in_carrier - T1_init) * eff_g
                dT2_g = abs(t_in_carrier - T2_final) * eff_g
                lmtd_grz = (dT1_g - dT2_g) / math.log(dT1_g / dT2_g) if (dT1_g > 0 and dT2_g > 0 and dT1_g != dT2_g) else dT1_g
                Q_grz_kwh = (mass_batch_kg * c_p_product * abs(T2_final - T1_init)) / 3600.0
                power_grz_kw = k_act_grz * scaled_area_m2 * lmtd_grz
                tau_grz = Q_grz_kwh / power_grz_kw if power_grz_kw > 0 else 0.0
            else:
                Q_grz_kwh, tau_grz = 0.0, 0.0

            # --- A2. OBLICZENIA FAZY CHŁODZENIA ---
            if medium_chl != "Brak (Zrzut na gorąco)" and (T2_final > T3_rozlew and T3_rozlew > t_in_chl):
                k_base_chl = 0.45 if "nierdzewna" in mat_reaktora else 0.75
                k_act_chl = k_base_chl * (1.0 - (fouling_factor / 100.0))
                w_cap_chl = ((v_flow_l_min / 60.0) * 1.0) * 4.184
                
                ntu_c = (k_act_chl * scaled_area_m2) / w_cap_chl
                eff_c = (1.0 - math.exp(-ntu_c)) / ntu_c if ntu_c > 0 else 1.0
                dT1_c = abs(T2_final - t_in_chl) * eff_c
                dT2_c = abs(T3_rozlew - t_in_chl) * eff_c
                lmtd_chl = (dT1_c - dT2_c) / math.log(dT1_c / dT2_c) if (dT1_c > 0 and dT2_c > 0 and dT1_c != dT2_c) else dT1_c
                
                Q_chl_kwh = (mass_batch_kg * c_p_product * abs(T2_final - T3_rozlew)) / 3600.0
                power_chl_kw = k_act_chl * scaled_area_m2 * lmtd_chl
                tau_chl = Q_chl_kwh / power_chl_kw if power_chl_kw > 0 else 0.0
            else:
                Q_chl_kwh, tau_chl = 0.0, 0.0

            # Sumaryczny czas trwania profilu termicznego
            total_thermal_time = tau_grz + tau_chl

            # --- B. OBLICZENIA MIESZADŁA ---
            visc_avg_pas = ((visc_max_cst + visc_min_cst) / 2.0 / 1_000_000.0) * rho_product
            D_vessel = 2.2 * ((v_working / 10.0) ** (1/3))
            d_impeller = D_vessel / 3.0
            Re_mixing = ((obroty_rpm / 60.0) * (d_impeller ** 2) * rho_product) / max(visc_avg_pas, 0.0001)
            Ne_power = AGITATOR_TYPES[typ_wirnika]["laminar_C"] / Re_mixing if Re_mixing < 50 else AGITATOR_TYPES[typ_wirnika]["turbulent_Ne"]
            power_shaft_w = Ne_power * ((obroty_rpm / 60.0) ** 3) * (d_impeller ** 5) * rho_product
            power_mix_kw = max((power_shaft_w / (motor_efficiency / 100.0) * 1.25) / 1000.0, 1.5)
            E_mixing_total_kwh = power_mix_kw * cyc_h

            # --- C. OBLICZENIA POMPY ---
            D_pipe_m = pipe_d_mm / 1000.0
            velocity_m_s = (q_user_m3_h / 3600.0) / ((math.pi * (D_pipe_m ** 2)) / 4.0)
            
            Re_pipe_max = (velocity_m_s * D_pipe_m) / max(visc_max_cst / 1_000_000.0, 0.00001)
            lambda_max = 64.0 / max(Re_pipe_max, 1.0) if Re_pipe_max < 2100 else (0.3164 / (Re_pipe_max ** 0.25))
            press_bar_max = (rho_product * 9.81 * (h_static_m + (lambda_max * (pipe_l_m / D_pipe_m) * ((velocity_m_s ** 2) / (2.0 * 9.81))))) / 100000.0
            power_pump_max_kw = max((q_user_m3_h * press_bar_max) / (36.0 * 0.65) * 1.25, 0.75)
            
            if visc_max_cst > 1500 or press_bar_max > 8.0:
                pump_selected = "Śrubowa (HD)"
            elif visc_max_cst > 300 or visc_min_cst > 50:
                pump_selected = "Krzywkowa (Lobe)"
            else:
                pump_selected = "Odśrodkowa"

            time_pumping_h = v_working / q_user_m3_h

            # Eksport czasów dla Zakładki 4 - teraz jako zsumowana faza Termiki
            st.session_state.calculated_times[tag] = {
                "heating": total_thermal_time,
                "pumping": time_pumping_h
            }

            velocity_status = "❌ Za wysoka (>2.0)" if velocity_m_s > 2.0 else "✅ OK"

            spec_rows.append({
                "Nazwa 🔒": tag,
                "Pojemność [m³]": round(v_working, 1),
                "Grzanie [kWh] 🔥": int(Q_grz_kwh),
                "Chłodzenie [kWh] ❄️": int(Q_chl_kwh),
                "Czas Termiki [h] ⏱️": round(total_thermal_time, 2),
                "Mieszanie [kWh] ⚙️": round(E_mixing_total_kwh, 1),
                "Typ Pompy 🔄": pump_selected,
                "Ciśnienie MAX [bar]": round(press_bar_max, 1),
                "Moc Pompy [kW] ⚡": round(power_pump_max_kw, 1),
                "Prędkość [m/s]": round(velocity_m_s, 2),
                "Status ⚠️": velocity_status
            })

        # --- ZBIORCZA MACIERZ WYNIKOWA NA DOLE ---
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📊 Zbiorcza Karta Specyfikacji (Termika, Mechanika i Hydraulika)")
        
        df_spec = pd.DataFrame(spec_rows)

        def style_velocity_warnings(row):
            styles = [''] * len(row)
            status = row["Status ⚠️"]
            if "Za wysoka" in str(status):
                idx_v = row.index.get_loc("Prędkość [m/s]")
                idx_s = row.index.get_loc("Status ⚠️")
                styles[idx_v] = 'background-color: #fce8e6; color: #a51d24; font-weight: bold;'
                styles[idx_s] = 'background-color: #fce8e6; color: #a51d24; font-weight: bold;'
            else:
                idx_v = row.index.get_loc("Prędkość [m/s]")
                styles[idx_v] = 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
            return styles

        styled_df_spec = df_spec.style.apply(style_velocity_warnings, axis=1)

        st.dataframe(
            styled_df_spec,
            hide_index=True,
            width="stretch",
            column_config={
                "Pojemność [m³]": st.column_config.NumberColumn(format="%.1f"),
                "Grzanie [kWh] 🔥": st.column_config.NumberColumn(format="%d"),
                "Chłodzenie [kWh] ❄️": st.column_config.NumberColumn(format="%d"),
                "Czas Termiki [h] ⏱️": st.column_config.NumberColumn(format="%.2f"),
                "Mieszanie [kWh] ⚙️": st.column_config.NumberColumn(format="%.1f"),
                "Ciśnienie MAX [bar]": st.column_config.NumberColumn(format="%.1f"),
                "Moc Pompy [kW] ⚡": st.column_config.NumberColumn(format="%.1f"),
                "Prędkość [m/s]": st.column_config.NumberColumn(format="%.2f")
            }
        )
# ==========================================
# ZAKŁADKA 3: LOGISTYKA, GOSPODARKA PALETOWA I NALEWAKI PER TYP OPAKOWANIA
# ==========================================
with tab3:
    st.header("📦 Analiza Logistyczna, Czas Rozlewu i Gospodarka Paletowa")

    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.info("💡 Aby przeprowadzić analizę logistyczną, najpierw zatwierdź konfigurację floty w **Zakładce 1**.")
    else:
        mixers_fleet = st.session_state.confirmed_mixers
        opakowania_podzial = st.session_state.get("opakowania_podzial", {})
        
        # 1. DEFINICJA SŁOWNIKA TONAZU MIESIĘCZNEGO (Zabezpieczenie przed NameError)
        tonaz_miesieczny_per_rodzina = {}
        for m in mixers_fleet:
            kat = m["product_family"]
            masa_miesieczna = m["batches_count"] * m["mass_per_batch"]
            tonaz_miesieczny_per_rodzina[kat] = tonaz_miesieczny_per_rodzina.get(kat, 0) + masa_miesieczna

        # Zbieranie wszystkich unikalnych typów opakowań wybranego portfolio
        aktywne_opakowania = set()
        for kat in FUCHS_PORTFOLIO.keys():
            packs = st.session_state.get(f"packs_{kat}", [])
            for p in packs:
                aktywne_opakowania.add(p)
        if not aktywne_opakowania:
            aktywne_opakowania = set(PACK_CONFIGS.keys())

        # --- SEKCJA 1: MATRYCA NALEWAKÓW PER OPAKOWANIE ---
        st.markdown("### 🎛️ 1. Konfiguracja Stanowisk Rozlewniczych per Typ Opakowania")
        st.caption("Każdy gabaryt opakowania posiada własną specyfikę rozlewu. Określ liczbę głowic oraz wydajność masową dla poszczególnych linii.")
        
        if "filling_lines_config" not in st.session_state:
            st.session_state.filling_lines_config = {}
            
        # Domyślne wartości startowe odzwierciedlające fizykę rozlewu
        for p in aktywne_opakowania:
            if p not in st.session_state.filling_lines_config:
                if "5l" in p.lower() or "1l" in p.lower() or "karton" in p.lower() or "small" in p.lower():
                    st.session_state.filling_lines_config[p] = {"nozzles": 4, "speed_kg_min": 15.0}
                elif "200l" in p.lower() or "beczka" in p.lower() or "medium" in p.lower() or "large" in p.lower():
                    st.session_state.filling_lines_config[p] = {"nozzles": 2, "speed_kg_min": 60.0}
                else: # IBC / Bulk
                    st.session_state.filling_lines_config[p] = {"nozzles": 1, "speed_kg_min": 150.0}

        def sync_filling_lines():
            if "filling_editor" in st.session_state:
                edits = st.session_state.filling_editor.get("edited_rows", {})
                pack_list = list(aktywne_opakowania)
                for idx, changes in edits.items():
                    if idx < len(pack_list):
                        p_name = pack_list[idx]
                        if "2. Liczba nalewaków / głowic [szt] 🟦" in changes:
                            st.session_state.filling_lines_config[p_name]["nozzles"] = int(changes["2. Liczba nalewaków / głowic [szt] 🟦"])
                        if "3. Wydajność 1 nalewaka [kg/min] 🟦" in changes:
                            st.session_state.filling_lines_config[p_name]["speed_kg_min"] = float(changes["3. Wydajność 1 nalewaka [kg/min] 🟦"])

        filling_table_rows = []
        for p in aktywne_opakowania:
            cfg = st.session_state.filling_lines_config[p]
            total_kg_h = cfg["nozzles"] * cfg["speed_kg_min"] * 60.0
            filling_table_rows.append({
                "1. Typ Opakowania 🔒": p,
                "2. Liczba nalewaków / głowic [szt] 🟦": int(cfg["nozzles"]),
                "3. Wydajność 1 nalewaka [kg/min] 🟦": float(cfg["speed_kg_min"]),
                "4. Łączna przepustowość sekcji [kg/h] 🔒": round(total_kg_h, 1)
            })

        df_filling_editor = pd.DataFrame(filling_table_rows)
        
        st.data_editor(
            df_filling_editor,
            hide_index=True,
            width="stretch",
            disabled=["1. Typ Opakowania 🔒", "4. Łączna przepustowość sekcji [kg/h] 🔒"],
            column_config={
                "2. Liczba nalewaków / głowic [szt] 🟦": st.column_config.NumberColumn(min_value=1, max_value=24, step=1),
                "3. Wydajność 1 nalewaka [kg/min] 🟦": st.column_config.NumberColumn(min_value=0.5, max_value=500.0, step=5.0),
                "4. Łączna przepustowość sekcji [kg/h] 🔒": st.column_config.NumberColumn(format="%.1f kg/h")
            },
            key="filling_editor",
            on_change=sync_filling_lines
        )

        # Globalny czas rotacji magazynowej
        st.markdown("<br>", unsafe_allow_html=True)
        c_rot1, c_rot2 = st.columns([1, 3])
        with c_rot1:
            czas_skladowania_dni = st.number_input("Czas składowania palety (Rotacja) [dni]:", min_value=1, max_value=90, value=14, step=1)
        dni_robocze_miesiac = 250.0 / 12.0

        st.markdown("---")

        # ==========================================
        # SEKCJA 1: SYMULACJA MIESZANA (REALNY SPLIT + WĄSKIE GARDŁO PER OPAKOWANIE)
        # ==========================================
        st.markdown("### 🔀 2. Symulacja Mieszana (Zoptymalizowany Realny Split i Bufor Paletowy)")
        st.caption("Aplikacja weryfikuje wydajność pompy z Zakładki 2 z wydajnością linii dla danego opakowania i wyznacza maksymalny czas rozlewu.")

        real_split_rows = []
        total_real_pallets_month = 0
        total_real_pallet_slots_needed = 0

        for kat, total_mass_month in tonaz_miesieczny_per_rodzina.items():
            wybrane_dla_linii = st.session_state.get(f"packs_{kat}", [])
            rho_linii = FUCHS_PORTFOLIO[kat]["density"]

            if "Water-miscible" in kat or "ECOCOOL" in kat:
                storage_req = "❄️ Frost Sensitive (Min +5°C), Strefa grzana"
            elif "Engine Oils" in kat:
                storage_req = "🔥 Klasa pożarowa III, Standard"
            else:
                storage_req = "🟢 Standard, Brak obostrzeń"

            for p in wybrane_dla_linii:
                key_id = f"pct_{kat}_{p}"
                udzial_pct = opakowania_podzial.get(key_id, 0.0)
                
                if udzial_pct > 0:
                    masa_opakowania_month = total_mass_month * (udzial_pct / 100.0)
                    pack_capacity_l = PACK_CONFIGS[p]["size_l"]
                    pack_capacity_kg = pack_capacity_l * rho_linii
                    liczba_sztuk_month = math.ceil(masa_opakowania_month / pack_capacity_kg) if pack_capacity_kg > 0 else 0
                    
                    # --- ANALIZA WĄSKIEGO GARDŁA PER TYP OPAKOWANIA ---
                    cfg_fill = st.session_state.filling_lines_config.get(p, {"nozzles": 1, "speed_kg_min": 50.0})
                    sekcja_nalewania_kg_h = cfg_fill["nozzles"] * cfg_fill["speed_kg_min"] * 60.0
                    sekcja_nalewania_m3_h = sekcja_nalewania_kg_h / (rho_linii * 1000.0)

                    m_parent = next((mx for mx in mixers_fleet if mx["product_family"] == kat), None)
                    q_pump_m3h = st.session_state.get("pump_flows", {}).get(m_parent["tag"], m_parent["capacity_m3"] / 0.75) if m_parent else 15.0

                    q_effective_flow_m3h = min(q_pump_m3h, sekcja_nalewania_m3_h)
                    
                    objętosc_strumienia_m3 = masa_opakowania_month / (rho_linii * 1000.0)
                    czas_rozlewu_h = objętosc_strumienia_m3 / q_effective_flow_m3h if q_effective_flow_m3h > 0 else 0.0
                    
                    szt_na_palecie = PACK_CONFIGS[p]["per_pallet"]
                    liczba_palet_month = math.ceil(liczba_sztuk_month / szt_na_palecie) if szt_na_palecie > 0 else 0
                    total_real_pallets_month += liczba_palet_month
                    
                    miejsca_paletowe_w_magazynie = math.ceil((liczba_palet_month / dni_robocze_miesiac) * czas_skladowania_dni)
                    total_real_pallet_slots_needed += miejsca_paletowe_w_magazynie
                    
                    limiter = "⚓ Pompa tłoczna" if q_pump_m3h < sekcja_nalewania_m3_h else f"🍼 Liniowe Nalewaki ({cfg_fill['nozzles']} gł.)"

                    real_split_rows.append({
                        "Linia produktowa 🔒": kat,
                        "Typ Opakowania 📦": p,
                        "Udział [%]": f"{udzial_pct:.1f}%",
                        "Liczba opakowań [/mies]": int(liczba_sztuk_month),
                        "Palety [EPAL/mies] 🧱": int(liczba_palet_month),
                        "Wymagane Miejsca Paletowe [szt] 📐": int(miejsca_paletowe_w_magazynie),
                        "Czas rozlewu strumienia [h] ⏱️": round(czas_rozlewu_h, 1),
                        "Element ograniczający (Wąskie gardło)": limiter,
                        "Wymagania Przechowywania ⚠️": storage_req
                    })

        if real_split_rows:
            df_real_split = pd.DataFrame(real_split_rows)
            st.dataframe(
                df_real_split,
                hide_index=True,
                width="stretch",
                column_config={
                    "Liczba opakowań [/mies]": st.column_config.NumberColumn(format="%d szt."),
                    "Palety [EPAL/mies] 🧱": st.column_config.NumberColumn(format="%d EPAL"),
                    "Wymagane Miejsca Paletowe [szt] 📐": st.column_config.NumberColumn(format="%d miejsc"),
                    "Czas rozlewu strumienia [h] ⏱️": st.column_config.NumberColumn(format="%.1f h")
                }
            )
# ==========================================
# ZAKŁADKA 4: FINANSE ORAZ INTEGRACJA CYKLU CZASOWEGO FABRYKI
# ==========================================
with tab4:
    st.header("💰 Optymalizacja Kosztów Energii i Bilans Finansowy")
    if "confirmed_mixers" not in st.session_state or not st.session_state.confirmed_mixers:
        st.warning("⚠️ Brak danych technicznych. Uruchom konfigurację i zatwierdź flotę w Zakładce 1.")
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
            tag = mixer["tag"]
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            m_monthly_kg = mixer["annual_volume"] / 12
            batches_per_month = mixer["batches_count"]
            
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
            
            t_max_mix = st.session_state.heat_temps.get(tag, 60.0)
            t_rozlew = st.session_state.filling_temps.get(tag, 30.0)
            base_manuf_cost_monthly = m_monthly_kg * manuf_cost_per_kg
            total_base_manuf_cost += base_manuf_cost_monthly
            
            oszczednosc_cieplna_mies = 0.0
            if t_rozlew < t_max_mix:
                energia_cieplna_mwh_mies = (m_monthly_kg * prod_info["cp"] * (t_max_mix - t_rozlew)) / 3_600_000.0
                oszczednosc_cieplna_mies = energia_cieplna_mwh_mies * cena_mwh
                total_monthly_saving_thermal += oszczednosc_cieplna_mies
                
            financial_summary.append({
                "Reaktor": tag, "Miesięczny tonaż [kg]": int(m_monthly_kg),
                "Energia Mieszania [kWh/m]": round(mixing_energy_month_kwh, 1), "Energia Pompowania [kWh/m]": round(pumping_energy_month_kwh, 1),
                "Koszt energii el.": f"{cost_el_node:.2f} {waluta}", "Oszczędność termiczna": f"- {oszczednosc_cieplna_mies:.2f} {waluta}"
            })
            
        st.dataframe(pd.DataFrame(financial_summary), hide_index=True, width="stretch")
        
        st.markdown("<br>", unsafe_allow_html=True)
        cost_total_el = ((total_mixing_energy_kwh + total_pumping_energy_kwh) / 1000.0) * cena_mwh
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1: st.metric("⚙️ Zużycie: Mieszanie", f"{total_mixing_energy_kwh:,.1f} kWh/m")
        with s_col2: st.metric("🔄 Zużycie: Przepompowanie", f"{total_pumping_energy_kwh:,.1f} kWh/m")
        with s_col3: st.metric("🔌 Łączny koszt energii el.", f"{cost_total_el:,.2f} {waluta}/mies")
        
        st.markdown("---")
        final_manufacturing_cost = total_base_manuf_cost + cost_total_el - total_monthly_saving_thermal
        st.metric(label="🚀 ZOPTYMALIZOWANY REALNY KOSZT WYTWORZENIA (Miesięcznie)", value=f"{final_manufacturing_cost:,.2f} {waluta}")

# ==========================================
        # ZAKTUALIZOWANA SEKCJA 2 W ZAKŁADCE 4: REALNY PEŁNY CYKL PROCESOWY
        # ==========================================
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### ⏱️ 2. Realna Analiza Czasu Cyklu i Optymalizacja Zmianowa")
        st.info("💡 **Dopełnienie procesu:** Czas podgrzewania oraz rozładunku (pompy) pochodzą z Zakładki 2. Poniżej uwzględniono brakujący czas homogenizacji.")

        time_analysis_rows = []
        calculated_times = st.session_state.get("calculated_times", {})

        for mixer in st.session_state.confirmed_mixers:
            tag = mixer["tag"]
            kat = mixer["product_family"]
            
            # Pobranie precyzyjnych, fizycznych czasów z Zakładki 2
            mixer_times = calculated_times.get(tag, {"heating": 1.5, "pumping": 0.75})
            t_heat_calc = mixer_times["heating"]
            t_pump_calc = mixer_times["pumping"]

            # POPRAWKA LAYOUTU: Bardzo krótkie etykiety + parametr help = równe okienka!
            with st.expander(f"⏱️ Składniki czasu cyklu dla aparatu: {tag} ({kat})", expanded=True):
                c_t1, c_t2, c_t3 = st.columns(3)
                with c_t1:
                    t_dosing = st.number_input(
                        "Dozowanie [h]:", 
                        min_value=0.1, max_value=6.0, value=1.0, step=0.25, key=f"tdos_{tag}", 
                        help=f"Czas dozowania baz i dodatków do reaktora {tag}."
                    )
                with c_t2:
                    nominal_cycle = float(FUCHS_PORTFOLIO[kat]["cycle_h"])
                    default_homog = max(0.5, round(nominal_cycle - t_heat_calc, 2))
                    t_homogenization = st.number_input(
                        "Homogenizacja [h]:", 
                        min_value=0.1, max_value=12.0, value=default_homog, step=0.5, key=f"thom_{tag}", 
                        help=f"Czas właściwego mieszania w {tag} po osiągnięciu zadanej temperatury."
                    )
                with c_t3:
                    t_qc = st.number_input(
                        "Kontrola QC [h]:", 
                        min_value=0.1, max_value=6.0, value=1.0, step=0.25, key=f"tqc_{tag}", 
                        help=f"Zatwierdzenie i zwolnienie przez laboratorium dla {tag}."
                    )

            # Wyznaczenie pełnego, realnego łańcucha operacji szarży
            t_total_chain = t_dosing + t_heat_calc + t_homogenization + t_qc + t_pump_calc
            
            # RESTRYKCYJNE KRYTERIUM ZMIANOWE (Warunek 8 godzin)
            if t_total_chain <= 8.0:
                rekomendacja_zmian = "🟢 Dwuzmianowa (Cykl <= 8h)"
            else:
                rekomendacja_zmian = "🔴 Jednozmianowa (Cykl > 8h)"

            time_analysis_rows.append({
                "ID Mieszalnika 🔒": tag,
                "Przypisana Linia FUCHS 🔒": kat,
                "Dozowanie [h]": t_dosing,
                "Podgrzewanie [h] 🔒": round(t_heat_calc, 2),
                "Homogenizacja [h]": t_homogenization,
                "Kontrola QC [h]": t_qc,
                "Rozlewanie [h] 🔒": round(t_pump_calc, 2),
                "Pełny łańcuch [h] 🔒": round(t_total_chain, 2),
                "System zmianowy ⚠️": rekomendacja_zmian
            })

        df_time_analysis = pd.DataFrame(time_analysis_rows)

        # Funkcja stylizująca i podświetlająca reaktory przekraczające normatyw 8h
        def style_time_chains(row):
            styles = [''] * len(row)
            val = row["Pełny łańcuch [h] 🔒"]
            if isinstance(val, (int, float)) and val > 8.0:
                idx_t = row.index.get_loc("Pełny łańcuch [h] 🔒")
                idx_r = row.index.get_loc("System zmianowy ⚠️")
                styles[idx_t] = 'background-color: #fce8e6; color: #a51d24; font-weight: bold;'
                styles[idx_r] = 'background-color: #fce8e6; color: #a51d24; font-weight: bold;'
            else:
                idx_t = row.index.get_loc("Pełny łańcuch [h] 🔒")
                styles[idx_t] = 'background-color: #e6f4ea; color: #137333; font-weight: bold;'
            return styles

        styled_df_time = df_time_analysis.style.apply(style_time_chains, axis=1)

        # Wyświetlenie zaktualizowanej, kompletnej tabeli w standardzie stretch
        st.dataframe(
            styled_df_time,
            hide_index=True,
            width="stretch",
            column_config={
                "Dozowanie [h]": st.column_config.NumberColumn(format="%.2f h"),
                "Podgrzewanie [h] 🔒": st.column_config.NumberColumn(format="%.2f h"),
                "Homogenizacja [h]": st.column_config.NumberColumn(format="%.2f h"),
                "Kontrola QC [h]": st.column_config.NumberColumn(format="%.2f h"),
                "Rozlewanie [h] 🔒": st.column_config.NumberColumn(format="%.2f h"),
                "Pełny łańcuch [h] 🔒": st.column_config.NumberColumn(format="%.2f h")
            }
        )

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
