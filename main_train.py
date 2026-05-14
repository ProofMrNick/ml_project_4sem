
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


SEED = 123

df = pd.read_csv("df_ready.csv")
df.dropna(subset=["description", "category"], inplace=True)
df.drop(columns=["Unnamed: 0"], inplace=True)



### ========== EDA ==========
print((df["category"].str.endswith("Recipes")).sum(), df.shape)  # 2498 (2498, 8)
df["category"] = df["category"].apply(lambda cat: " ".join(cat.split()[:-1]))  # all categories contian "recipes" as the last word => it's not neede here


df["ingredient_count"] = df["ingredients"].str.split(",").str.len()
df["description_length"] = df["description"].str.len()
df["step_words_count"] = df["cooking_steps"].str.split().str.len()

print(
    (df[ df["step_words_count"].notna() ]["step_words_count"]).describe()
)

print(df.head(12))
df["step_words_count"] = df["step_words_count"].fillna(np.inf)
df = df[df["step_words_count"] >= 10]
df["step_words_count"] = df["step_words_count"].apply(lambda stp: stp if stp < np.inf else np.nan)  # dropping all rows with suspicious;y small numer of words in steps 

print(df.shape)
print(df.isna().sum())


box = plt.boxplot(df[ df["step_words_count"].notna() ]["step_words_count"])
mx = [item.get_ydata()[1] for item in box["whiskers"]][1]
print(mx)  # value of the top whisker (aka "max value" but avoiiding outliers)
print(len([
    dot for dot in df[ df["step_words_count"].notna() ]["step_words_count"] \
    if dot > mx
]))  # number of outliers (of the top whisker)
plt.savefig("plot1.png")



### ========== feature engineering ==========
# some helper functions
c = 0
def func(stp):
  global c
  stp = str(stp)
  stp = " ".join(stp.split())  # to eliminate \t, \n and multiple whitespaces 
  words = stp.split()

  for i in range(len(words)):
    if words[i] == "heat" and words[i - 1] in ["low", "medium", "high", "medium-low", "medium-high"]:
      c += 1
      return words[i - 1]

  return ""


def func_temp(stp, stat_func):
  stp = str(stp)
      
  temps = []
  stp = stp.replace("°", " ")  # degrees are sometimes marked as "°C"
    
  stp = " ".join(stp.split()) 
  words = stp.split()

  for i in range(len(words)):
    if words[i] in ["degree", "C"] and words[i - 1].isdigit():  # "C" = dgrees Celcius
      temps.append(int(words[i - 1]))

  if len(temps) == 0:
      return 0

  return stat_func(temps)


def func_time(stp):
  stp = str(stp)
  minutes = []

  stp = " ".join(stp.split()) 
  words = stp.split()

  for i in range(len(words)):
    if any([word for word in ["minute", "min"] if word in words[i]]) \
    and words[i - 1].isdigit():
        minutes.append(int(words[i - 1]))
    elif any([word for word in ["hour", "hr"] if word in words[i]]):  # hrs = hours
        try:
            minutes.append(60 * float(words[i - 1]))  # as it can be "1.5 hours" or smth like that
        except:
            continue

  if len(minutes) == 0:
      return 0

  return sum(minutes) 


df["heat_type"] = df["cooking_steps"].apply(lambda stp: func(stp))
print(c)

df["has_oven_keyword"] = df["cooking_steps"].apply(lambda stp: "oven" in str(stp).lower()).astype(int)
df["has_stove_keyword"] = df["cooking_steps"].apply(lambda stp: "stove" in str(stp).lower()).astype(int)
df["has_bbq_keyword"] = df["cooking_steps"].apply(lambda stp: "bbq" in str(stp).lower()).astype(int)
df["has_pan_keyword"] = df["cooking_steps"].apply(lambda stp: "pan" in str(stp).lower()).astype(int)
df["has_grill_keyword"] = df["cooking_steps"].apply(lambda stp: "grill" in str(stp).lower()).astype(int)

df["has_easy_keyword"] = df["description"].apply(lambda stp: "easy" in str(stp).lower()).astype(int)
df["has_slow_keyword"] = df["cooking_steps"].apply(lambda stp: "slow" in str(stp).lower()).astype(int)
df["has_bake_keyword"] = df["cooking_steps"].apply(lambda stp: "bak" in str(stp).lower()).astype(int)  # can be "bake" or "baking" => common part is "bak"

df["prep_ratio"] = df["cooking_steps"].apply(lambda stp: str(stp).lower().count("prep") / len(str(stp).split()))  # probably recipes with a ton of prepping require less time for actual cooking
df["ingredient_density"] = df.apply(lambda row: row["step_words_count"] / row["ingredient_count"], axis=1)  # how much words of cooking steps are required per each ingresient

