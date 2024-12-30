import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from io import BytesIO
from datetime import datetime

# If you want st-aggrid for advanced table controls, uncomment and install:
# pip install streamlit-aggrid
# from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode

# ---------------------------------------------------------
#                   DATA LOADING & CACHING
# ---------------------------------------------------------
@st.cache_data
def load_data() -> pd.DataFrame:
    """
    Load and validate grow light data from a specified Excel file.
    Using Streamlit's cache to speed up re-runs.
    """
    try:
        # Hard-coded file path (adjust as needed):
        file_path = "C:/Users/BZL03/Downloads/DLC data.xlsx"
        
        # Check local file path if it's a string
        if isinstance(file_path, str) and not Path(file_path).exists():
            st.error(f"Data file not found at: {file_path}")
            return pd.DataFrame()  # or return None
        
        # Read the Excel file
        df = pd.read_excel(file_path, engine='openpyxl')
        
        # Convert numeric columns by pattern
        numeric_patterns = [
            'Flux', 'Efficacy', 'Wattage', 'Voltage', 
            'Factor', 'Distortion', 'Temp', 'Diameter', 
            'Length', 'Width', 'Height'
        ]
        for col in df.columns:
            if any(pattern in col for pattern in numeric_patterns):
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convert Date Qualified if it exists
        if 'Date Qualified' in df.columns:
            df['Date Qualified'] = pd.to_datetime(df['Date Qualified'], errors='coerce')
        
        # Basic sanity check for a few required columns
        required_columns = [
            'Manufacturer',
            'Model Number',
            'Reported Input Wattage',
            'Reported Photosynthetic Photon Efficacy (400-700nm)',
            'Reported Photosynthetic Photon Flux (400-700nm)'
        ]
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns in data file: {missing_cols}")
            return pd.DataFrame()
        
        st.success("Data loaded successfully.")
        return df
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame()

