import pandas as pd

events = pd.read_csv("matches/2025-09-20/events.csv")


import numpy as np    

possession_counts = (
    events["possession_team"]
    .ne(events["possession_team"].shift(1))
    .groupby(events["possession_team"])
    .sum()
)
df = pd.DataFrame()
df["possession_team"] = possession_counts.index
df["possession_count"] = possession_counts.values
print(df)



