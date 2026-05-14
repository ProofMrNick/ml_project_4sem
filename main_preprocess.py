
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt 


### === PREPROCESSING PARSED DF INTO READY-TO-USE FORM (imputation and feture engineering see in main_train.py) ===

df = pd.read_csv("df_parsed_recipes.csv")
print(df.head())
print(df.columns)

print(df.dtypes)
print(df.isna().sum())

print(df[df.duplicated(subset=["source_url"])].shape)  # no duplicates (yay!)

mask = df["description"].astype(str).str.startswith("This mouth-watering recipe is ready in just")
print(mask.sum())



df.rename(columns={
  "genre": "category"
}, inplace=True)
df.drop(columns=["Unnamed: 0", "source_url", "total_time_raw"], inplace=True)
df.dropna(subset="total_time_minutes", inplace=True)
print(df.shape)


c = 0
def extract_time(row):  # could've been an inline function but meh, this one's cleaner
  time_mins = 0
  global c
  
  if (not pd.isna(row["total_time_minutes"])) \
  and isinstance(row["description"], str) \
  and row["description"].startswith("This mouth-watering recipe is ready in just"):
    words = row["description"].split("mouth-watering recipe is ready in just")[1].split()

    for i in range(len(words)):
      if words[i].isdigit():
        if words[i + 1] in ["hour", "hours"]:
          time_mins += int(words[i]) * 60
          
        if words[i + 1] in ["minute", "minutes"]:
          time_mins += int(words[i])
          c += 1
          break

  return ( time_mins if time_mins > 0 else row["total_time_minutes"] )

df["total_time_minutes"] = df.apply(lambda row: extract_time(row), axis=1)
print(df["total_time_minutes"])
print(c)


def process_servings(row):
  if pd.isna(row["num_of_servings"]):
    return row["num_of_servings"]
  
  words = row["num_of_servings"].split()
  
  for word in words:
    if word.replace(".", "").isdigit():
      return float(word)

  
  
df["num_of_servings"] = df.apply(lambda row: process_servings(row), axis=1)

df["ingredients"] = df["ingredients"].apply(lambda ing: ing.replace("[", "").replace("'", "") if not pd.isna(ing) else ing)
df["cooking_steps"] = df["cooking_steps"].apply(lambda stp: stp.replace("[", "").replace("'", "") if not pd.isna(stp) else stp)


print(df.isna().sum())
print(df.dtypes)
print()
print(df.head())
df.to_csv("df_ready.csv")