# ---------------------------------------------------------
#               ADVANCED FILTERING (SIDE TAB)
# ---------------------------------------------------------
def apply_advanced_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Presents a robust set of filters on the sidebar, returning
    the filtered DataFrame. 
    Added water-cooling example logic, if the column exists.
    """
    st.sidebar.title("Advanced Filters")

    # Manufacturer / Brand
    if 'Manufacturer' in df.columns:
        all_manufacturers = sorted(df['Manufacturer'].dropna().unique())
        selected_manufacturers = st.sidebar.multiselect(
            "Manufacturer(s)",
            options=all_manufacturers,
            default=all_manufacturers
        )
    else:
        selected_manufacturers = df.index

    if 'Brand' in df.columns:
        all_brands = sorted(df['Brand'].dropna().unique())
        selected_brands = st.sidebar.multiselect(
            "Brand(s)",
            options=all_brands,
            default=all_brands
        )
    else:
        selected_brands = df.index
    
    # Wattage Range
    if 'Reported Input Wattage' in df.columns:
        min_watt = float(df['Reported Input Wattage'].min())
        max_watt = float(df['Reported Input Wattage'].max())
        watt_range = st.sidebar.slider(
            "Wattage Range (W)",
            min_value=0.0,
            max_value=max_watt,
            value=(min_watt, max_watt),
            step=25.0
        )
    else:
        watt_range = (0, 99999)
    
    # Efficacy Range
    if 'Reported Photosynthetic Photon Efficacy (400-700nm)' in df.columns:
        min_eff = float(df['Reported Photosynthetic Photon Efficacy (400-700nm)'].min())
        max_eff = float(df['Reported Photosynthetic Photon Efficacy (400-700nm)'].max())
        eff_range = st.sidebar.slider(
            "Efficacy Range (µmol/J)",
            min_value=min_eff,
            max_value=max_eff,
            value=(min_eff, max_eff)
        )
    else:
        eff_range = (0, 999)
    
    # PPF Range
    if 'Reported Photosynthetic Photon Flux (400-700nm)' in df.columns:
        min_ppf = float(df['Reported Photosynthetic Photon Flux (400-700nm)'].min())
        max_ppf = float(df['Reported Photosynthetic Photon Flux (400-700nm)'].max())
        ppf_range = st.sidebar.slider(
            "PPF Range (µmol/s)",
            min_value=min_ppf,
            max_value=max_ppf,
            value=(min_ppf, max_ppf)
        )
    else:
        ppf_range = (0, 999999)
    
    # THD (Total Harmonic Distortion)
    thd_range = (0, 9999)
    if 'Tested Total Harmonic Distortion' in df.columns:
        thd_col = 'Tested Total Harmonic Distortion'
        if df[thd_col].notna().any():
            min_thd = float(df[thd_col].min())
            max_thd = float(df[thd_col].max())
            thd_range = st.sidebar.slider(
                "Tested THD (%)",
                min_value=min_thd,
                max_value=max_thd,
                value=(min_thd, max_thd),
                step=1.0
            )
    
    # Power Factor
    pf_range = (0, 1.0)
    if 'Tested Power Factor' in df.columns:
        pf_col = 'Tested Power Factor'
        if df[pf_col].notna().any():
            min_pf = float(df[pf_col].min())
            max_pf = float(df[pf_col].max())
            pf_range = st.sidebar.slider(
                "Tested Power Factor",
                min_value=min_pf,
                max_value=max_pf,
                value=(min_pf, max_pf),
                step=0.01
            )
    
    # Fixture Max Ambient Temp
    # Example numeric filter (for, e.g., water cooling considerations):
    if 'Fixture Maximum Ambient Temp' in df.columns:
        min_temp = float(df['Fixture Maximum Ambient Temp'].min())
        max_temp = float(df['Fixture Maximum Ambient Temp'].max())
        fixture_temp_range = st.sidebar.slider(
            "Fixture Max Ambient Temp Range",
            min_value=min_temp,
            max_value=max_temp,
            value=(min_temp, max_temp)
        )
    else:
        fixture_temp_range = (0.0, 999.0)

    # Water Cooling (example)
    # Suppose your dataset has a column "Cooling Method" or "Is Water Cooled?" with True/False or "Water"/"Air".
    # We'll assume there's a column "Cooling Method" with possible values: ["Air-Cooled", "Water-Cooled", etc.]
    water_cooled_only = False
    if 'Cooling Method' in df.columns:
        water_cooled_only = st.sidebar.checkbox("Water-Cooled Only?")

    # Dimmable / Tunable
    spectral_tuning = False
    dimmable = False
    if 'Spectrally Tunable' in df.columns:
        spectral_tuning = st.sidebar.checkbox("Spectrally Tunable Only?")
    if 'Dimmable' in df.columns:
        dimmable = st.sidebar.checkbox("Dimmable Only?")
    
    # Power Type
    if 'Input Power Type' in df.columns:
        all_power_types = sorted(df['Input Power Type'].dropna().unique())
        selected_power_types = st.sidebar.multiselect(
            "Input Power Type(s)",
            options=all_power_types,
            default=all_power_types
        )
    else:
        selected_power_types = df.index

    # Filter step by step
    filtered = df.copy()
    
    # Manufacturer & Brand
    if 'Manufacturer' in df.columns:
        filtered = filtered[filtered['Manufacturer'].isin(selected_manufacturers)]
    if 'Brand' in df.columns:
        filtered = filtered[filtered['Brand'].isin(selected_brands)]
    
    # Wattage
    if 'Reported Input Wattage' in df.columns:
        filtered = filtered[
            (filtered['Reported Input Wattage'] >= watt_range[0]) 
            & (filtered['Reported Input Wattage'] <= watt_range[1])
        ]
    
    # Efficacy
    if 'Reported Photosynthetic Photon Efficacy (400-700nm)' in filtered.columns:
        filtered = filtered[
            (filtered['Reported Photosynthetic Photon Efficacy (400-700nm)'] >= eff_range[0])
            & (filtered['Reported Photosynthetic Photon Efficacy (400-700nm)'] <= eff_range[1])
        ]
    
    # PPF
    if 'Reported Photosynthetic Photon Flux (400-700nm)' in filtered.columns:
        filtered = filtered[
            (filtered['Reported Photosynthetic Photon Flux (400-700nm)'] >= ppf_range[0])
            & (filtered['Reported Photosynthetic Photon Flux (400-700nm)'] <= ppf_range[1])
        ]
    
    # THD
    if 'Tested Total Harmonic Distortion' in filtered.columns:
        filtered = filtered[
            ((filtered['Tested Total Harmonic Distortion'] >= thd_range[0])
             & (filtered['Tested Total Harmonic Distortion'] <= thd_range[1]))
            | (filtered['Tested Total Harmonic Distortion'].isna())
        ]
    
    # PF
    if 'Tested Power Factor' in filtered.columns:
        filtered = filtered[
            ((filtered['Tested Power Factor'] >= pf_range[0])
             & (filtered['Tested Power Factor'] <= pf_range[1]))
            | (filtered['Tested Power Factor'].isna())
        ]

    # Fixture Maximum Ambient Temp
    if 'Fixture Maximum Ambient Temp' in filtered.columns:
        filtered = filtered[
            (filtered['Fixture Maximum Ambient Temp'] >= fixture_temp_range[0])
            & (filtered['Fixture Maximum Ambient Temp'] <= fixture_temp_range[1])
        ]

    # Water-Cooled filter
    if water_cooled_only and 'Cooling Method' in filtered.columns:
        filtered = filtered[filtered['Cooling Method'].str.contains("Water", case=False, na=False)]

    # Spectral Tuning
    if spectral_tuning and 'Spectrally Tunable' in filtered.columns:
        filtered = filtered[filtered['Spectrally Tunable'] == True]
    
    # Dimmable
    if dimmable and 'Dimmable' in filtered.columns:
        filtered = filtered[filtered['Dimmable'] == True]
    
    # Input Power Type
    if 'Input Power Type' in filtered.columns:
        filtered = filtered[filtered['Input Power Type'].isin(selected_power_types)]
    
    return filtered

# ---------------------------------------------------------
#         OPTIONAL: Combined Global + Advanced Filters
# ---------------------------------------------------------
def apply_combined_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Demonstrates how to combine simpler global filters 
    (like power range, manufacturer) with the advanced filters above.
    """
    st.sidebar.header("Global Filters")
    
    # Basic global filters (example)
    if 'Manufacturer' in df.columns:
        manufacturers = sorted(df['Manufacturer'].unique())
        selected_manufacturers = st.sidebar.multiselect(
            "Select Manufacturers (Global)",
            options=manufacturers,
            default=manufacturers
        )
        global_mask = df['Manufacturer'].isin(selected_manufacturers)
    else:
        global_mask = df.index == df.index  # all True if Manufacturer col missing

    if 'Reported Input Wattage' in df.columns:
        power_range = st.sidebar.slider(
            "Power Range (W) (Global)",
            min_value=float(df['Reported Input Wattage'].min()),
            max_value=float(df['Reported Input Wattage'].max()),
            value=(
                float(df['Reported Input Wattage'].min()),
                float(df['Reported Input Wattage'].max())
            )
        )
        global_mask &= df['Reported Input Wattage'].between(*power_range)
    
    df_global_filtered = df[global_mask].copy()
    
    # Now apply the advanced filters on top
    df_advanced_filtered = apply_advanced_filters(df_global_filtered)
    return df_advanced_filtered

