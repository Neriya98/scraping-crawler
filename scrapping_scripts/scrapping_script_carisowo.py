# Version 1.3

from bs4 import BeautifulSoup
import requests
import numpy as np
import pandas as pd
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_categories(base_url):
    """
    Récupère toutes les catégories et leurs URLs depuis la page des catégories.
    """
    url = base_url
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Erreur lors de l'accès à la page des catégories : {url}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    categories = []
    # Adaptation : On récupère ici les catégories de la même manière que dans votre code initial
    categories_list = [soup.select_one(f"div.col-12.col-sm-6.flex-md-align ul:nth-of-type(2) li:nth-of-type({i}) a") for i in range(2, 5)]

    for category in categories_list:
        try:
            category_url = f"{base_url}{category['href']}"  # URL de la catégorie
            category_name = category.get_text(strip=True)  # Nom de la catégorie
            categories.append({"Nom": category_name, "URL": category_url})
        except (AttributeError, IndexError) as e:
            print(f"Erreur lors de l'extraction d'une catégorie : {e}")
            continue
    return categories

def scrape_product_details(product_url, product_location, product_title, category_name):
    """
    Récupère les détails d'un produit en visitant sa page.
    """
    response = requests.get(product_url)
    if response.status_code != 200:
        print(f"Erreur lors de l'accès au produit : {product_url}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    try:
        # Prix
        price_el = soup.select_one("div.ad-price span.price-wrap span")
        price = price_el.get_text(strip=True) if price_el else "Non disponible"
        price = price + " CFA" if price != "Non disponible" else price

        # Détails du produit
        description_el = soup.select_one("div.ad-seller-comment div.comment-wrapper p")
        description = description_el.get_text(separator=', ', strip=True) if description_el else "Non disponible"

        # Date de publication
        publish_el = soup.select_one("div.ad-info-wrapper div.responsive-wrapper:nth-of-type(2) div.ad-info-block div.ad-created-border span:nth-of-type(2) strong")
        publish = publish_el.get_text(strip=True) if publish_el else "Non disponible"

        # Nombre de vues
        views_el = soup.select_one("div.ad-info-wrapper div:nth-of-type(2) div:nth-of-type(2) div span:nth-of-type(2)")
        views = views_el.get_text(strip=True) if views_el else "Non disponible"

        # Contact du vendeur
        vendor_phones_raw = soup.select("div.ad-about div.seller-phones div.phone-wrapper span")
        vendor_phones = []
        for phone in vendor_phones_raw:
            vendor_phone = phone.get_text(strip=True).replace(" ", "")
            vendor_phones.append(vendor_phone)

        # Caractéristiques
        properties = soup.select("div.vehicle-properties div.prop")
        car_details = []
        for prop in properties:
            prop_name_el = prop.select_one("div > span:nth-of-type(1)")
            prop_value_el = prop.select_one("div > span:nth-of-type(2)")
            prop_name = prop_name_el.get_text(strip=True) if prop_name_el else "Non disponible"
            prop_value = prop_value_el.get_text(strip=True) if prop_value_el else "Non disponible"
            car_details.append([prop_name, prop_value])

        return {
            "Titre": product_title,
            "Prix_normal": price,
            "Description": description,
            "Localisation_bien": product_location,
            "Lien_produit": product_url,
            "Lien_images": np.nan,
            "Catégorie": category_name,
            "Fournisseur_nom": np.nan,
            "Fournisseur_nb_annonces":np.nan,
            "Fournisseur_presence":np.nan,
            "Fournisseur_date_publication": publish,
            "Fournisseur_profil":np.nan,
            "Fournisseur_numeros_tel": vendor_phones,
            "Voiture_caracteristiques": car_details,
            "Vues": views,
        }
    except AttributeError as e:
        print(f"Erreur lors de l'extraction des détails du produit {product_url} : {e}")
        return None

def scrape_products_from_category(category, base_url):
    """
    Récupère les détails de tous les produits d'une catégorie donnée.
    On itère sur plusieurs pages, et on arrête dès qu'une page n'a plus de produits.
    """
    category_name = category["Nom"]
    category_url = f"{category['URL']}.html"
    all_products = []

    for page in range(1, 1000):  
        url = f"{category_url}?page={page}" if page > 1 else category_url
        print(f"Scraping page : {url}")
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Erreur lors de l'accès à la page {page} de la catégorie '{category_name}' : {url}")
            break

        soup = BeautifulSoup(response.content, "html.parser")
        annonces = soup.find_all("a", class_="common-ad-card")

        if not annonces:
            print(f"Aucun produit trouvé sur la page {page}. Fin du scraping pour cette catégorie.")
            break

        # Extraire les données de la page en parallèle
        product_args = []
        # Exclure les urls qui sont déjà scrappés
        with open ("./files/urls_file.txt", "r", encoding="utf-8") as urls_file:
            previous_links = list(set([line.strip() for line in urls_file.readlines() if "carisowo" in line]))

        # Take the announces that contain the links differents from the ones that have been scrapped
        annonces_filtered = [annonce for annonce in annonces if f"{base_url}{annonce.get('href')}" not in previous_links]
        # Assign the filtered announces to announces
        annonces = annonces_filtered
        # Iterate through announces to get the product proprieties
        for annonce in annonces:
            product_url = f"{base_url}{annonce.get('href')}"
            product_title = annonce.find("h4").get("title") if annonce.find("h4") else "Non disponible"
            product_location = annonce.find("div", class_="location").get_text(strip=True) if annonce.find("div", class_="location") else "Non disponible"
            product_args.append([product_url, product_location, product_title, category_name])

        # Paralléliser le scraping des produits
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(scrape_product_details, p_url, p_loc, p_title, c_name)
                       for p_url, p_loc, p_title, c_name in product_args]

            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_products.append(result)
        # Mise à jour du fichier urls_file.txt pour les nouveaux liens scrappés
        product_urls = [product[0] for product in product_args]
        with open("./files/urls_file.txt", "a", encoding="utf-8") as uf:
            for link in product_urls:
                uf.write(link + "\n")

    return all_products

def main_carisowo(base_url):
    output_dir = "Produits_carisowo"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    categories = get_categories(base_url)
    if not categories:
        print("Aucune catégorie trouvée.")
        return

    for category in categories:
        category_file = f"Produits_carisowo/{category['Nom']}.jsonl"
        # Vérification si la catégorie a déjà été scrappée
        if os.path.isfile(category_file):
            print(f"La catégorie {category['Nom']} a été déjà scrappée. Elle sera donc ignorée.")
            continue

        print(f"Scraping produits de la catégorie : {category['Nom']}")
        products = scrape_products_from_category(category, base_url)
        print(f"Nombre de produits scrapés pour la catégorie {category['Nom']} : {len(products)}")

        # Sauvegarde en JSONL
        with open(category_file, "w", encoding="utf-8") as f:
            for product in products:
                json_line = json.dumps(product, ensure_ascii=False)
                f.write(json_line + "\n")
    
    if os.path.exists(output_dir):
                os.removedirs(output_dir)
    # Une fois toutes les catégories traitées, on relit tous les fichiers JSONL
    data = []
    category_files = [f for f in os.listdir("Produits_carisowo") if f.endswith(".jsonl")]
    for cf in category_files:
        file_path = os.path.join("Produits_carisowo", cf)
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                data.append(json.loads(line))

    df = pd.DataFrame(data)
    return df