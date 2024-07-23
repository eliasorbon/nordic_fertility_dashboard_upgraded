import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import seaborn as sns
import io
import requests
from scipy import stats
import numpy as np

# Set up the color palette and style
plt.style.use('seaborn-v0_8-whitegrid')
color_palette = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
sns.set_palette(color_palette)

# Custom fonts
title_font = fm.FontProperties(family='Arial', weight='bold', size=16)
subtitle_font = fm.FontProperties(family='Arial', style='italic', size=12)
label_font = fm.FontProperties(family='Arial', size=12)
tick_font = fm.FontProperties(family='Arial', size=10)

def get_country_codes(countries):
    url = "http://api.worldbank.org/v2/country"
    params = {"format": "json", "per_page": 300}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        country_dict = {item['name'].lower(): item['id'] for item in data[1]}
        
        codes = []
        for country in countries:
            code = country_dict.get(country.lower())
            if code:
                codes.append(code)
            else:
                print(f"Warning: Could not find code for {country}. Using name as is.")
                codes.append(country)
        
        return codes
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching country codes: {e}")
        return countries

def fetch_world_bank_data(countries, indicators, start_year=1960, end_year=2022, timeout=30):
    base_url = "http://api.worldbank.org/v2/country/{}/indicator/{}"
    
    all_data = []
    
    for country in countries:
        for indicator in indicators:
            url = base_url.format(country, indicator)
            params = {
                "date": f"{start_year}:{end_year}",
                "format": "json",
                "per_page": 1000
            }
            
            try:
                print(f"Fetching {indicator} data for {country}...")
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                data = response.json()
                
                if len(data) > 1:
                    country_data = [(item['country']['value'], item['date'], indicator, item['value']) for item in data[1]]
                    all_data.extend(country_data)
                else:
                    print(f"No data available for {country} and indicator {indicator}")
                
            except requests.exceptions.RequestException as e:
                print(f"An error occurred while fetching data for {country} and indicator {indicator}: {e}")
    
    if not all_data:
        print("No data was fetched from the World Bank API.")
        return None
    
    print("Processing fetched data...")
    df = pd.DataFrame(all_data, columns=['Country', 'Year', 'Indicator', 'Value'])
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    df = df.pivot_table(index=['Country', 'Year'], columns='Indicator', values='Value').reset_index()
    df['Year'] = pd.to_numeric(df['Year'])
    
    return df