# ---------------------------------------------------------
#     EXCEL DOWNLOAD, SCENARIOS, & OUTLIER HIGHLIGHTING
# ---------------------------------------------------------
def create_excel_download(df: pd.DataFrame) -> bytes:
    """
    Create an in-memory Excel file (as bytes) for download.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


def threshold_alerts(df: pd.DataFrame, efficacy_threshold=2.0):
    """
    Show a red alert and highlight any products that fall below
    an efficacy threshold. Demonstrates outlier detection.
    """
    st.subheader("Threshold Alert")
    if 'Reported Photosynthetic Photon Efficacy (400-700nm)' not in df.columns:
        st.warning("Efficacy column not present.")
        return
    
    fails = df[df['Reported Photosynthetic Photon Efficacy (400-700nm)'] < efficacy_threshold]
    if not fails.empty:
        st.error(f"{len(fails)} products fall below the efficacy threshold of {efficacy_threshold} µmol/J")
        st.dataframe(fails)
    else:
        st.success(f"No products fall below the {efficacy_threshold} µmol/J threshold.")


def highlight_outliers(val, lower_bound, upper_bound):
    """
    Used in conjunction with DataFrame.style.applymap() to highlight outliers.
    """
    if pd.api.types.is_number(val):
        if val < lower_bound or val > upper_bound:
            return 'background-color: yellow;'
    return ''


def save_filter_state(current_filter_description: str):
    """
    Save the current filter 'scenario' (any text or context describing the current state)
    in st.session_state for easy scenario comparisons.
    """
    if 'scenarios' not in st.session_state:
        st.session_state['scenarios'] = []
    st.session_state['scenarios'].append(current_filter_description)


def compare_scenarios():
    """
    Display previously saved scenario states (if any).
    In a real scenario, you'd store actual filter values or data snapshots, not just text.
    """
    if 'scenarios' in st.session_state and st.session_state['scenarios']:
        st.write("### Saved Scenarios:")
        for i, scenario in enumerate(st.session_state['scenarios']):
            st.write(f"**Scenario {i+1}:** {scenario}")
    else:
        st.info("No scenarios saved yet. Go to 'Advanced Filters', choose some settings, and click 'Save Scenario'.")

# ---------------------------------------------------------
#                  METRICS & COMPARISON
# ---------------------------------------------------------
def display_comparative_metrics(df1: pd.DataFrame, df2: pd.DataFrame = None):
    """
    Display basic metrics (PPF, Efficacy, Power) with optional comparison 
    to another DataFrame.
    """
    if df1.empty:
        st.warning("No data in first DataFrame.")
        return
    
    col1, col2, col3 = st.columns(3)
    if 'Reported Photosynthetic Photon Flux (400-700nm)' in df1.columns:
        with col1:
            st.metric(
                label="Avg PPF (µmol/s)",
                value=f"{df1['Reported Photosynthetic Photon Flux (400-700nm)'].mean():.0f}",
                delta=None if df2 is None or df2.empty else f"{(df1['Reported Photosynthetic Photon Flux (400-700nm)'].mean() - df2['Reported Photosynthetic Photon Flux (400-700nm)'].mean()):.0f}"
            )
    if 'Reported Photosynthetic Photon Efficacy (400-700nm)' in df1.columns:
        with col2:
            st.metric(
                label="Avg Efficacy (µmol/J)",
                value=f"{df1['Reported Photosynthetic Photon Efficacy (400-700nm)'].mean():.2f}",
                delta=None if df2 is None or df2.empty else f"{(df1['Reported Photosynthetic Photon Efficacy (400-700nm)'].mean() - df2['Reported Photosynthetic Photon Efficacy (400-700nm)'].mean()):.2f}"
            )
    if 'Reported Input Wattage' in df1.columns:
        with col3:
            st.metric(
                label="Avg Power (W)",
                value=f"{df1['Reported Input Wattage'].mean():.0f} W",
                delta=None if df2 is None or df2.empty else f"{(df1['Reported Input Wattage'].mean() - df2['Reported Input Wattage'].mean()):.0f}"
            )


def multi_manufacturer_comparison(df: pd.DataFrame):
    """
    Allows the user to pick multiple manufacturers from filtered data
    and compare them on a scatter or bar chart for Efficacy vs Wattage vs PPF.
    """
    st.subheader("Multi-Manufacturer Comparison")
    
    if 'Manufacturer' not in df.columns or df.empty:
        st.warning("No Manufacturer column or data is empty.")
        return
    
    # Select multiple manufacturers
    mans = sorted(df['Manufacturer'].dropna().unique())
    selected_mans = st.multiselect(
        "Compare these Manufacturers",
        options=mans,
        default=mans[:5]  # pick first 5 by default
    )
    
    compare_df = df[df['Manufacturer'].isin(selected_mans)]
    if compare_df.empty:
        st.warning("No data to compare with the current filter/selection.")
        return
    
    # Show a scatter plot (Efficacy vs Wattage) sized by PPF
    if all(col in compare_df.columns for col in [
        'Reported Input Wattage', 
        'Reported Photosynthetic Photon Efficacy (400-700nm)',
        'Reported Photosynthetic Photon Flux (400-700nm)'
    ]):
        fig = px.scatter(
            compare_df,
            x='Reported Input Wattage',
            y='Reported Photosynthetic Photon Efficacy (400-700nm)',
            size='Reported Photosynthetic Photon Flux (400-700nm)',
            color='Manufacturer',
            hover_data=['Model Number'],
            title="Comparison: Efficacy vs. Wattage (Bubble size = PPF)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Required columns for scatter comparison are missing.")
    
    # Also show table (sortable by default in Streamlit)
    st.dataframe(compare_df.sort_values(
        by='Reported Photosynthetic Photon Efficacy (400-700nm)', 
        ascending=False
    ))

# ---------------------------------------------------------
#             CHARTS & VISUALIZATIONS
# ---------------------------------------------------------
def create_efficiency_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a dual-axis bar chart showing PPF and Efficacy by Model Number.
    """
    fig = go.Figure()
    needed_cols = [
        'Model Number',
        'Reported Photosynthetic Photon Flux (400-700nm)',
        'Reported Photosynthetic Photon Efficacy (400-700nm)'
    ]
    if not all(col in df.columns for col in needed_cols):
        return fig
    
    fig.add_trace(
        go.Bar(
            name='PPF',
            x=df['Model Number'],
            y=df['Reported Photosynthetic Photon Flux (400-700nm)'],
            yaxis='y'
        )
    )
    fig.add_trace(
        go.Bar(
            name='Efficacy',
            x=df['Model Number'],
            y=df['Reported Photosynthetic Photon Efficacy (400-700nm)'],
            yaxis='y2'
        )
    )
    fig.update_layout(
        title='Efficiency Metrics by Model',
        barmode='group',
        yaxis=dict(title='PPF (µmol/s)', side='left'),
        yaxis2=dict(title='Efficacy (µmol/J)', side='right', overlaying='y'),
        height=600
    )
    return fig