stats = {
    "min": lambda x: min(x), 
    "max": lambda x: max(x), 
    "sum": lambda x: sum(x), 
    "avg": lambda x: sum(x) / len(x),
}

for stat in list(stats.keys()):
    df[f"temp_{stat}"] = df["cooking_steps"].apply(lambda temp: func_temp(temp, stats[stat]))  # calculating min, max, ... of tempretaures (if presented)

df["extracted_minutes"] = df["cooking_steps"].apply(lambda stp: func_time(stp))


print(df[ df["extracted_minutes"].notna() ])

#print(df[ df["cooking_steps"].apply(lambda stp: "degree" in str(stp).lower()) ])


print()
print( df[ df["total_time_minutes"] < df["extracted_minutes"] ][["total_time_minutes", "extracted_minutes"]] )
# turns out, there's a grammatic mistake in the cooking steps: someone has written "... 10013 minutes..." instead of (supposedly) "...10-13 minutes..." (they messed up "-" and "0" on their keyboard lol) 

print(df[ df["extracted_minutes"] == 80160.0 ][["title", "total_time_minutes", "extracted_minutes"]])
print(df.shape)



### ========== splitting ==========
# dropping rows where thre's only 1 value in  a "category" group (will come in handy during splittign)
val_counts = dict(df["category"].value_counts())
print(val_counts)
df = df[~df["category"].isin([
    [categ for categ in val_counts.keys() if val_counts[categ] == val][0] for val in list(val_counts.values()) if val <= 1
])]
print(df.shape)
print(df.columns)


# splitting
X = df.drop(columns=[
    "total_time_minutes", 
    "cooking_steps",
    "description",
    "ingredients",
])
y = df["total_time_minutes"]  # target


X_train, X_test, y_train, y_test = train_test_split(
    X, 
    y, 
    test_size=0.2, 
    random_state=SEED, 
    stratify=df["category"]
)

# top outliers separately for train (to avoid data leakage!!!)
box_train = plt.boxplot(X_train[ X_train["step_words_count"].notna() ]["step_words_count"])
mx_train = [item.get_ydata()[1] for item in box_train["whiskers"]][1]

print(mx_train)


# ========== imputation (servings + coking steps words count) ==========

# imputing num_of_servings (simple median by category, as RF will be too much)
X_train["servings_imputed"] = X_train["num_of_servings"].isna().astype(int)  # flag that teh value was imputed 
X_test["servings_imputed"] = X_test["num_of_servings"].isna().astype(int)

X_train["num_of_servings"] = X_train.groupby("category")["num_of_servings"] \
    .transform(
    lambda serv: serv.fillna(serv.median())
)

# filling any stray rows (those weher it's impossible to group by category )
global_median = X_train["num_of_servings"].median()
X_train["num_of_servings"] = X_train["num_of_servings"].fillna(
    global_median
)

# applying to x_test (using x_train medians) 
train_medians = X_train.groupby("category")["num_of_servings"].median().to_dict()
print(train_medians)

X_test["num_of_servings"] = X_test.groupby("category")["num_of_servings"] \
    .transform(
    lambda serv: serv.fillna(
        train_medians.get(serv.name, global_median)
    )
)



# imputing coking steps words count
train_known = X_train[X_train["step_words_count"].notna()]
train_missing = X_train[X_train["step_words_count"].isna()]

test_known = X_test[X_test["step_words_count"].notna()]
test_missing = X_test[X_test["step_words_count"].isna()]

imputation_helpers = ["ingredient_count", "description_length", "num_of_servings"]
step_count_imputer = RandomForestRegressor(
    n_estimators=20, 
    max_depth=3, 
    random_state=SEED
)

X_train["steps_imputed"] = X_train["step_words_count"].isna().astype(int)  # flag that teh value was imputed 
X_test["steps_imputed"] = X_test["step_words_count"].isna().astype(int)

# X_train
step_count_imputer.fit(
    train_known[imputation_helpers], 
    train_known["step_words_count"]
)
X_train.loc[train_missing.index, "step_words_count"] = np.clip(
    step_count_imputer.predict(train_missing[imputation_helpers]), 20, mx_train
)  # forcing  the values into range [20, mx_train] to avoid unexpected behavior

# X_test (predicting based on X train)
X_test.loc[test_missing.index, "step_words_count"] = np.clip(
    step_count_imputer.predict(test_missing[imputation_helpers]), 20, mx_train
)  # forcing  the values into range [20, mx_train] to avoid unexpected behavior


# applying after imputing 
X_train["ingredient_density"] = X_train.apply(lambda row: row["step_words_count"] / row["ingredient_count"], axis=1)

X_test["ingredient_density"] = X_test.apply(lambda row: row["step_words_count"] / row["ingredient_count"], axis=1)