def create_dashboard(countries, data):
    if data is None or data.empty:
        print("No data available. Please check your internet connection and try again.")
        return None
    
    print("Available columns in the data:")
    print(data.columns)
    
    fig = Figure(figsize=(20, 16), dpi=300)
    canvas = FigureCanvas(fig)
    
    fig.patch.set_facecolor('#ECEFF4')
    fig.suptitle('Nordic Countries Fertility Analysis Dashboard', fontproperties=title_font, fontsize=24, y=0.98, color='#2E3440')
    fig.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.92, wspace=0.3, hspace=0.4)
   
    # 1. Fertility Rate Trends
    ax1 = fig.add_subplot(321)
    fertility_rate_col = 'SP.DYN.TFRT.IN'
    if fertility_rate_col in data.columns:
        for i, country in enumerate(countries):
            country_data = data[data['Country'] == country]
            ax1.plot(country_data['Year'], country_data[fertility_rate_col], label=country, linewidth=2, color=color_palette[i])
        ax1.set_title('Fertility Rate Trends (1960-2022)', fontproperties=title_font, pad=20, color='#2E3440')
        ax1.text(0.5, -0.15, 'How the average number of children born to a woman has changed over time',
                 horizontalalignment='center', verticalalignment='center', transform=ax1.transAxes,
                 fontproperties=subtitle_font, color='#4C566A')
        ax1.set_xlabel('Year', fontproperties=label_font, color='#4C566A')
        ax1.set_ylabel('Fertility Rate (births per woman)', fontproperties=label_font, color='#4C566A')
        ax1.tick_params(axis='both', which='major', labelsize=10, colors='#4C566A')
        ax1.legend(prop=label_font, loc='center left', bbox_to_anchor=(1, 0.5))
        ax1.grid(True, linestyle='--', alpha=0.7, color='#D8DEE9')
        ax1.set_facecolor('#E5E9F0')
    else:
        ax1.text(0.5, 0.5, 'Fertility Rate data not available', ha='center', va='center')

    # 2. Latest Fertility Rates
    ax2 = fig.add_subplot(322)
    if fertility_rate_col in data.columns:
        latest_year = data['Year'].max()
        latest_data = data[data['Year'] == latest_year]
        latest_data = latest_data.sort_values(fertility_rate_col, ascending=True)
        bars = ax2.barh(latest_data['Country'], latest_data[fertility_rate_col], color=color_palette)
        ax2.set_title(f'Fertility Rates ({latest_year})', fontproperties=title_font, pad=20, color='#2E3440')
        ax2.text(0.5, -0.15, 'Current average number of children born to a woman in each country',
                 horizontalalignment='center', verticalalignment='center', transform=ax2.transAxes,
                 fontproperties=subtitle_font, color='#4C566A')
        ax2.set_xlabel('Fertility Rate (births per woman)', fontproperties=label_font, color='#4C566A')
        ax2.tick_params(axis='both', which='major', labelsize=10, colors='#4C566A')
        ax2.set_facecolor('#E5E9F0')
        for bar in bars:
            width = bar.get_width()
            ax2.text(width, bar.get_y() + bar.get_height()/2, f'{width:.2f}',
                     ha='left', va='center', fontproperties=tick_font, color='#2E3440')
    else:
        ax2.text(0.5, 0.5, 'Fertility Rate data not available', ha='center', va='center')

    # 3. Correlation between Fertility Rate and Female Labor Force Participation
    ax3 = fig.add_subplot(323)
    labor_force_col = 'SL.TLF.CACT.FE.ZS'
    if fertility_rate_col in data.columns and labor_force_col in data.columns:
        for i, country in enumerate(countries):
            country_data = data[data['Country'] == country]
            ax3.scatter(country_data[labor_force_col], country_data[fertility_rate_col], label=country, alpha=0.7, color=color_palette[i])
        ax3.set_title('Fertility Rate vs Female Labor Force Participation', fontproperties=title_font, pad=20, color='#2E3440')
        ax3.text(0.5, -0.15, 'How fertility rates relate to women\'s participation in the workforce',
                 horizontalalignment='center', verticalalignment='center', transform=ax3.transAxes,
                 fontproperties=subtitle_font, color='#4C566A')
        ax3.set_xlabel('Female Labor Force Participation Rate (%)', fontproperties=label_font, color='#4C566A')
        ax3.set_ylabel('Fertility Rate (births per woman)', fontproperties=label_font, color='#4C566A')
        ax3.tick_params(axis='both', which='major', labelsize=10, colors='#4C566A')
        ax3.legend(prop=label_font, loc='center left', bbox_to_anchor=(1, 0.5))
        ax3.grid(True, linestyle='--', alpha=0.7, color='#D8DEE9')
        ax3.set_facecolor('#E5E9F0')
    else:
        ax3.text(0.5, 0.5, 'Data not available for this plot', ha='center', va='center')

    # 4. Teenage Birth Rate Trends
    ax4 = fig.add_subplot(324)
    teen_birth_col = 'SP.ADO.TFRT'
    if teen_birth_col in data.columns:
        for i, country in enumerate(countries):
            country_data = data[data['Country'] == country]
            ax4.plot(country_data['Year'], country_data[teen_birth_col], label=country, linewidth=2, color=color_palette[i])
        ax4.set_title('Teenage Birth Rate Trends (1960-2022)', fontproperties=title_font, pad=20, color='#2E3440')
        ax4.text(0.5, -0.15, 'How the number of births among teenage women has changed over time',
                 horizontalalignment='center', verticalalignment='center', transform=ax4.transAxes,
                 fontproperties=subtitle_font, color='#4C566A')
        ax4.set_xlabel('Year', fontproperties=label_font, color='#4C566A')
        ax4.set_ylabel('Births per 1,000 women ages 15-19', fontproperties=label_font, color='#4C566A')
        ax4.tick_params(axis='both', which='major', labelsize=10, colors='#4C566A')
        ax4.legend(prop=label_font, loc='center left', bbox_to_anchor=(1, 0.5))
        ax4.grid(True, linestyle='--', alpha=0.7, color='#D8DEE9')
        ax4.set_facecolor('#E5E9F0')
    else:
        ax4.text(0.5, 0.5, 'Teenage Birth Rate data not available', ha='center', va='center')

    # 5. Fertility Rate Change (1960 vs 2022)
    ax5 = fig.add_subplot(325)
    if fertility_rate_col in data.columns:
        fertility_1960 = data[data['Year'] == 1960].set_index('Country')[fertility_rate_col]
        fertility_2022 = data[data['Year'] == 2022].set_index('Country')[fertility_rate_col]
        fertility_change = fertility_2022 - fertility_1960
        fertility_change = fertility_change.sort_values(ascending=True)
        bars = ax5.barh(fertility_change.index, fertility_change.values, color=color_palette)
        ax5.set_title('Change in Fertility Rate (1960 to 2022)', fontproperties=title_font, pad=20, color='#2E3440')
        ax5.text(0.5, -0.15, 'How much the average number of children born to a woman has changed since 1960',
                 horizontalalignment='center', verticalalignment='center', transform=ax5.transAxes,
                 fontproperties=subtitle_font, color='#4C566A')
        ax5.set_xlabel('Change in Fertility Rate', fontproperties=label_font, color='#4C566A')
        ax5.tick_params(axis='both', which='major', labelsize=10, colors='#4C566A')
        ax5.set_facecolor('#E5E9F0')
        for bar in bars:
            width = bar.get_width()
            ax5.text(width, bar.get_y() + bar.get_height()/2, f'{width:.2f}',
                     ha='left' if width > 0 else 'right', va='center', fontproperties=tick_font, color='#2E3440')
    else:
        ax5.text(0.5, 0.5, 'Fertility Rate data not available', ha='center', va='center')

    # 6. Fertility Rate Forecast
    ax6 = fig.add_subplot(326)
    if fertility_rate_col in data.columns:
        for i, country in enumerate(countries):
            country_data = data[data['Country'] == country]
            x = country_data['Year']
            y = country_data[fertility_rate_col]
            
            # Linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            line = slope * x + intercept
            
            # Plotting data and regression line
            ax6.scatter(x, y, label=f'{country} (Data)', alpha=0.5, color=color_palette[i])
            ax6.plot(x, line, label=f'{country} (Trend)', color=color_palette[i])
            
            # Forecasting next 10 years
            future_years = np.arange(x.max() + 1, x.max() + 11)
            future_fertility = slope * future_years + intercept
            ax6.plot(future_years, future_fertility, linestyle='--', color=color_palette[i])

        ax6.set_title('Fertility Rate Forecast (Next 10 Years)', fontproperties=title_font, pad=20, color='#2E3440')
        ax6.text(0.5, -0.15, 'Predicted trends in fertility rates for the coming decade',
                 horizontalalignment='center', verticalalignment='center', transform=ax6.transAxes,
                 fontproperties=subtitle_font, color='#4C566A')
        ax6.set_xlabel('Year', fontproperties=label_font, color='#4C566A')
        ax6.set_ylabel('Fertility Rate (births per woman)', fontproperties=label_font, color='#4C566A')
        ax6.tick_params(axis='both', which='major', labelsize=10, colors='#4C566A')
        ax6.legend(prop=label_font, loc='center left', bbox_to_anchor=(1, 0.5))
        ax6.grid(True, linestyle='--', alpha=0.7, color='#D8DEE9')
        ax6.set_facecolor('#E5E9F0')
    else:
        ax6.text(0.5, 0.5, 'Fertility Rate data not available for forecast', ha='center', va='center')

    fig.text(0.05, 0.01, 'Data source: World Bank', fontproperties=tick_font, color='#4C566A')
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    buf.seek(0)
    
    return buf

# Example usage:
nordic_countries = ['Norway', 'Sweden', 'Denmark', 'Finland', 'Iceland']
indicators = [
    'SP.DYN.TFRT.IN',  # Fertility rate, total (births per woman)
    'SP.ADO.TFRT',     # Adolescent fertility rate (births per 1,000 women ages 15-19)
    'SL.TLF.CACT.FE.ZS'  # Labor force participation rate, female (% of female population ages 15+) (modeled ILO estimate)
]

print("Fetching country codes...")
country_codes = get_country_codes(nordic_countries)
print("Fetching data from World Bank...")
data = fetch_world_bank_data(country_codes, indicators)

print("\nFirst few rows of the fetched data:")
print(data.head())

dashboard_image = create_dashboard(nordic_countries, data)

if dashboard_image:
    with open('upgraded_nordic_fertility_dashboard.png', 'wb') as f:
        f.write(dashboard_image.getvalue())
    print("Dashboard saved as 'upgraded_nordic_fertility_dashboard.png'")
else:
    print("Failed to create dashboard due to data retrieval issues.")