# (Other chart functions omitted for brevity; keep them if needed)

# ---------------------------------------------------------
#        CONTROL METHOD ANALYSIS
# ---------------------------------------------------------
def control_analysis(df: pd.DataFrame):
    """Analyze and display control method metrics"""
    st.header("Control Method Analysis")
    
    if 'Dimming and Control Method to the Product' not in df.columns:
        st.warning("Control method data not available in the dataset")
        return
        
    # Control method distribution
    st.subheader("Distribution of Control Methods")
    control_dist = df['Dimming and Control Method to the Product'].value_counts()
    fig_control = px.pie(
        values=control_dist.values,
        names=control_dist.index,
        title='Distribution of Control Methods'
    )
    st.plotly_chart(fig_control)
    
    # Control method by manufacturer
    st.subheader("Control Methods by Manufacturer")
    control_by_mfg = pd.crosstab(
        df['Manufacturer'], 
        df['Dimming and Control Method to the Product']
    )
    fig_control_mfg = px.bar(
        control_by_mfg,
        title='Control Methods Distribution by Manufacturer',
        barmode='stack'
    )
    st.plotly_chart(fig_control_mfg)
    
    # Efficacy by control method
    st.subheader("Efficacy by Control Method")
    if 'Reported Photosynthetic Photon Efficacy (400-700nm)' in df.columns:
        fig_eff = px.box(
            df,
            x='Dimming and Control Method to the Product',
            y='Reported Photosynthetic Photon Efficacy (400-700nm)',
            title='Efficacy Distribution by Control Method'
        )
        st.plotly_chart(fig_eff)
    
    # Table of control methods and counts
    st.subheader("Control Methods Summary")
    if 'Reported Photosynthetic Photon Efficacy (400-700nm)' in df.columns:
        control_summary = df.groupby('Dimming and Control Method to the Product').agg({
            'Manufacturer': 'count',
            'Reported Photosynthetic Photon Efficacy (400-700nm)': 'mean',
            'Reported Input Wattage': 'mean'
        }).round(2)
        control_summary.columns = ['Count', 'Avg Efficacy (μmol/J)', 'Avg Power (W)']
        st.dataframe(control_summary)
    else:
        st.write("Missing Efficacy column in dataset.")

