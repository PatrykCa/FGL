import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Kreator Linii FUCHS Portfolio", layout="wide")

st.title("🏭 Kompleksowy Kreator Produkcyjny FUCHS Oil")
st.subheader("Zarządzanie Wolumenami i Gabarytami Aparatury (Forma Tabeli Zbiorczej)")
st.markdown("---")

# --- 1. BAZA DANYCH RODZIN PRODUKTOWYCH FUCHS ---
FUCHS_PORTFOLIO = {
    "Industrial: Hydraulic Oils (RENOLIN)": {"material": "Stal węglowa", "density": 0.88, "cycle_h": 4, "cp": 2.0, "flash": "220°C", "visc": "46 mm²/s", "frost": "Nie"},
    "Industrial: Gear & Turbine Oils (RENOLIN)": {"material": "Stal węglowa", "density": 0.89, "cycle_h": 5, "cp": 1.9, "flash": "240°C", "visc": "220 mm²/s", "frost": "Nie"},
    "Industrial: Slideway & Machine Oils (RENAX)": {"material": "Stal węglowa", "density": 0.88, "cycle_h": 4, "cp": 2.0, "flash": "210°C", "visc": "68 mm²/s", "frost": "Nie"},
    "Automotive: Engine Oils (TITAN)": {"material": "Stal węglowa", "density": 0.87, "cycle_h": 5, "cp": 2.1, "flash": "230°C", "visc": "11.5 mm²/s", "frost": "Nie"},
    "Automotive: Gear & Transmission Oils (TITAN)": {"material": "Stal węglowa", "density": 0.88, "cycle_h": 5, "cp": 2.0, "flash": "210°C", "visc": "14.0 mm²/s", "frost": "Nie"},
    "Metal Processing: Water-miscible (ECOCOOL)": {"material": "Stal nierdzewna", "density": 0.99, "cycle_h": 6, "cp": 3.8, "flash": "Brak", "visc": "60 mm²/s", "frost": "TAK"},
    "Metal Processing: Non-water-miscible (ECOCUT)": {"material": "Stal węglowa", "density": 0.87, "cycle_h": 4, "cp": 2.0, "flash": "190°C", "visc": "22 mm²/s", "frost": "Nie"},
    "Metal Processing: Cleaners (RENOCLEAN)": {"material": "Stal nierdzewna", "density": 1.01, "cycle_h": 4, "cp": 3.9, "flash": "Brak", "visc": "5 mm²/s", "frost": "TAK"}
}

PACK_SIZES = {
    "1l (Detal)": 1.0, "4l (Karton)": 4.0, "5l (Karton)": 5.0, 
    "10l (Kanister)": 10.0, "20l (Kanister)": 20.0, 
    "60l (Beczka)": 60.0, "200l (Beczka)": 200.0, "1000l (IBC)": 1000.0
}

AVAILABLE_HOURS_MONTH = (250 * 16) / 12  # ~333.33 h/miesiąc

