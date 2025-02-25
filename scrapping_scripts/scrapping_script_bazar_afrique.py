from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_categories(base_url):
    """
    Récupère toutes les catégories et leurs URLs depuis la page des catégories.
    """
    url = f"{base_url}/search"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Erreur lors de l'accès à la page des catégories : {url}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    categories = []
    categories_list = soup.select("ul.accordion-body-list.fs-sm li a")
    # Récupérer toutes les catégories
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
        title = soup.select_one(
            "div.border-bottom.pt-2.pb-4.py-lg-4 h1.h3.mb-2.break-long-words"
        )
        title = title.get_text(strip=True) if title else "Non disponible"

        # Prix
        price = soup.select_one("div.border-bottom.pt-2.pb-4.py-lg-4 h2.h4.fw-normal")
        price = price.get_text(strip=True) if price else "Non disponible"

        # Lieu
        location = soup.select_one("div.border-bottom.pt-2.pb-4.py-lg-4 p.mb-2.pb-1.fs-sm.text-muted")
        location = location.get_text(strip=True) if location else "Non disponible"

        # Détails du produit
        description = soup.select_one("p.line-breaks.break-long-words.mb-0")
        description = description.get_text(strip=True).replace("\n", " ") if description else "Non disponible"

        # Date de publication
        publish = soup.select_one("li.mb-0.me-3.pe-3.border-end.text-muted span")
        publish = publish.get_text(strip=True) if publish else "Non disponible"

        # Nom du vendeur
        vendor_name = soup.select_one("div.ps-3.flex-grow-1 h5")
        vendor_name = vendor_name.get_text(strip=True) if vendor_name else "Non disponible"

        # Temps de présence
        vendor_presence = soup.select_one("div.ps-3.flex-grow-1 div.small.opacity-70.text-muted")
        vendor_presence = vendor_presence.get_text(strip=True) if vendor_presence else "Non disponible"

        # Nombre d'annonces
        vendor_anounces = soup.select_one("div.ps-3.flex-grow-1 div.small.text-primary")
        vendor_anounces = vendor_anounces.get_text(strip=True) if vendor_anounces else "Non disponible"

        # Lien du profil du vendeur
        vendor_profil_el = soup.select_one(
            "a.d-flex.align-items-center.border-bottom.pb-4.text-decoration-none."
            "mb-3.w-100.text-muted.link-chevron-right.mt-4.d-flex.d-lg-none"
        )
        vendor_profil = vendor_profil_el["href"] if vendor_profil_el else "Non disponible"

        # Liens vers l'image
        raw_images = soup.select("div.gallery-item.rounded.rounded-md-3 img")
        image_urls = [slide["src"] for slide in raw_images if slide.get("src")]

        return {
            "Titre": title,
            "Prix_normal": price,
            "Description": description,
            "Localisation_bien": location,
            "Lien_produit": product_url,
            "Liens_images": image_urls,
            "Catégorie": category_name,
            "Fournisseur_nom": vendor_name,
            "Fournisseur_nb_annonces": vendor_anounces,
            "Fournisseur_presence": vendor_presence,
            "Fournisseur_date_publication": publish,
            "Fournisseur_profil": vendor_profil,
        }

    except AttributeError as e:
        print(f"Erreur lors de l'extraction des détails du produit {product_url} : {e}")
        return None


def scrape_products_from_category(category, base_url):
    """
    Récupère les détails de tous les produits d'une catégorie donnée en visitant leur page respective.
    """
    category_name = category["Nom"]
    category_url = category["URL"]
    all_products = []

    print(f"Scraping page : {category_url}")
    response = requests.get(category_url)
    if response.status_code != 200:
        print(f"Erreur lors de l'accès à la page de la catégorie '{category_name}' : {category_url}")

    soup = BeautifulSoup(response.content, "html.parser")

    # Sélectionner tous les liens produits (ici, un set() de balises <a>)
    all_product_tags = soup.select("div.position-relative.overflow-hidden.card-img-top.post-box-horizontal-image-container a")
    if not all_product_tags:
        print(f"Aucune page produit trouvée pour la catégorie : {category_name}")
        return []

    # Lire tous les liens déjà connus dans urls_file.txt (pour filtrer)
    with open("urls_file.txt", "r", encoding="utf-8") as urls_file:
        previous_links = set(line.strip() for line in urls_file if "bazarafrique" in line)

    # Construction des URL complètes pour la page actuelle
    current_links = set(f"{base_url}{tag['href']}" for tag in all_product_tags)

    # Filtrage : prendre les liens qui ne sont pas déjà connus
    new_links = current_links.difference(previous_links)
    if not new_links:
        print(f"Aucun nouveau produit à scraper pour la catégorie : {category_name}")
        return []

    print(f"{len(new_links)} nouveau(x) lien(s) détecté(s) pour la catégorie {category_name}")

    # Paralléliser le scraping des produits
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(scrape_product_details, link, category_name) for link in new_links]
        for future in as_completed(futures):
            product_details = future.result()
            if product_details:
                all_products.append(product_details)

    # Mettre à jour le fichier urls_file.txt avec les nouveaux liens
    with open("./urls_file.txt", "a", encoding="utf-8") as urls_file:
        for link in new_links:
            urls_file.write(link + "\n")

    return all_products


def main_bazar_afrique(base_url):
    """
    Scrape tous les produits de toutes les catégories et les associe aux catégories.
    """
    # Créer le dossier de sortie s'il n'existe pas
    output_dir = "Produits_bazar_afrique"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    categories = get_categories(base_url)
    if not categories:
        print("Aucune catégorie trouvée.")
        return pd.DataFrame()

    # Parcourir chaque catégorie
    for category in categories:
        print(f"Scraping produits de la catégorie : {category['Nom']}")
        category_file = os.path.join(output_dir, f"{category['Nom']}.jsonl")

        # Vérifier si le fichier de la catégorie existe déjà
        if os.path.isfile(category_file):
            print(f"La catégorie {category['Nom']} a déjà été scrappée. Elle sera donc ignorée.")
            continue

        # Sinon, scrap et sauvegarde
        products = scrape_products_from_category(category, base_url)
        print(f"Nombre de produits scrapés : {len(products)} pour la catégorie {category['Nom']}")

        if products:
            with open(category_file, "w", encoding="utf-8") as f:
                for product in products:
                    json_line = json.dumps(product, ensure_ascii=False)
                    f.write(json_line + "\n")
        # Delete the intermediaries files 
        if os.path.exists(output_dir):
                os.removedirs(output_dir)
    # Une fois toutes les catégories traitées, on relit tous les fichiers JSONL
    data = []
    for category in categories:
        category_file = os.path.join(output_dir, f"{category['Nom']}.jsonl")
        if os.path.isfile(category_file):
            with open(category_file, "r", encoding="utf-8") as f:
                for line in f:
                    data.append(json.loads(line))

    # Crée et retourne un DataFrame (qu’on peut ensuite sauvegarder en CSV si besoin)
    df = pd.DataFrame(data)
    return df