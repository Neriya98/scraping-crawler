import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_categories(base_url):
    """
    Récupère toutes les catégories et leurs URLs depuis la page des catégories.
    """
    url = f"{base_url}/parcategorie"
    response = requests.get(base_url)
    # if response.status_code != 200:
    #     print(f"Erreur lors de l'accès à la page des catégories : {base_url}")
    #     return []
    
    soup = BeautifulSoup(response.content, "html.parser")
    categories = []

    # Récupérer toutes les catégories
    for i, category in enumerate(soup.select("ul.dropdown-menu.mega-dropdown-menu.row li.col-md-3 a"), start=1):
        try:
            category_url = f"{url}/{i}"  # URL de la catégorie
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
        title = soup.select_one("h4.product-name a").get_text(strip=True)

        # Prix normal (aucun prix barré mentionné dans votre HTML)
        price_normal = soup.select_one("b[style='color:blue']").get_text(strip=True)

        # Description du produit
        description = soup.select_one("p.product-desc").get_text(strip=True)

        # Catégorie
        category = soup.select_one("ul.list-unstyled.product_info.mtb_20 li:nth-of-type(1) span a").get_text(strip=True)

        # Code Produit
        product_code = (
            soup.select_one("ul.list-unstyled.product_info.mtb_20 li:nth-of-type(2) span")
            .get_text(strip=True)
            .replace("#produit ", "")
        )

        # Étiquette (ex. : "Stock limité")
        tag = soup.select_one("ul.product_info li:nth-of-type(3) span").get_text(strip=True)

        # Texte livraison
        shipping = soup.select_one("div.tab-pane.active.pt_20").get_text(strip=True)

        # Image produit
        image_el = soup.select_one("a.thumbnails img")
        image_url = image_el["src"] if image_el else "Non Disponible"

        return {
            "Titre": title,
            "Prix_normal": price_normal,
            "Description": description,
            "Code_produit": product_code,
            "Etiquette": tag,
            "Livraison": shipping,
            "Lien_produit": product_url,
            "Liens_images": image_url,
            "Catégorie": category,
        }

    except AttributeError as e:
        print(f"Erreur lors de l'extraction des détails du produit {product_url} : {e}")
        return None

def scrape_products_from_category(category, base_url):
    """
    Récupère les détails de tous les produits d'une catégorie donnée en visitant leur page respective.
    Parallélise le scraping des détails produits.
    """
    category_name = category["Nom"]
    category_url = category["URL"]
    all_products = []

    # S'assurer que le fichier urls_file.txt existe pour éviter les erreurs
    for page in range(1, 300):  # Ajustez la limite si nécessaire
        if page == 1:
            url = category_url
        else:
            url = f"{category_url}/{page}"
        
        print(f"Scraping page : {url}")
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Erreur lors de l'accès à la page {page} de la catégorie '{category_name}' : {url}")
            break

        soup = BeautifulSoup(response.content, "html.parser")

        # Vérifier si la page est vide
        products = soup.select("div.col-lg-2.col-md-3.col-xs-6 div.single-product")
        if not products:
            print(f"Aucun produit trouvé sur la page {page}. Fin du scraping pour cette catégorie.")
            break

        # Lecture des liens déjà scrappés
        with open("./urls_file.txt", "r", encoding="utf-8") as urls_file:
            previous_links = set(line.strip() for line in urls_file if "toutvendu" in line)

        # Filtrer les produits déjà scrappés
        filtered_products = []
        for product in products:
            link_el = product.select_one("a[href*='/details']")
            if link_el:
                full_url = f"{base_url}{link_el['href']}"
                if full_url not in previous_links:
                    filtered_products.append(product)

        if not filtered_products:
            print(f"Aucun nouveau produit sur la page {page} pour la catégorie '{category_name}'.")
            # Vous pouvez `break` pour arrêter de scraper cette catégorie ou continuer à la page suivante
            # break  # <-- Décommentez si vous souhaitez arrêter quand il n'y a plus de nouveaux produits

        # Paralléliser l'appel à scrape_product_details pour chacun des produits
        new_products = []
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            for product in filtered_products:
                link_el = product.select_one("a[href*='/details']")
                product_url = f"{base_url}{link_el['href']}"
                futures[executor.submit(scrape_product_details, product_url, category_name)] = product_url

            for future in as_completed(futures):
                product_url = futures[future]
                result = future.result()
                if result:
                    new_products.append(result)

        # Mise à jour du fichier urls_file.txt avec les nouveaux liens scrappés
        with open("./urls_file.txt", "a", encoding="utf-8") as uf:
            for product in filtered_products:
                link_el = product.select_one("a[href*='/details']")
                product_url = f"{base_url}{link_el['href']}"
                uf.write(product_url + "\n")

        all_products.extend(new_products)

    return all_products

def main_tout_vendu(base_url):
    """
    Scrape tous les produits de toutes les catégories et les associe aux catégories.
    """
    categories = get_categories(base_url)
    if not categories:
        print("Aucune catégorie trouvée.")
        return pd.DataFrame()

    all_products = []

    # Parcourir chaque catégorie
    for category in categories:
        print(f"Scraping produits de la catégorie : {category['Nom']}")
        products = scrape_products_from_category(category, base_url)
        all_products.extend(products)

    # Conversion finale en DataFrame
    df = pd.DataFrame(all_products)
    return df