
import requests
from bs4 import BeautifulSoup, Comment
import pandas as pd
import time
import random
import re
import json
import shutil
import os


# IMPORTANT: on cooking websites, it's a common thing when recipes are presented in a form of a <meta> tag containing all the needed informataion (cooking time, ingredients, recipe steps, ...) - individual pieces of info are marked with "@" (this is all done for SEO). so, keepig that in mind, the extarction of this data will be dealing with that <meta> tag

# collecting URLs
def get_foodnetwork_uk_urls(
    start_page=2, 
    end_page=25,
    base_url="https://foodnetwork.co.uk/collections/chicken-recipes"  # can be modifieed if more URLs are needed
):
    urls = []
    for page in range(start_page, end_page + 1):
        page_url = f"{base_url}?recipes={page}"
        print(f"fetching pagge {page}: {page_url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            
            response = requests.get(page_url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for link_tag in soup.find_all("a", class_="block group"):
                href = link_tag.get("href")
                if href and href.startswith("http"):
                    clean_url = href.strip()
                    if clean_url not in urls:
                        urls.append(clean_url)

            print(f"found {len([a for a in soup.find_all('a', class_='block group') if a.get('href')])} recipe links")
            time.sleep(random.uniform(1.5, 3.0))  # to avoid getting banned for "too many requests"
            
        except requests.RequestException as e:
            print(f"ERROR AT PAGE {page}: {e}")
            continue

    with open("foodnetwork_uk_urls.txt", "a", encoding="utf-8") as f:  # mode = "a" so that new URLS can be added over time (if needed)
        for u in urls:
            f.write(u + "\n")
    print()
    print(f"total unique URLs collected: {len(urls)}")
    
    return urls



# helper funcs (mostly working with "schema" - an html meta tag that contains all the needed info (it's made primarily for seach engine s))
def clean_text(text):
    if not text:
        return None
        
    text = " ".join(text.split())  # getting rid of \t, \n and multiple whitesapces
    text = re.sub(r'^[\s\•\-\*\u2022]+\s*', '', text)  # gwtting rid of every other garbage character, like bulletpoints, "-", etc
    
    return text if text else None


def parse_iso_duration(iso_str):  # decodes coking time in fromat like "1H30M"
    if not isinstance(iso_str, str):
        return None
        
    iso_str = iso_str.upper().strip()
    if not iso_str.startswith("PT"):
        return parse_time_to_minutes(iso_str)  # if string is not in a corect format

    total = 0
    hours = re.search(r'(\d+)H', iso_str)  # parsing hours
    if hours:
        total += int(hours.group(1)) * 60
    
    mins = re.search(r'(\d+)M', iso_str)  # parsing minites
    if mins:
        total += int(mins.group(1))
        
    return total if total > 0 else None
    

def parse_time_to_minutes(time_str):  # parsing string if it's NOT in iso format
    if not isinstance(time_str, str):
        return None
        
    time_str = time_str.lower().strip()
    total = 0
    
    h = re.search(r'(\d+)\s*(?:hr|hour|hrs|hours)', time_str)
    if h: 
        total += int(h.group(1)) * 60
        
    m = re.search(r'(\d+)\s*(?:min|minute|mins|minutes)', time_str)
    if m: 
        total += int(m.group(1))
        
    if total == 0:
        num = re.search(r'^\s*(\d+)\s*$', time_str)
        if num: 
            total = int(num.group(1))
            
    return total if total > 0 else None

    
def extract_json_ld_recipe(soup):
    scripts = soup.find_all("script", type="application/ld+json")
    
    for script in scripts:
        try:
            json_text = script.get_text() or script.string  # handling None (if occured)
            if not json_text:
                continue
                
            data = json.loads(json_text)

            # extracting recipe from <meta> (so much complexity as sometimes webpages can have different structure => handling all possible outcomes))
            if isinstance(data, dict) and "@graph" in data:
                for item in data["@graph"]:
                    if item.get("@type") == "Recipe":
                        return item
                        
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("@type") == "Recipe":
                        return item
                        
            elif isinstance(data, dict) and data.get("@type") == "Recipe":
                return data
                
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
            
    return None
    

# actually parisng the extracted instructions 
def parse_instructions_html(instructions):
    if not instructions:
        return []

    steps = []
    # once again, handling all posible cases: format of dict, list oor sting
    if isinstance(instructions, list):
        for item in instructions:
            if isinstance(item, dict):
                # website uses schema.org format: {"@type": "...", "text": "..."}
                text = item.get("text") or item.get("itemText")
                if text:
                    # if text contains html , parsing it
                    if "<" in text:
                        sub_soup = BeautifulSoup(text, "html.parser")
                        for p in sub_soup.find_all(["p", "li"]):
                            step = clean_text(p.get_text())
                            if step:  # checking if cleaned text in not an empty string
                                steps.append(step)
                    else:
                        cleaned = clean_text(text)
                        if cleaned:
                            steps.append(cleaned)
                            
            elif isinstance(item, str):
                if "<" in item:  # if html
                    sub_soup = BeautifulSoup(item, "html.parser")
                    for p in sub_soup.find_all(["p", "li"]):
                        step = clean_text(p.get_text())
                        if step:
                            steps.append(step)
                else:
                    cleaned = clean_text(item)
                    if cleaned:
                        steps.append(cleaned)
                        
    elif isinstance(instructions, str):
        # if presented in a form of a single string with html
        if "<" in instructions:
            sub_soup = BeautifulSoup(instructions, "html.parser")
            for p in sub_soup.find_all(["p", "li"]):
                step = clean_text(p.get_text())
                if step:
                    steps.append(step)
        else:
            cleaned = clean_text(instructions)
            if cleaned:
                steps.append(cleaned)

    return [s for s in steps if s]  # removing any empty strings



# main parser function (retrieves data form the website for it to be then processed)
def scrape_recipe_full(url):
    # pretending to be a real user as otherwise some websites may may not allow in :( 
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["style", Comment]):  # removing styles and commets
            element.decompose()
            
        for script in soup.find_all("script"):
            if script.get("type") != "application/ld+json":
                script.decompose()  # deleting tag entirely 

        # extracting json-ld (which is a machine-readable recipe schema)
        json_ld = None
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                json_text = script.string or script.get_text()
                if not json_text:
                    continue
                data = json.loads(json_text)

                # handling recipe (trying all oossinble scenarios)
                if isinstance(data, dict) and data.get("@type") == "Recipe":
                    json_ld = data
                    break
                    
                elif isinstance(data, dict) and "@graph" in data:
                    for item in data["@graph"]:
                        if isinstance(item, dict) and item.get("@type") == "Recipe":
                            json_ld = item
                            break
                            
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Recipe":
                            json_ld = item
                            break
                            
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue

        result = { "source_url": url }

        # now retrieving all the columns for the future dataset
        # extracting title (trying both html parsing and retrieving from json-ld)
        title_tag = soup.find("h1", class_="mb-4 print:text-black p-name")
        result["title"] = clean_text(title_tag.get_text()) if title_tag else None
        
        if not result["title"] and json_ld and json_ld.get("name"):  # if html's "title " is empty
            result["title"] = clean_text(json_ld["name"])

        # cooking time (from json-d as it's loaded dynamically) => it's the target variable!!!
        result["total_time_minutes"] = None
        result["total_time_raw"] = None

        if json_ld:
            # prefering cook_time, but if not present, switching to to total_time, then prep_time
            time_val = json_ld.get("cookTime") or json_ld.get("totalTime") or json_ld.get("prepTime")
            
            if time_val:
                result["total_time_raw"] = time_val
                # parsing format like "PT45M" or  "PT1H30M"
                if isinstance(time_val, str) and time_val.startswith("PT"):
                    hours = re.search(r'(\d+)H', time_val)
                    mins = re.search(r'(\d+)M', time_val)
                    total = 0
                    if hours: total += int(hours.group(1)) * 60
                    if mins: total += int(mins.group(1))
                    result["total_time_minutes"] = total if total > 0 else None
                else:
                    # if not in correct format, switching to basic string parsing
                    result["total_time_minutes"] = parse_time_to_minutes(time_val)

        # description (trying both json-ld nad html)
        desc_tag = soup.find("p", class_="font-medium mt-8 lg:mt-12 p-summary")
        result["description"] = clean_text(desc_tag.get_text()) if desc_tag else None
        
        if not result["description"] and json_ld and json_ld.get("description"):
            result["description"] = clean_text(json_ld["description"])

        # list of ingredients (html + json-ld)
        ingredients = []
        for label in soup.find_all("label", class_="font-medium ml-4 text-[13px] p-ingredient"):
            text = clean_text(label.get_text())
            if text:
                ingredients.append(text)
        
        if not ingredients and json_ld and json_ld.get("recipeIngredient"):
            ingredients = [clean_text(ing) for ing in json_ld["recipeIngredient"] if clean_text(ing)]
        result["ingredients"] = ingredients if ingredients else None

        # cooking steps (html + json-ld)
        cooking_steps = []
        steps_container = soup.find("div", class_="legacy-method content e-instructions")
        if steps_container:
            for p_tag in steps_container.find_all("p"):
                step_text = clean_text(p_tag.get_text(separator=' ', strip=True))
                if step_text:
                    cooking_steps.append(step_text)
        
        if not cooking_steps and json_ld and json_ld.get("recipeInstructions"):
            instructions = json_ld["recipeInstructions"]
            if isinstance(instructions, list):
                for item in instructions:
                    text = None
                    if isinstance(item, dict):
                        text = item.get("text") or item.get("itemText")
                    elif isinstance(item, str):
                        text = item
                        
                    if text:
                        # removing html tags if present
                        if "<" in text:
                            text = BeautifulSoup(text, "html.parser").get_text()
                        cleaned = clean_text(text)
                        if cleaned:
                            cooking_steps.append(cleaned)
        result["cooking_steps"] = cooking_steps if cooking_steps else None

        # num of servings (tried to retrieve it from html but failed miserably (turns out, num of servings is loaded dynamicaly for some reson) so thre's only json-ld verison)
        result["num_of_servings"] = None
        if json_ld and json_ld.get("recipeYield"):
            yield_val = json_ld["recipeYield"]

            # trying both list asn string format
            if isinstance(yield_val, list):
                yield_val = yield_val[0] if yield_val else None
            if yield_val:
                result["num_of_servings"] = clean_text(str(yield_val))

        # genre (or like the "featured in" tab at the very bottom of the webpage)
        genre_tag = soup.find("a", class_="block text-[12px] uppercase text-maroon underline whitespace-nowrap")
        result["genre"] = clean_text(genre_tag.get_text()) if genre_tag else None
        
        if not result["genre"] and json_ld and json_ld.get("recipeCuisine"):
            result["genre"] = clean_text(json_ld["recipeCuisine"])

        # loggin g out
        found = [
            k for k, v in result.items() if v is not None and k != "source_url"
        ]
        print(f"extracted { len(found) } / 7 fields: { ', '.join(found) }")
        
        return result

    
    except Exception as e:
        print(f"ERROR: {e}")
        
        return None



# helper functions
# loading csv (if exists), otherwise returning elmpty df with columsn
def load_existing_df(filepath):
    if os.path.exists(filepath):
        try:
            return pd.read_csv(filepath)
        except Exception as e:
            print(f"NO DF EXISTS '{filepath}': {e}. RETURNING EMPTY DF")
    
    return pd.DataFrame(columns=[
        "source_url", 
        "title", 
        "total_time_raw", 
        "total_time_minutes",
        "description", 
        "ingredients", 
        "cooking_steps", 
        "num_of_servings", 
        "genre"
    ])


# saving df (backup is a temporary df needed in case smth goes wrong with saving chunks of URLs data), so it's like this: copying old df -> writing new one -> if no errrors, deleting backup 
def save_df_with_backup(df, filepath):
    if os.path.exists(filepath):  # creating back up 'cause i dont wanna lose my parsed data
        shutil.copy(filepath, filepath + ".bak")
    
    df.to_csv(filepath, index=False, encoding="utf-8")
    
    if os.path.exists(filepath + ".bak"):
        try:
            os.remove(filepath + ".bak")
        except:
            pass  # keeping backup if errorr




### MAIN PARSING PIPELINE
def main_pipeline(
    chunk_size=100,  # size of URL chink (how many urls should me processed before appending to the dataframe file)
    output_file="df_parsed_recipes.csv",
    start_from_url="https://foodnetwork.co.uk/recipes/yucatan-chicken-skewers-with-peanut-red-chile-bbq-sauce-and-red-cabbage-slaw"  # to resume parsing form a specific URl 
):
    try:
        with open("foodnetwork_uk_urls.txt", "r", encoding="utf-8") as f:
            all_urls = [ line.strip() for line in f if line.strip() ]
        print(f"tota: {len(all_urls)} urls loaded")
        
    except FileNotFoundError:
        print("ERROR: FILE NOT FOUND!!!")
        
        return

    df_existing = load_existing_df(output_file)
    processed_urls = ( set(df_existing["source_url"].dropna().tolist()) \
                       if "source_url" in df_existing.columns \
                       else set() )
    print(f"already p rocessed: {len(processed_urls)} URLs")

    # skipping alrady processed urls + startig from url "start_from_url"
    urls_to_process = []
    resume_mode = start_from_url is not None
    for url in all_urls:
        if resume_mode and url != start_from_url:
            continue  # skip until the "satrt_from_url" is found
        resume_mode = False  # found it
        
        if url not in processed_urls:
            urls_to_process.append(url)

    if not urls_to_process:
        print("ALL urls have processed")
        
        return df_existing
        

    print(f"urls to be processed: {len(urls_to_process)}")
    
    total_chunks = (len(urls_to_process) + chunk_size - 1) // chunk_size
    global_start_idx = len(processed_urls)

    for chunk_idx in range(total_chunks):
        chunk_start = chunk_idx * chunk_size
        chunk_end = min( chunk_start + chunk_size, len(urls_to_process) )
        chunk_urls = urls_to_process[chunk_start:chunk_end]

        print("=============================")
        print(f"chunk num {chunk_idx + 1} of {total_chunks}: URLs [{global_start_idx + chunk_start + 1}:{global_start_idx + chunk_end + 1}]")
        print("=============================")

        chunk_results = []

        try:
            for local_idx, url in enumerate(chunk_urls, 1):
                global_idx = global_start_idx + chunk_start + local_idx
                print(f"[{global_idx} of {len(all_urls)}] {url}")

                data = scrape_recipe_full(url)

                if data and data.get("title"):
                    chunk_results.append(data)
                    print(f"loaded {data['title'][:45]}...")
                else:
                    print(f"ERROR: skipped this url")

                time.sleep(random.uniform(0.8, 1.8))  # artificial delay to not get banned by the website...

            # appending results into df
            if chunk_results:
                df_chunk = pd.DataFrame(chunk_results)
                df_updated = pd.concat([df_existing, df_chunk], ignore_index=True)

                save_df_with_backup(df_updated, output_file)

                # adding processed urls to the processed_urls
                new_processed = set(df_chunk["source_url"].dropna().tolist())
                processed_urls.update(new_processed)
                df_existing = df_updated  # ready for enxt chunk

                print(f"chunk processed: { len(chunk_results) } new recipes; total: { len(df_existing) }")
            else:
                print(f"ERROR: NO DATA EXTRACTED FORM TEH CHUNK")

            # some more debug logs
            remaining = len(urls_to_process) - chunk_end
            if remaining > 0:
                print(f"urls left: {remaining}")
                time.sleep(3)

        # important: process can be SAFELY stopped wioth CTRL + C
        except KeyboardInterrupt:
            print()
            print(f"STOPPING")
            print(f"saved: {len(df_existing)} recipes in '{output_file}'")
            
            return df_existing

        except Exception as e:
            print(f"ERROR IN CHUNK {chunk_idx+1}: {e}")
            
            return df_existing

    print()
    print(f"all chunks finished")
    print(f"total: {len(df_existing)} recipes saved to '{output_file}'")

    return df_existing



### LAUCNCHING THE PROCESS
CHUNK_SIZE = 100
OUTPUT_FILE = "df_parsed_recipes.csv"

get_foodnetwork_uk_urls()

try:
    with open("foodnetwork_uk_urls.txt", "r", encoding="utf-8") as f:
        all_urls = [line.strip() for line in f if line.strip()]
    print(f"loaded {len(all_urls)} URLs")
    
except FileNotFoundError:
    print("EEROR: FILE NOT FOUND")
    exit(1)

if os.path.exists(OUTPUT_FILE):
    try:
        df_existing = pd.read_csv(OUTPUT_FILE)
        processed = set(df_existing["source_url"].dropna().astype(str).tolist())
        processed.discard("nan")  # removing NaNs (if any)
        print(f"process resumed: {len(processed)} urls already processed")
        
    except Exception as e:
        print(f"FAILED TO LOAD CSV: {e}. STARTING FROM SCRATCH")
        
        df_existing = pd.DataFrame(columns=[
            "source_url", 
            "title", 
            "total_time_raw", 
            "total_time_minutes",
            "description", 
            "ingredients", 
            "cooking_steps", 
            "num_of_servings", 
            "genre"
        ])
        processed = set()
        
else:
    df_existing = pd.DataFrame(columns=[
        "source_url", 
        "title", 
        "total_time_raw", 
        "total_time_minutes",
        "description", 
        "ingredients", 
        "cooking_steps", 
        "num_of_servings", 
        "genre"
    ])
    processed = set()

urls_to_scrape = [ url for url in all_urls if url not in processed ]
print(f"total: {len(urls_to_scrape)} new URLs to process")

if not urls_to_scrape:
    print("ALL urls processed")
    exit(0)

global_counter = len(processed)

try:
    for chunk_start in range(0, len(urls_to_scrape), CHUNK_SIZE):
        chunk_end = min(chunk_start + CHUNK_SIZE, len(urls_to_scrape))
        chunk_urls = urls_to_scrape[chunk_start:chunk_end]

        print(f"chunk: URLs [{chunk_start + 1}:{chunk_end}] of {len(urls_to_scrape)}")

        for local_idx, url in enumerate(chunk_urls, 1):
            global_counter += 1
            print(f"[{global_counter} of {len(all_urls)}] {url[:70]}...")

            try:
                data = scrape_recipe_full(url)
                if data and data.get("title"):
                    df_existing = pd.concat([ df_existing, pd.DataFrame([data]) ], ignore_index=True)
                    df_existing.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
                    processed.add(url)
                    print(f"SAVED: {data['title'][:40]}...")
                else:
                    print(f"URL SKIPPED")
                    
            except KeyboardInterrupt:
                print()
                print(f"STOPPED WITH CTRL + C")
                print(f"last successful save: { len(df_existing) } recipes in '{OUTPUT_FILE}'")
                
                exit(0)

            time.sleep(random.uniform(0.8, 1.8))

        print(f"chunk complete; total saved: {len(df_existing)}")
        if chunk_end < len(urls_to_scrape):
            time.sleep(2)

    print(f"ALL DONE!!! final count: {len(df_existing)} recipes in '{OUTPUT_FILE}'")

except KeyboardInterrupt:
    print()
    print(f"STOPPED WITH CTRL + C")
    print(f"saved: { len(df_existing) } recipes in '{OUTPUT_FILE}'")
    exit(0)
    
except Exception as e:
    print(f"ERROR: {e}")
    if len(df_existing) > 0:
        df_existing.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
        print(f"SAVED: {len(df_existing)} recipes")
        
    exit(1)





