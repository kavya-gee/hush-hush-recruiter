import pandas as pd

# Load the CSV file
input_file = 'Contributors_Details_Final.csv'
df = pd.read_csv(input_file)

# Calculate the number of rows per file
total_rows = len(df)
rows_per_file = total_rows // 5

# Split the DataFrame into 5 parts
for i in range(5):
    start_row = i * rows_per_file
    end_row = (i + 1) * rows_per_file if i < 4 else total_rows  # Ensure the last file gets the remaining rows
    
    # Create a new DataFrame for the split data
    split_df = df.iloc[start_row:end_row]
    
    # Save the split DataFrame to a new CSV file
    output_file = f'Contributors_Details_Part_{i + 1}.csv'
    split_df.to_csv(output_file, index=False)
    
    print(f'Saved {output_file} with {len(split_df)} rows.')

print("Splitting completed!")