# ---------------------------------------------------------
#        EXAMPLE SUBPAGES (MARKET, TECHNICAL, ETC.)
# ---------------------------------------------------------
def market_overview(df: pd.DataFrame):
    """Display market overview with safe handling of empty dataframes"""
    st.header("📈 Market Overview")
    
    if df.empty:
        st.warning("No data available for the selected filters")
        return
        
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📦 Total Products", len(df))
        with col2:
            st.metric("🏭 Unique Manufacturers", df['Manufacturer'].nunique())
        with col3:
            mfg_counts = df['Manufacturer'].value_counts()
            if not mfg_counts.empty:
                top_mfg = mfg_counts.index[0]
                top_count = mfg_counts.iloc[0]
                st.metric("👑 Market Leader", f"{top_mfg} ({top_count} products)")
            else:
                st.metric("👑 Market Leader", "No data")

def technical_specs(df: pd.DataFrame):
    """
    Display expanded technical specifications, 
    including Maximum Ambient Temp, Warranty, etc.
    """
    st.header("Technical Specifications Analysis")
    
    if df.empty:
        st.warning("No data to display for technical specs.")
        return
    
    # Display key specs metrics
    col1, col2, col3 = st.columns(3)
    
    if 'Tested Power Factor' in df.columns and df['Tested Power Factor'].notna().any():
        with col1:
            st.metric(
                "Average Power Factor",
                f"{df['Tested Power Factor'].mean():.2f}"
            )
    
    if 'Tested Total Harmonic Distortion' in df.columns and df['Tested Total Harmonic Distortion'].notna().any():
        with col2:
            st.metric(
                "Average THD",
                f"{df['Tested Total Harmonic Distortion'].mean():.1f}%"
            )
    
    if 'Fixture Maximum Ambient Temp' in df.columns and df['Fixture Maximum Ambient Temp'].notna().any():
        with col3:
            st.metric(
                "Average Max Temp",
                f"{df['Fixture Maximum Ambient Temp'].mean():.1f}°C"
            )

    # Warranty distribution
    if 'Warranty' in df.columns:
        st.subheader("Warranty Distribution")
        fig_warranty = px.histogram(
            df,
            x='Warranty',
            color='Manufacturer',
            title='Warranty (years) Distribution by Manufacturer'
        )
        st.plotly_chart(fig_warranty)

    # Power Factor Distribution
    if 'Tested Power Factor' in df.columns:
        st.subheader("Power Factor Distribution")
        fig_pf = px.histogram(
            df,
            x='Tested Power Factor',
            color='Manufacturer',
            title='Power Factor Distribution by Manufacturer'
        )
        st.plotly_chart(fig_pf)

    # THD Analysis
    if 'Tested Total Harmonic Distortion' in df.columns:
        st.subheader("Total Harmonic Distortion")
        fig_thd = px.box(
            df,
            x='Manufacturer',
            y='Tested Total Harmonic Distortion',
            title='THD Distribution by Manufacturer'
        )
        st.plotly_chart(fig_thd)

    # Temperature capabilities
    if 'Fixture Maximum Ambient Temp' in df.columns:
        st.subheader("Temperature Analysis")
        fig_temp = px.scatter(
            df,
            x='Reported Input Wattage',
            y='Fixture Maximum Ambient Temp',
            color='Manufacturer',
            title='Maximum Ambient Temperature vs. Input Power'
        )
        st.plotly_chart(fig_temp)

