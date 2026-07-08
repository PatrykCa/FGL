import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="System Projektowania FUCHS", layout="wide")

st.title("🏭 Inżynieryjny Reaktor Procesowy & Logistyczny FUCHS Oil")
st.subheader("Uproszczone Wymiarowanie Linii Produkcyjnych na Podstawie Zadanych Parametrów")
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

# --- PANEL BOCZNY (TYLKO WYBÓR I PODSTAWOWY WOLUMEN) ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz aktywne linie produktowe FUCHS:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Roczne Wolumeny & Opakowania")
input_data = {}

for kat in wybrane_kategorie:
    short_name = kat.split(':')[-1].strip()
    st.sidebar.markdown(f"### 🧪 {short_name}")
    
    vol = st.sidebar.number_input("Roczna produkcja [kg]:", min_value=0, value=1200000, step=100000, key=f"vol_{kat}")
    
    packs = st.sidebar.multiselect(
        "Opakowania końcowe:",
        list(PACK_CONFIGS.keys()) + ["Bulk (Cysterna luz)"],
        default=["200l (Beczka)", "1000l (IBC)"],
        key=f"packs_{kat}"
    )
    input_data[kat] = {"wolumen": vol, "opakowania": packs}

# Inicjalizacja stanu sesji dla zachowania spójności danych między zakładkami
if "confirmed_mixers" not in st.session_state:
    st.session_state.confirmed_mixers = []

# --- KREOWANIE TRZECH ZAKŁADEK ---
tab1, tab2, tab3 = st.tabs([
    "📊 1. Główne Zestawienie i Szarże", 
    "📐 2. Karta Techniczna Maszyn i Hydrodynamika", 
    "📦 3. Bilans Magazynowy i Miejsca Paletowe"
])

# ==========================================
# ZAKŁADKA 1: NOWA UPROSZCZONA STRONA GŁÓWNA
# ==========================================
with tab1:
    st.header("Główne parametry procesowe węzła")
    
    if wybrane_kategorie:
        # Przygotowanie danych wejściowych do interaktywnej tabeli (data_editor)
        raw_rows = []
        for kat in wybrane_kategorie:
            short_name = kat.split(":")[-1].strip()
            v_annual = input_data[kat]["wolumen"]
            
            # Wartości domyślne dla edytowalnych pól, pobierane z sesji lub standardowe
            default_util = 75.0
            default_batch_size = 8800.0 if "Water-miscible" not in kat else 9900.0 # ~10m3 na bazie gęstości
            
            raw_rows.append({
                "Nazwa rodziny": short_name,
                "Roczna produkcja [kg]": int(v_annual),
                "Utilization %": default_util,
                "Wielkość pojedynczej szarży [kg]": default_batch_size,
                "full_key": kat # ukryty klucz pomocniczy
            })
            
        df_to_edit = pd.DataFrame(raw_rows)
        
        st.markdown("💡 *Kolumny oznaczone kolorem niebieskim są edytowalne. Zmień wartości Obłożenia lub Wielkości szarży bezpośrednio w tabeli, aby natychmiast przeliczyć proces.*")
        
        # Konfiguracja kolumn i wyróżnienie pól wejściowych za pomocą st.column_config
        edited_df = st.data_editor(
            df_to_edit,
            hide_index=True,
            use_container_width=True,
            disabled=["Nazwa rodziny"], # Blokada edycji nazw rodzin
            column_config={
                "Nazwa rodziny": st.column_config.TextColumn("1. Nazwa rodziny"),
                "Roczna produkcja [kg]": st.column_config.NumberColumn(
                    "2. Roczna produkcja [kg]", 
                    help="Wartość zdefiniowana w panelu bocznym",
                    required=True
                ),
                "Utilization %": st.column_config.NumberColumn(
                    "3. Utilization % (Wpisz)", 
                    min_value=1, max_value=100, step=5, 
                    help="Wpisz pożądane obłożenie węzła (pole edytowalne)",
                    required=True
                ),
                "Wielkość pojedynczej szarży [kg]": st.column_config.NumberColumn(
                    "5. Wielkość pojedynczej szarży [kg] (Wpisz)", 
                    min_value=100, max_value=50000, step=500,
                    help="Wpisz masę jednej szarży (pole edytowalne)",
                    required=True
                ),
                "full_key": None # ukrycie kolumny technicznej
            }
        )
        
        # --- OBLICZENIA I GENEROWANIE KOLUMNY WYLICZONEJ (LICZBA SZARŻ NA MIESIĄC) ---
        calculated_rows = []
        confirmed_list_temp = []
        
        st.markdown("### 📊 Wynikowe zestawienie operacyjne")
        
        for idx, row in edited_df.iterrows():
            m_annual = row["Roczna produkcja [kg]"]
            m_monthly = m_annual / 12
            batch_size_kg = row["Wielkość pojedynczej szarży [kg]"]
            
            # Liczba szarż wyliczona jako liczba całkowita (zaokrąglona w górę)
            if batch_size_kg > 0:
                needed_batches = math.ceil(m_monthly / batch_size_kg)
            else:
                needed_batches = 0
                
            calculated_rows.append({
                "1. Nazwa rodziny": row["Nazwa rodziny"],
                "2. Roczna produkcja [kg]": f"{int(m_annual):,}",
                "3. Utilization %": f"{row['Utilization %']}%",
                "4. Liczba szarż na miesiąc [całkowita]": int(needed_batches),
                "5. Wielkość pojedynczej szarży [kg]": f"{int(batch_size_kg):,}"
            })
            
            # Wsteczna kalkulacja dla potrzeb hydrodynamiki w Zakładce 2
            original_key = row["full_key"]
            dens = FUCHS_PORTFOLIO[original_key]["density"]
            calculated_vol_m3 = batch_size_kg / (dens * 1000.0) if batch_size_kg > 0 else 1.0
            
            confirmed_list_temp.append({
                "tag": f"MT-{101 + idx}",
                "product_family": original_key,
                "capacity_m3": calculated_vol_m3,
                "material": FUCHS_PORTFOLIO[original_key]["material"],
                "batches_count": needed_batches,
                "mass_per_batch": batch_size_kg
            })
            
        # Wyświetlenie końcowej tabeli wynikowej o czystej, czytelnej strukturze
        st.dataframe(pd.DataFrame(calculated_rows), hide_index=True, use_container_width=True)
        
        # Zapisanie stanu maszyn dla Zakładki 2 i 3
        st.session_state.confirmed_mixers = confirmed_list_temp
        
    else:
        st.warning("Wybierz przynajmniej jedną rodzinę produktów w panelu bocznym.")