# --- 2. PANEL BOCZNY ---
st.sidebar.header("📋 KROK 1: Wybór Rodzin FUCHS")
wybrane_kategorie = st.sidebar.multiselect(
    "Wybierz rodziny produktowe:",
    list(FUCHS_PORTFOLIO.keys()),
    default=["Industrial: Hydraulic Oils (RENOLIN)", "Automotive: Engine Oils (TITAN)", "Metal Processing: Water-miscible (ECOCOOL)"]
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ KROK 2: Dane wejściowe")
input_data = {}
for kat in wybrane_kategorie:
    st.sidebar.markdown(f"### 🧪 {kat}")
    vol = st.sidebar.number_input(f"Roczna produkcja [kg]:", min_value=0, value=1200000, step=100000, key=f"vol_{kat}")
    packs = st.sidebar.multiselect(
        "Opakowania końcowe (FL):",
        list(PACK_SIZES.keys()) + ["Bulk (Cysterna luz)"],
        default=["200l (Beczka)", "1000l (IBC)"],
        key=f"packs_{kat}"
    )
    input_data[kat] = {"wolumen": vol, "opakowania": packs}

# Inicjalizacja stanów dla tabeli głównej
if "df_products" not in st.session_state or st.sidebar.button("🔄 Resetuj / Aktualizuj listę z panelu bocznego"):
    data_rows = []
    for kat in wybrane_kategorie:
        if input_data[kat]["wolumen"] > 0:
            m_production_kg = input_data[kat]["wolumen"] / 12
            dens = FUCHS_PORTFOLIO[kat]["density"]
            cyc = FUCHS_PORTFOLIO[kat]["cycle_h"]
            
            # Rekomendacja (75%)
            sys_szarze = round((AVAILABLE_HOURS_MONTH * 0.75) / cyc, 1)
            sys_m3 = (m_production_kg / sys_szarze) / (dens * 1000)
            sys_m3 = max(0.5, math.ceil(sys_m3 * 2) / 2)
            
            data_rows.append({
                "Produkt (Rodzina)": kat.split(":")[-1].strip(),
                "Pełna Nazwa": kat,
                "Produkcja [kg/m]": int(m_production_kg),
                "Rekomend. Pojemność [m³]": float(sys_m3),
                "Rekomend. Szarże [szt/m]": float(sys_szarze),
                "Rekomend. Utylizacja [%]": 75.0,
                "Zsymulowana Pojemność [m³]": float(sys_m3),
                "Zsymulowane Szarże [szt/m]": float(sys_szarze),
                "Zsymulowana Utylizacja [%]": 75.0,
                "Zatwierdź Opcję": "Rekomendowana"
            })
    st.session_state.df_products = pd.DataFrame(data_rows)

if "confirmed_setup" not in st.session_state:
    st.session_state.confirmed_setup = {}

tab1, tab2 = st.tabs(["📊 1. Logistyka Szarż i Zbiorniki", "📐 2. Specyfikacja Ciągu Technologicznego (P&ID)"])

with tab1:
    st.header("Zestawienie Wolumenów i Parametrów Szarż")
    st.caption("Wskazówka: Możesz edytować wartości w sekcji 'Zsymulowana...' bezpośrednio w komórkach tabeli poniżej. Zmiana jednej wartości automatycznie przeliczy pozostałe dwa parametry w wierszu.")
    
    if not st.session_state.df_products.empty:
        # --- SILNIK POWIĄZAŃ (DWUKIERUNKOWOŚĆ) DZIAŁAJĄCY NA CAŁEJ TABELI ---
        def handle_matrix_change():
            edited_df = st.session_state["prod_editor"]["edited_rows"]
            old_df = st.session_state.df_products
            
            for row_idx, changes in edited_df.items():
                kat_full = old_df.loc[row_idx, "Pełna Nazwa"]
                m_prod = old_df.loc[row_idx, "Produkcja [kg/m]"]
                d = FUCHS_PORTFOLIO[kat_full]["density"]
                c = FUCHS_PORTFOLIO[kat_full]["cycle_h"]
                
                # Przypisujemy wartości bazowe (przed zmianą)
                v_val = old_df.loc[row_idx, "Zsymulowana Pojemność [m³]"]
                s_val = old_df.loc[row_idx, "Zsymulowane Szarże [szt/m]"]
                u_val = old_df.loc[row_idx, "Zsymulowana Utylizacja [%]"]
                
                # Sprawdzamy, która kolumna została zmieniona i wyliczamy resztę rzędu
                if "Zsymulowana Pojemność [m³]" in changes:
                    v_val = changes["Zsymulowana Pojemność [m³]"]
                    if v_val > 0:
                        s_val = round(m_prod / (v_val * d * 1000), 1)
                        u_val = round((s_val * c / AVAILABLE_HOURS_MONTH) * 100, 1)
                elif "Zsymulowane Szarże [szt/m]" in changes:
                    s_val = changes["Zsymulowane Szarże [szt/m]"]
                    if s_val > 0:
                        v_val = round(max(0.5, math.ceil((m_prod / (s_val * d * 1000)) * 2) / 2), 1)
                        u_val = round((s_val * c / AVAILABLE_HOURS_MONTH) * 100, 1)
                elif "Zsymulowana Utylizacja [%]" in changes:
                    u_val = changes["Zsymulowana Utylizacja [%]"]
                    s_val = round(((u_val / 100) * AVAILABLE_HOURS_MONTH) / c, 1)
                    if s_val > 0:
                        v_val = round(max(0.5, math.ceil((m_prod / (s_val * d * 1000)) * 2) / 2), 1)
                
                # Zapisujemy wyliczone wartości z powrotem do rzędu
                old_df.loc[row_idx, "Zsymulowana Pojemność [m³]"] = float(v_val)
                old_df.loc[row_idx, "Zsymulowane Szarże [szt/m]"] = float(s_val)
                old_df.loc[row_idx, "Zsymulowana Utylizacja [%]"] = float(u_val)
                
                if "Zatwierdź Opcję" in changes:
                    old_df.loc[row_idx, "Zatwierdź Opcję"] = changes["Zatwierdź Opcję"]
            
            st.session_state.df_products = old_df

        # WIZUALIZACJA TABELI GŁÓWNEJ (Zablokowane kolumny rekomendacji, edytowalne kolumny użytkownika)
        edited_table = st.data_editor(
            st.session_state.df_products,
            key="prod_editor",
            on_change=handle_matrix_change,
            disabled=["Produkt (Rodzina)", "Pełna Nazwa", "Produkcja [kg/m]", "Rekomend. Pojemność [m³]", "Rekomend. Szarże [szt/m]", "Rekomend. Utylizacja [%]"],
            column_config={
                "Pełna Nazwa": None, # ukrywamy kolumnę techniczną
                "Zatwierdź Opcję": st.column_config.SelectboxColumn("Wariant dla projektu", options=["Rekomendowana", "Użytkownika"], width="medium"),
                "Produkcja [kg/m]": st.column_config.NumberColumn(format="%d kg"),
                "Zsymulowana Utylizacja [%]": st.column_config.NumberColumn(min_value=0.1, max_value=200.0)
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Pojedynczy centralny przycisk zamrożenia całej konfiguracji tabelarycznej
        st.markdown("---")
        if st.button("🔒 ZATWIERDŹ I WYŚLIJ CAŁĄ TABELĘ DO PROJEKTU TECHNICZNEGO"):
            new_confirmed = {}
            for idx, row in edited_table.iterrows():
                kat_key = row["Pełna Nazwa"]
                if row["Zatwierdź Opcję"] == "Rekomendowana":
                    new_confirmed[kat_key] = {
                        "capacity": row["Rekomend. Pojemność [m³]"], "batches": row["Rekomend. Szarże [szt/m]"], "utilization": row["Rekomend. Utylizacja [%]"], "opakowania": input_data[kat_key]["opakowania"]
                    }
                else:
                    new_confirmed[kat_key] = {
                        "capacity": row["Zsymulowana Pojemność [m³]"], "batches": row["Zsymulowane Szarże [szt/m]"], "utilization": row["Zsymulowana Utylizacja [%]"], "opakowania": input_data[kat_key]["opakowania"]
                    }
            st.session_state.confirmed_setup = new_confirmed
            st.success("✔️ Cała konfiguracja została pomyślnie zamrożona i przesłana. Przejdź do Zakładki 2!")

        # --- SEKCJA LOGISTYKI OPAKOWAŃ POD TABELĄ ---
        st.markdown("### 📦 Logistyka i zapotrzebowanie na opakowania (Miesięcznie)")
        for idx, row in edited_table.iterrows():
            kat_key = row["Pełna Nazwa"]
            chosen_packs = input_data[kat_key]["opakowania"]
            if chosen_packs:
                st.markdown(f"**Dla produktu: {row['Produkt (Rodzina)']}**")
                num_pack_types = len(chosen_packs)
                mass_per_type_l = (row["Produkcja [kg/m]"] / FUCHS_PORTFOMIO := FUCHS_PORTFOLIO[kat_key]["density"]) / num_pack_types
                
                pack_cols = st.columns(num_pack_types)
                for p_idx, pack_name in enumerate(chosen_packs):
                    with pack_cols[p_idx]:
                        if pack_name in PACK_SIZES:
                            cap_l = PACK_SIZES[pack_name]
                            total_szt = math.ceil(mass_per_type_l / cap_l)
                            st.metric(label=pack_name, value=f"{total_szt:,} szt.")
                        else:
                            total_trucks = round((row["Produkcja [kg/m]"] / num_pack_types) / 24000, 1)
                            st.metric(label="Transport: Bulk", value=f"{total_trucks} cystern")
    else:
        st.info("Wybierz rodziny produktowe o wolumenie większym niż 0 w panelu bocznym.")

with tab2:
    st.header("📐 Inżynieryjna Specyfikacja Ciągu Technologicznego")
    
    if not st.session_state.confirmed_setup:
        st.info("ℹ️ Aby wygenerować specyfikację techniczną, zatwierdź tabelę główną w Zakładki 1 przyciskiem '🔒 Zatwierdź i wyślij'.")
    else:
        rows = []
        idx = 101
        for kat, dane in st.session_state.confirmed_setup.items():
            rules = FUCHS_PORTFOLIO[kat]
            v_final = dane["capacity"]
            opakowania_str = ", ".join(dane["opakowania"]) if dane["opakowania"] else "Brak"
            
            rows.append({
                "Tag Mieszalnika": f"MT-{idx}",
                "Rodzina Produktowa": kat.split(":")[-1].strip(),
                "Pojemność [m³]": f"{v_final:.1f} m³",
                "Szarże / miesiąc": dane["batches"],
                "Obłożenie (%)": f"{dane['utilization']:.1f}%",
                "Materiał (Stal)": rules["material"],
                "Flash Point": rules["flash"],
                "Viscosity": rules["visc"],
                "Frost Sensitivity": rules["frost"],
                "Masa Szarży [kg]": v_final * rules["density"] * 1000,
                "cp": rules["cp"],
                "Opakowania": opakowania_str
            })
            idx += 1
            
        df_ins = pd.DataFrame(rows)
        
        st.markdown("#### 🌡️ Parametry Procesowe i Bilans Cieplny")
        final_table_data = []
        for index, row in df_ins.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 3, 3])
                with c1:
                    st.markdown(f"**{row['Tag Mieszalnika']}**<br><small>{row['Rodzina Produktowa']}</small>", unsafe_allowed_html=True)
                    st.caption(f"Opakowania: {row['Opakowania']}")
                with c2:
                    dt_heat = st.number_input(f"ΔT grzania [°C] ({row['Tag Mieszalnika']}):", value=40, step=5, key=f"dth_{row['Tag Mieszalnika']}")
                    total_heat_gj = (row["Masa Szarży [kg]"] * row["cp"] * dt_heat * row["Szarże / miesiąc"]) / (1_000_000 * 0.85)
                with c3:
                    dt_cool = st.number_input(f"ΔT chłodzenia [°C] ({row['Tag Mieszalnika']}):", value=30, step=5, key=f"dtc_{row['Tag Mieszalnika']}")
                    total_cool_gj = (row["Masa Szarży [kg]"] * row["cp"] * dt_cool * row["Szarże / miesiąc"]) / (1_000_000 * 0.85)
                
                final_table_data.append({
                    "Tag": row["Tag Mieszalnika"],
                    "Produkt": row["Rodzina Produktowa"],
                    "Pojemność": row["Pojemność [m³]"],
                    "Stal": row["Materiał (Stal)"],
                    "Ciepło grzania [GJ/m]": f"{total_heat_gj:.2f} GJ",
                    "Ciepło chłodzenia [GJ/m]": f"{total_cool_gj:.2f} GJ",
                    "Flash Point": row["Flash Point"],
                    "Lepkość": row["Viscosity"],
                    "Wrażliwość na mróz": row["Frost Sensitivity"]
                })
        
        st.markdown("---")
        st.markdown("### 📋 Zbiorcza Tabela Technologiczna")
        st.table(pd.DataFrame(final_table_data))