def efficiency_analysis(df: pd.DataFrame):
    """Analyze and display efficiency metrics"""
    st.header("Efficiency Analysis")
    
    if df.empty:
        st.warning("No data available for efficiency analysis.")
        return
    
    # Basic columns check
    if 'Reported Photosynthetic Photon Efficacy (400-700nm)' not in df.columns:
        st.warning("Efficacy column is missing. Cannot do Efficiency Analysis.")
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Average Efficacy",
            f"{df['Reported Photosynthetic Photon Efficacy (400-700nm)'].mean():.2f} μmol/J"
        )
    with col2:
        st.metric(
            "Max Efficacy",
            f"{df['Reported Photosynthetic Photon Efficacy (400-700nm)'].max():.2f} μmol/J"
        )
    with col3:
        st.metric(
            "Min Efficacy",
            f"{df['Reported Photosynthetic Photon Efficacy (400-700nm)'].min():.2f} μmol/J"
        )

    # Efficacy distribution
    st.subheader("Efficacy Distribution")
    fig_dist = px.histogram(
        df,
        x='Reported Photosynthetic Photon Efficacy (400-700nm)',
        color='Manufacturer',
        title='Efficacy Distribution by Manufacturer'
    )
    fig_dist.update_layout(height=500)
    st.plotly_chart(fig_dist, use_container_width=True)

    # Top performers
    st.subheader("Top 10 Most Efficient Products")
    top_10 = df.nlargest(10, 'Reported Photosynthetic Photon Efficacy (400-700nm)')
    st.dataframe(
        top_10[[
            'Manufacturer', 
            'Model Number', 
            'Reported Photosynthetic Photon Efficacy (400-700nm)',
            'Reported Input Wattage'
        ]]
    )

    # Circular chart of average efficacy by manufacturer
    st.subheader("Efficiency by Manufacturer")
    avg_eff_by_mfg = df.groupby('Manufacturer')['Reported Photosynthetic Photon Efficacy (400-700nm)'].mean().reset_index()
    fig_pie = px.pie(
        avg_eff_by_mfg,
        values='Reported Photosynthetic Photon Efficacy (400-700nm)',
        names='Manufacturer',
        title='Average Efficacy by Manufacturer'
    )
    fig_pie.update_layout(
        height=600,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.0
        )
    )
    st.plotly_chart(fig_pie, use_container_width=True)


def create_power_ranges(df: pd.DataFrame, increment=100):
    """Create extended power ranges based on data"""
    max_power = df['Reported Input Wattage'].max()
    ranges = []
    current = 0
    
    while current <= max_power:
        next_power = min(current + increment, max_power)
        ranges.append((
            current,
            next_power,
            f"{current}-{next_power}W"
        ))
        current = next_power
    
    return ranges