print(X_train.isna().sum())  # => no more missing values (yay!)
print(X_test.isna().sum())



### ========== encoding ==========
categs = set()
for cat in list(X_train["category"]):
    categs.update(cat.split())  # there's category called "Healthy Chicken", while both "Healthy" and "Chicken" categories are also presented => encoding them keeping this in mind

print(categs)

for categ in categs:
    X_train[f"cat_{categ}"] = X_train["category"].apply(lambda cat: 1 if categ in cat else 0)  # using "in" operator aas it can be thsi: "Chicken" in "Healthy Chicken"
    X_test[f"cat_{categ}"] = X_test["category"].apply(lambda cat: 1 if categ in cat else 0)


heat_types = set()
for type in list(X_train["heat_type"]):
    heat_types.update(type.split())

print(heat_types)

for type in heat_types:
    X_train[f"cat_{type}"] = X_train["heat_type"].apply(lambda tp: 1 if type == tp else 0)
    X_test[f"cat_{type}"] = X_test["heat_type"].apply(lambda tp: 1 if type == tp else 0)

print(X_train.head(20))


X_train.drop(columns=[
    "title",
    "category",
    "heat_type"
], inplace=True)

X_test.drop(columns=[
    "title",
    "category",
    "heat_type"
], inplace=True)

    

### ========== training + hyper parameter tuning ==========
# log-transofrm to dela with long tail (target is skewed)
y_train_log = np.log1p(y_train)  # log(1 + minutes)
y_test_log = np.log1p(y_test)


# hyper param tuning + 3 fold cross-val (UNCOMMENT TO LAUNCH)
# commented out because i don't wanna wait for an eternity every time i run the script
'''
params = {
    "n_estimators": [50, 100, 125, 150, 175, 200, 250, 500],
    "max_depth": [12, 15, None],
    "min_samples_leaf": [3, 5],
    "max_features": ["sqrt", "log2", None]
}

grid = GridSearchCV(
    RandomForestRegressor(random_state=SEED, n_jobs=-1),
    params,
    cv=3,
    scoring="neg_mean_absolute_error",
    verbose=0
)

grid.fit(X_train, y_train_log)

print(f"best params: {grid.best_params_}")  # best params {'max_depth': 12, 'max_features': None, 'min_samples_leaf': 3, 'n_estimators': 500}
print(f"best cross-val MAE (LOGARITHMIC!!!): {(-grid.best_score_):.3f}")

# evaluating performance on test set
best_model = grid.best_estimator_

y_pred_log = best_model.predict(X_test)
y_pred = np.expm1(y_pred_log)

mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)
print(f"test metrics: MAE={mae:.2f} minutes, R^2={r2:.3f}")
'''


# training RF with best parametres from hyper param tuning
rf = RandomForestRegressor(
    n_estimators=500,
    max_depth=None,
    min_samples_leaf=3,
    random_state=SEED, 
    n_jobs=-1
)


rf.fit(X_train, y_train_log)
y_pred_log = rf.predict(X_test)

y_pred = np.expm1(y_pred_log)

# metrcis + evauation
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)
median_ae = np.median(np.abs(y_test - y_pred))

print()
print("GLOBAL METRCIS RESULTS:")  # global metrics
print(f"MAE:       {mae:.2f} minutes")
print(f"RMSE:      {rmse:.2f} minutes")
print(f"R^2:       {r2:.3f}")
print(f"Median AE: {median_ae:.2f} minutes")



# perfromance metrics by chunks of cooking time (0-30 minutes, 30-50 minutes, ...)
eval_df = pd.DataFrame({
    "y_true": y_test,
    "y_pred": y_pred,
    "error": np.abs(y_test - y_pred)
})

# chunks
chunks = [
    (0, 30, "<30 min"),
    (30, 60, "30-60 min"),
    (60, 120, "1-2 hours"),
    (120, 180, "2-3 hours"),
    (180, 240, "3-4 hours"),
    (240, 300, "4-5 hours"),
    (300, 3000, ">5 hours")
]

print()
print("CHUNKWISE METRICS:")
for low, high, label in chunks:
    query = (eval_df["y_true"] >= low) & (eval_df["y_true"] < high)
    n = eval_df[query].shape[0]
    if n > 0:
        mae = eval_df[query]["error"].mean()
        median = eval_df[query]["error"].median()
        within_20 = (eval_df[query]["error"] <= 20).mean() * 100
        
        print(f"{label:12s} (n={n:3d}): MAE={mae:5.1f} min, Median={median:5.1f} minutes, witihin 20 minutes={within_20:5.1f}%")  # "within 20 minutes" = percentage of vlaues where error is <20 minutes



# 10 worst predictions
print()
print("10 LARGEST ERRORS:")
print( eval_df.sort_values("error", ascending=False).head(10).to_string() )