# ==========================================
# ZAKŁADKA 2: SPECYFIKACJA URZĄDZEŃ
# ==========================================
with tab2:
    st.header("Karty Charakterystyki Technicznej i Energetycznej Aparatów")
    
    if not st.session_state.confirmed_mixers:
        st.info("ℹ️ Wybierz produkty na stronie głównej, aby wyświetlić parametry inżynieryjne.")
    else:
        engineering_table_data = []
        
        for mixer in st.session_state.confirmed_mixers:
            kat = mixer["product_family"]
            prod_info = FUCHS_PORTFOLIO[kat]
            
            st.markdown(f"### ⚙️ Profil Technologiczny: **{mixer['tag']}** (Dedykowany dla: *{mixer['1. Nazwa rodziny' if '1. Nazwa rodziny' in mixer else kat.split(':')[-1].strip()]}*)")
            
            rho = prod_info["density"] * 1000.0  
            v_kin = prod_info["visc_kin"] / 1_000_000.0  
            eta_dyn = v_kin * rho  
            
            # Skalowanie mieszadła pod zmienną geometrię wynikającą ze zdefiniowanej masy szarży
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
            * **Materiał konstrukcyjny reaktora:** `{mixer['material']}` | **Wyliczona pojemność robocza miksera:** `{mixer['capacity_m3']:.2f} m³`
            * **Reologia:** lepkość kinematyczna `{prod_info['visc_kin']} mm²/s` | **Liczba Reynoldsa (Re):** `{Re:,.1f}`
            * ⚡ **Moc znamionowa napędu:** `{P_kw:.2f} kW` | **Pobór energii mechanicznej:** `{E_mix_mj:.1f} MJ/szarżę`
            * 🔥 **Ciepło technologiczne:** `{Q_heat_mj:,.1f} MJ/szarżę` | ❄️ **Zapotrzebowanie na chłód:** `{Q_cool_mj:,.1f} MJ/szarżę`
            """)
            
            engineering_table_data.append({
                "Mieszalnik": mixer["tag"],
                "Materiał": mixer["material"],
                "Pojemność [m³]": round(mixer["capacity_m3"], 2),
                "Wielkość szarży [kg]": int(mixer["mass_per_batch"]),
                "Moc układu [kW]": round(P_kw, 2),
                "Ciepło grzania [MJ]": round(Q_heat_mj, 1),
                "Chłód procesowy [MJ]": round(Q_cool_mj, 1),
                "Klasyfikacja zapłonu": prod_info["flash_point"]
            })
            st.markdown("---")
            
        st.subheader("📋 Zbiorcza Tabela Inżynieryjna")
        st.dataframe(pd.DataFrame(engineering_table_data), hide_index=True, use_container_width=True)

# ==========================================
# ZAKŁADKA 3: LOGISTYKA OPAKOWAŃ I PALET
# ==========================================
with tab3:
    st.header("Zliczanie Jednostek Opakowaniowych i Wymiarowanie Magazynu")
    
    total_pallets_all = 0
    pallet_rows = []
    
    for mixer in st.session_state.confirmed_mixers:
        kat = mixer["product_family"]
        v_annual = input_data[kat]["wolumen"]
        chosen_packs = input_data[kat]["opakowania"]
        
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
                    "Kontrola Temperatury (Frost)": FUCHS_PORTFOLIO[kat]["frost_sensitivity"]
                })
            st.markdown("<br>", unsafe_allow_html=True)
            
    if pallet_rows:
        st.markdown("---")
        st.subheader("📋 Miesięczny Bilans Powierzchni Składowania")
        df_pallets = pd.DataFrame(pallet_rows)
        st.dataframe(df_pallets, hide_index=True, use_container_width=True)