def lighting_analysis(df: pd.DataFrame):
    """Enhanced lighting analysis with detailed power ranges"""
    st.header("Advanced Lighting Analysis")

    # Define wavelength ranges with precise colors
    spectral_bands = {
        'Blue (400-500nm)': '#0066FF',     
        'Green (500-600nm)': '#00FF00',    
        'Red (600-700nm)': '#FF0000',      
        'Far Red (700-800nm)': '#8B0000'   
    }

    # Dynamic power range selection
    max_power = int(df['Reported Input Wattage'].max())
    power_increment = st.select_slider(
        "Power Range Increment (W)",
        options=[100, 200, 500],
        value=100
    )

    # Generate power ranges up to max wattage
    power_ranges = [
        (i, min(i + power_increment, max_power))
        for i in range(0, max_power + power_increment, power_increment)
    ]

    # Create labels for power ranges
    power_labels = [f"{min_w}-{max_w}W" for min_w, max_w in power_ranges]

    # Analyze spectrum by power range
    specs_by_power = []
    for (min_w, max_w), label in zip(power_ranges, power_labels):
        power_mask = df['Reported Input Wattage'].between(min_w, max_w)
        if df[power_mask].empty:
            continue
            
        for band, color in spectral_bands.items():
            flux_col = f"Reported Photon Flux {band}"
            specs_by_power.append({
                'Power_Range': label,
                'Band': band.split()[0],
                'Flux': df[power_mask][flux_col].mean(),
                'Count': df[power_mask][flux_col].count(),
                'Min': df[power_mask][flux_col].min(),
                'Max': df[power_mask][flux_col].max(),
                'StdDev': df[power_mask][flux_col].std(),
                'Color': color
            })

    # Create visualization
    if specs_by_power:
        power_specs_df = pd.DataFrame(specs_by_power)
        fig_power_spectrum = px.bar(
            power_specs_df,
            x='Power_Range',
            y='Flux',
            color='Band',
            barmode='group',
            color_discrete_map={
                'Blue': '#0066FF',
                'Green': '#00FF00',
                'Red': '#FF0000',
                'Far Red': '#8B0000'
            },
            title=f'Spectral Distribution by Power Range (Increments: {power_increment}W)'
        )
        st.plotly_chart(fig_power_spectrum)

    # ...rest of existing lighting_analysis function...


