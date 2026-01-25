import json
import pandas as pd

def process_competitions_data(input_file='competitions.json', output_file='competition_ratings.xlsx'):
    """
    Process competitions.json to create a dataset where:
    - Rows are countries
    - Columns are division levels
    - Values are AvgTeamRating
    """
    # Load the JSON data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Create a dictionary to store the data
    # Structure: {country: {division_level: AvgTeamRating}}
    country_division_ratings = {}
    
    # First pass: collect all countries and division levels
    all_countries = set()
    all_divisions = set()
    
    for competition in data:
        country = competition.get('Country')
        division_level = competition.get('DivisionLevel')
        
        if country is not None:
            all_countries.add(country)
        if division_level is not None:
            all_divisions.add(division_level)
    
    # Initialize all countries with "NO DATA" for all division levels
    for country in all_countries:
        country_division_ratings[country] = {div: "NO DATA" for div in all_divisions}
    
    # Second pass: fill in actual data
    for competition in data:
        country = competition.get('Country')
        division_level = competition.get('DivisionLevel')
        avg_rating = competition.get('AvgTeamRating')
        
        # Skip if any required field is missing
        if country is None or division_level is None:
            continue
        
        # Store the rating (None values will become NaN, actual values will replace "NO DATA")
        country_division_ratings[country][division_level] = avg_rating
    
    # Convert to DataFrame
    df = pd.DataFrame.from_dict(country_division_ratings, orient='index')
    
    # Sort columns by division level
    df = df.reindex(sorted(df.columns), axis=1)
    
    # Sort rows by Division 1 rating (descending, with NaN and "NO DATA" at the end)
    # First, create a temporary column for sorting
    df['_sort_key'] = df[1].apply(lambda x: float(x) if isinstance(x, (int, float)) else -1)
    df = df.sort_values('_sort_key', ascending=False)
    df = df.drop('_sort_key', axis=1)
    
    # Rename columns to be more descriptive
    df.columns = [f'Division_{col}' for col in df.columns]
    
    # Replace all numeric values with 1, keep "NO DATA" as is, and keep NaN as is
    for col in df.columns:
        df[col] = df[col].apply(lambda x: 1 if isinstance(x, (int, float)) and pd.notna(x) else x)
    
    # Save to Excel
    df.to_excel(output_file, sheet_name='Competition Ratings')
    
    print(f"Dataset created successfully!")
    print(f"Shape: {df.shape[0]} countries x {df.shape[1]} division levels")
    print(f"\nSaved to: {output_file}")
    print(f"\nFirst few rows:\n")
    print(df.head(10))
    print(f"\nSummary statistics:\n")
    print(df.describe())
    
    return df

if __name__ == '__main__':
    df = process_competitions_data()
