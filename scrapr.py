import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from tqdm import tqdm
import sqlite3
import json

CARDS_API_URL = 'https://marvelsnapzone.com/getinfo/?searchtype=cards&searchcardstype=true'
LOCATIONS_API_URL = 'https://marvelsnapzone.com/getinfo/?searchtype=locations&searchcardstype=true'
ROOT_DIR = 'marvel-snap'
CARDS_DIR = 'cards'
VARIANTS_DIR = 'variants'
LOCATIONS_DIR = 'locations'


def get_cards(url: str = CARDS_API_URL):
    """
    Retrieves a list of cards from the Marvel SNAP Zone API.

    Returns:
        A list of cards, where each card is represented as a dictionary.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        json_data = response.json()
        success = json_data.get("success", {})
        return success.get("cards", [])
    except requests.exceptions.RequestException:
        print(f"Error: Request failed with status code {response.status_code}")


def download_images(urls, dir: str = ROOT_DIR):
    """
    Downloads images from the given URLs and stores them in the given directory.

    Args:
        urls: A list of URLs to download images from.
        dir: The directory to store the images in.
    """

    overall_progress = tqdm(total=len(urls), unit=' URL')

    def download_image(url, dir: str = ROOT_DIR):
        try:
            file_name = url.rsplit('/', 1)[-1].rsplit('?', 1)[0]
            file_path = os.path.join(dir, file_name)
            png_file_path = os.path.splitext(file_path)[0] + ".png"

            if os.path.exists(png_file_path):
                overall_progress.update(1)
                return

            temp_file_path = file_path + ".webp"
            with open(temp_file_path, 'wb') as file:
                response = requests.get(url, stream=True)
                response.raise_for_status()

                for data in response.iter_content(1024):
                    file.write(data)

            image = Image.open(temp_file_path)
            image.save(png_file_path, "PNG")
            overall_progress.update(1)

        except requests.exceptions.RequestException:
            overall_progress.update(1)

        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    with ThreadPoolExecutor(max_workers=5) as executor:
        for url in urls:
            executor.submit(download_image, url, dir)

    overall_progress.close()


def create_directories():
    """
    Creates the directories for the card images.

    ROOT_DIR
    ├── CARDS_DIR
    ├── LOCATIONS_DIR
    └── VARIANTS_DIR

    """
    if not os.path.exists(ROOT_DIR):
        os.mkdir(ROOT_DIR)

    directories = [CARDS_DIR, VARIANTS_DIR, LOCATIONS_DIR]

    for directory in directories:
        path = os.path.join(ROOT_DIR, directory)
        if not os.path.exists(path):
            os.mkdir(path)


if __name__ == '__main__':
    print("[%s] %s" %
          (datetime.now(), "Start downloading..."))
    cards = get_cards()
    card_image_urls = [card['art'] for card in cards]
    variant_image_urls = [variant['art']
                          for card in cards for variant in card.get('variants', [])]

    locations = get_cards(LOCATIONS_API_URL)
    location_image_urls = [location['art'] for location in locations]

    card_name = [card['name'] for card in cards]
    card_cost = [card['cost'] for card in cards]
    card_power = [card['power'] for card in cards]
    card_ability = [card['ability'] for card in cards]
    card_flavor = [card['flavor'] for card in cards]

    card_ability_pruned = []
    card_description = []
    card_dictionary = []

    for x in range(len(card_ability)):
        card_ability_pruned.append(card_ability[x].replace("<span>", "").replace("</span>", ""))

    for x in range(len(card_ability_pruned)):
        if card_ability_pruned[x] == '':
            card_description.append(card_flavor[x])
        else:
            card_description.append(card_ability_pruned[x])

    for x in range(len(card_name)):
        temp = [card_name[x],card_cost[x],card_power[x],card_description[x]]
        card_dictionary.append(temp)
    
    if os.path.isfile("./cards.json"):
        os.remove("./cards.json")

    column = ['name', 'cost', 'power', 'description']
    items = [dict(zip(column, row)) for row in card_dictionary]

    with open("cards.json", "w") as f:
        print(json.dumps(items), file=f)
    
    if os.path.isfile("./MarvelSnap.sqlite3"):
        os.remove("./MarvelSnap.sqlite3")

    con = sqlite3.connect("MarvelSnap.sqlite3")
    cur = con.cursor()

    with con:
        cur.execute("CREATE TABLE cards(name, cost, power, description)")
   
    with con:
        cur.executemany("INSERT INTO cards VALUES(?, ?, ?, ?)", card_dictionary)
    
    
    con.close()
    create_directories()

    #download_images(card_image_urls, os.path.join(ROOT_DIR, CARDS_DIR))
    #download_images(variant_image_urls, os.path.join(ROOT_DIR, VARIANTS_DIR))
    #download_images(location_image_urls, os.path.join(ROOT_DIR, LOCATIONS_DIR))

    print("[%s] %s" %
          (datetime.now(), f"Finished downloading. Check '{ROOT_DIR}' directory."))