def set_custom_style():
    st.markdown("""
        <style>
        .stApp {
            background: #f0f2f6;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .metric-card {
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .filters-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin: 10px 0;
        }
        </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
#          ENHANCED FILTERS WITH SELECT/REMOVE ALL
# ---------------------------------------------------------
def create_filters(df: pd.DataFrame):
    """Enhanced filters with select all/none functionality"""
    with st.sidebar:
        st.markdown('<div class="filters-card">', unsafe_allow_html=True)
        st.subheader("🎛️ Filters")
        
        with st.expander("📊 Manufacturer Filter", expanded=True):
            col1, col2 = st.columns(2)
            
            # Initialize session state for manufacturers if not exists
            if 'selected_manufacturers' not in st.session_state:
                st.session_state.selected_manufacturers = sorted(df['Manufacturer'].unique())
            
            with col1:
                if st.button("Select All"):
                    st.session_state.selected_manufacturers = sorted(df['Manufacturer'].unique())
            with col2:
                if st.button("Clear All"):
                    st.session_state.selected_manufacturers = []
            
            all_manufacturers = sorted(df['Manufacturer'].unique())
            selected_manufacturers = st.multiselect(
                "Select Manufacturers",
                options=all_manufacturers,
                default=st.session_state.selected_manufacturers,
                key='mfg_filter'
            )
            
            # Update session state
            st.session_state.selected_manufacturers = selected_manufacturers

        # Control Methods filter
        if 'Dimming and Control Method to the Product' in df.columns:
            with st.expander("🎮 Control Methods", expanded=True):
                control_methods = sorted(df['Dimming and Control Method to the Product'].dropna().unique())
                selected_controls = st.multiselect(
                    "Select Control Methods",
                    options=control_methods,
                    default=control_methods
                )
        else:
            selected_controls = []

    return selected_manufacturers, selected_controls

# ---------------------------------------------------------
#                      MAIN APP
# ---------------------------------------------------------
def create_global_filters(df: pd.DataFrame):
    """Create unified global filters including cooling type"""
    with st.sidebar:
        st.header("Global Filters")

        # Manufacturer Filter
        with st.expander("Manufacturer Filter", expanded=True):
            if 'selected_manufacturers' not in st.session_state:
                st.session_state.selected_manufacturers = sorted(df['Manufacturer'].unique())
            
            selected_manufacturers = st.multiselect(
                "Select Manufacturers",
                options=sorted(df['Manufacturer'].unique()),
                default=st.session_state.selected_manufacturers
            )

        # Cooling Type Filter (if column exists)
        cooling_type = None
        if 'Cooling Type' in df.columns:
            with st.expander("Cooling System", expanded=True):
                cooling_types = ['All'] + sorted(df['Cooling Type'].unique().tolist())
                cooling_type = st.selectbox(
                    "Select Cooling Type",
                    options=cooling_types,
                    index=0
                )

        # Power Range Filter
        with st.expander("Power Range", expanded=True):
            max_power = df['Reported Input Wattage'].max()
            power_range = st.slider(
                "Input Power (W)",
                min_value=0,
                max_value=int(max_power),
                value=(0, int(max_power)),
                step=100
            )

    return selected_manufacturers, cooling_type, power_range

def apply_filters(df: pd.DataFrame, manufacturers, cooling_type, power_range):
    """Apply all global filters"""
    mask = (
        df['Manufacturer'].isin(manufacturers) &
        df['Reported Input Wattage'].between(*power_range)
    )
    
    if cooling_type and cooling_type != 'All':
        mask &= df['Cooling Type'] == cooling_type
        
    return df[mask]

def main():
    """Main application entry point"""
    st.set_page_config(page_title="Grow Light Analysis", layout="wide")
    
    df = load_data()
    if df is None:
        return

    # Use consolidated global filters
    selected_manufacturers, cooling_type, power_range = create_global_filters(df)
    
    # Apply filters
    filtered_df = apply_filters(df, selected_manufacturers, cooling_type, power_range)
    
    set_custom_style()

    # Give the user an option to open "Advanced Filters" in a separate section
    with st.sidebar.expander("Advanced Filters (Optional)", expanded=False):
        apply_adv = st.checkbox("Apply Advanced Filters", value=False)
    if apply_adv:
        filtered_df = apply_advanced_filters(filtered_df)

    # Create tabs
    tabs = st.tabs([
        "Market Overview",
        "Technical Specs",
        "Lighting Analysis",
        "Control Analysis",
        "Efficiency Analysis",
        "Data Explorer"
    ])
    
    with tabs[0]:
        market_overview(filtered_df)

    with tabs[1]:
        technical_specs(filtered_df)
    
    with tabs[2]:
        lighting_analysis(filtered_df)
        
    with tabs[3]:
        control_analysis(filtered_df)
        
    with tabs[4]:
        efficiency_analysis(filtered_df)

    with tabs[5]:
        create_interactive_table(filtered_df)


# ---------------------------------------------------------
#    ENHANCED INTERACTIVE TABLE WITH MULTICOLUMN SORT
# ---------------------------------------------------------
def create_interactive_table(df: pd.DataFrame):
    """Updated interactive table without duplicate manufacturer filters"""
    st.subheader("Interactive Data Explorer")
    
    # Column selector without manufacturer/brand columns
    exclude_columns = ['Manufacturer', 'Brand']
    available_columns = [col for col in df.columns if col not in exclude_columns]
    
    with st.expander("Select Columns to Display"):
        selected_columns = st.multiselect(
            "Choose columns to display",
            options=available_columns,
            default=[
                'Model Number',
                'Reported Input Wattage',
                'Reported Photosynthetic Photon Efficacy (400-700nm)',
                'Reported Photosynthetic Photon Flux (400-700nm)'
            ]
        )
    
    # Text search filter
    search_text = st.text_input("Search in any column", "")
    
    # Apply text search filter (case-insensitive partial match across all columns)
    if search_text:
        mask_list = []
        for col in df.columns:
            # Convert to string, check if search_text is in it
            mask_list.append(df[col].astype(str).str.contains(search_text, case=False, na=False))
        combined_mask = pd.concat(mask_list, axis=1).any(axis=1)
        filtered_data = df[combined_mask]
    else:
        filtered_data = df
    
    # Multi-column sort UI
    st.write("#### Sorting Options")
    sort_col_1 = st.selectbox("Primary Sort Column", options=["None"] + selected_columns)
    sort_order_1 = st.radio("Primary Sort Order", options=["Ascending", "Descending"], index=0, key="sort1")
    
    sort_col_2 = st.selectbox("Secondary Sort Column", options=["None"] + selected_columns)
    sort_order_2 = st.radio("Secondary Sort Order", options=["Ascending", "Descending"], index=0, key="sort2")
    
    # Build sort instructions
    sort_by = []
    ascending = []
    
    if sort_col_1 != "None":
        sort_by.append(sort_col_1)
        ascending.append(True if sort_order_1 == "Ascending" else False)
    
    if sort_col_2 != "None":
        sort_by.append(sort_col_2)
        ascending.append(True if sort_order_2 == "Ascending" else False)
    
    if sort_by:
        filtered_data = filtered_data.sort_values(by=sort_by, ascending=ascending)
    
    # Display the table
    st.dataframe(
        filtered_data[selected_columns],
        use_container_width=True,
        height=600
    )

    # Download filtered data
    st.write("### Download")
    if st.button("Download Filtered Data"):
        csv = filtered_data[selected_columns].to_csv(index=False)
        st.download_button(
            "Click to Download",
            csv,
            "filtered_data.csv",
            "text/csv",
            key="download-csv"
        )

# ---------------------------------------------------------
#                       RUN APP
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
