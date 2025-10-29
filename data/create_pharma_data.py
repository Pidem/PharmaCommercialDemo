import sqlite3
import random
from datetime import datetime, timedelta

def create_pharma_database():
    conn = sqlite3.connect('data/pharma_sales.db')
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT,
            therapeutic_area TEXT,
            launch_date DATE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            smind INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            region TEXT,
            country TEXT,
            quarter TEXT,
            year INTEGER,
            units_sold INTEGER,
            revenue_usd REAL,
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
    ''')
    
    # Insert products
    products = [
        (1, 'Cosentyx', 'Immunology', '2015-01-15'),
        (2, 'Entresto', 'Cardiovascular', '2015-07-07'),
        (3, 'Kesimpta', 'Neurology', '2020-08-20'),
        (4, 'Zolgensma', 'Gene Therapy', '2019-05-24'),
        (5, 'Kisqali', 'Oncology', '2017-03-13')
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?)', products)
    
    # Generate sales data with specific patterns
    regions = ['North America', 'Europe', 'Asia Pacific', 'Latin America']
    countries = ['USA', 'Germany', 'Japan', 'Brazil', 'UK', 'France', 'China', 'Canada']
    quarters = ['Q1', 'Q2', 'Q3', 'Q4']
    years = [2022, 2023, 2024]
    
    sales_data = []
    for product_id in range(1, 6):
        for year in years:
            for quarter in quarters:
                for region in regions:
                    country = random.choice(countries)
                    
                    if product_id == 1:  # Cosentyx - brutal decline
                        base_units = 45000 if year == 2022 else (25000 if year == 2023 else 8000)
                        units = base_units + random.randint(-2000, 2000)
                    else:  # Other drugs - stable
                        units = random.randint(18000, 22000)
                    
                    revenue = units * random.uniform(150, 300)
                    sales_data.append((product_id, region, country, quarter, year, units, revenue))
    
    cursor.executemany('''
        INSERT INTO sales (product_id, region, country, quarter, year, units_sold, revenue_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', sales_data)
    
    conn.commit()
    conn.close()
    print("Pharmaceutical sales database created successfully!")

if __name__ == "__main__":
    create_pharma_database()