# version 1.4

from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_categories(base_url:str):
    """
    Récupère toutes les catégories et leurs URLs depuis la page des catégories.

    parameters : 
        - base_url (str): url racine du site
    return :
        - categories (dict) : dictionnaire contenant les categories.
    """
    response = requests.get(base_url)
    if response.status_code != 200:
        print(f"Erreur lors de l'accès à la page des catégories : {base_url}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    categories = []

    categories_list = soup.select("li.category.gtm-category-bar.center a")
    # Si nécessaire, supprimer le premier élément
    if categories_list:
        categories_list.pop(0)
    for category in categories_list:
        try:
            category_url = f"{base_url}{category['href']}"  # URL de la catégorie
            category_name = category.get_text(strip=True)  # Nom de la catégorie
            categories.append({"Nom": category_name, "URL": category_url})
        except (AttributeError, IndexError) as e:
            print(f"Erreur lors de l'extraction d'une catégorie : {e}")
            continue
    return categories

def scrape_product_details(product_url, category_name):
    """
    Récupère les détails d'un produit en visitant sa page.
    """
    response = requests.get(product_url)
    if response.status_code != 200:
        print(f"Erreur lors de l'accès au produit : {product_url}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    try:
        # Titre du produit
        title = soup.select_one("div.ad__info__box.ad__info__box-priceAndTitle h1.title.title-ad.hide-on-large-and-down")
        title = title.get_text(strip=True) if title else "Non disponible"

        # Prix
        price = soup.select_one("div.ad__info__box.ad__info__box-priceAndTitle p.price")
        price = price.get_text(strip=True) if price else "Non disponible"

        # Lieu
        location = soup.select_one("p.extras span.valign-wrapper:nth-of-type(2) span")
        location = location.get_text(strip=True) if location else "Non disponible"

        # Description
        description = soup.select_one("div.ad__info__box.ad__info__box-descriptions p:nth-of-type(2)")
        description = description.get_text(strip=True).replace("*", "").replace("\n", " ") if description else "Non disponible"

        # Nom du vendeur
        vendor_name = soup.select_one("div.profile-card__content p.username a")
        vendor_name = vendor_name.get_text(strip=True) if vendor_name else "Non disponible"

        # Localisation du vendeur
        vendor_location = soup.select_one("div.profile-card__content p.physical-address span.physical-address__name")
        vendor_location = vendor_location.get_text(strip=True) if vendor_location else "Non disponible"

        # Nombre d'annonces du vendeur
        vendor_anounces = soup.select_one("div.profile-card__content p.nb-ads")
        vendor_anounces = vendor_anounces.get_text(strip=True) if vendor_anounces else "Non disponible"

        # Temps de présence du vendeur
        vendor_presence_raw = soup.select_one("div.profile-card__content p.member-since span")
        vendor_presence_raw = vendor_presence_raw.get_text(strip=True) if vendor_presence_raw else "Non disponible"
        vendor_presence = vendor_presence_raw.split("\xa0")[-1].strip() if vendor_presence_raw != "Non disponible" else "Non disponible"

        # Caractéristiques du produit
        characteristics = soup.select("div.details-characteristics ul li")
        details = []
        for charac in characteristics:
            name = charac.select_one("span.label") or charac.select_one("span:not(.qt)")
            value = charac.select_one("span.qt")
            if name and value:
                details.append((name.get_text(strip=True), value.get_text(strip=True)))
        details = list(set(details))

        # Images
        slides = soup.select("div.swiper-slide")
        image_urls = [
            slide.get("style", "").split("url(")[1].split(")")[0].strip("'\"")
            for slide in slides if "background-image" in slide.get("style", "") and "thumb" not in slide.get("style", "")
        ]

        return {
            "Titre": title,
            "Prix_normal": price,
            "Description": description,
            "Localisation_bien": location,
            "Lien_produit": product_url,
            "Liens_images": image_urls,
            "Catégorie": category_name,
            "Caractéristiques": details,
            "Fournisseur_nom": vendor_name,
            "Fournisseur_emplacement": vendor_location,
            "Fournisseur_nb_annonces": vendor_anounces,
            "Fournisseur_presence": vendor_presence
        }

    except AttributeError as e:
        print(f"Erreur lors de l'extraction des détails du produit {product_url} : {e}")
        return None

def scrape_products_from_category(category, base_url):
    """
    Récupère les détails de tous les produits d'une catégorie donnée en itérant sur les pages.
    S'arrête lorsque une page n'a plus de produits.
    """
    category_name = category["Nom"]
    category_url = category["URL"]
    all_products = []

    for page in range(1, 1000):  # Ajustez la limite si nécessaire
        if page == 1:
            url = category_url
        else:
            url = f"{category_url}?page={page}"
        print(f"Scraping page : {url}")
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Erreur lors de l'accès à la page {page} de la catégorie '{category_name}' : {url}")
            break

        soup = BeautifulSoup(response.content, "html.parser")

        # Vérifier si la page est vide
        product_links = soup.select("a.card-image.ad__card-image.waves-block.waves-light")

        if not product_links:
            print(f"Aucun produit trouvé sur la page {page}. Fin du scraping pour cette catégorie.")
            break
        
        # Paralléliser le scrap des produits de cette page
        product_urls = [f"{base_url}{link['href']}" for link in product_links]

        # Filter the links that are not in the urls_file
        with open ("./urls_file.txt", "r", encoding="utf-8") as urls_file:
            previous_links = list(set([line.strip() for line in urls_file.readlines() if "coinafrique" in line]))
        product_urls = [product_url for product_url in product_urls if product_url not in previous_links]
        
        # On lance plusieurs threads pour récupérer les détails des produits
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(scrape_product_details, p_url, category_name) for p_url in product_urls]
            for future in as_completed(futures):
                product_details = future.result()
                if product_details:
                    all_products.append(product_details)
        
        # Mise à jour du fichier urls_file.txt pour les nouveaux liens scrappés
        with open("./urls_file.txt", "a", encoding="utf-8") as uf:
            for link in product_urls:
                uf.write(link + "\n")
    return all_products

def main_coin_afrique(base_url):
    output_dir = "Produits_coin_afrique"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    categories = get_categories(base_url)
    if not categories:
        print("Aucune catégorie trouvée.")
        return


    for category in categories:
        category_file = f"Produits_coin_afrique/{category['Nom']}.jsonl"
        if os.path.exists(category_file):
            print(f"La catégorie '{category['Nom']}' a déjà été scrappée. Elle sera donc ignorée.")
            continue
        else:
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
    # Une fois toutes les catégories traitées, fusionner tous les fichiers JSONL en un seul DataFrame
    data = []
    category_files = [f for f in os.listdir("Produits_coin_afrique") if f.endswith(".jsonl")]

    for cf in category_files:
        file_path = os.path.join("Produits_coin_afrique/", cf)
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line.strip())
                data.append(record)

    df = pd.DataFrame(data)
    return df