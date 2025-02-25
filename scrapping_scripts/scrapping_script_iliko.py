from bs4 import BeautifulSoup
import requests
import numpy as np
import pandas as pd
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_categories(base_url):
    """
    Récupère toutes les catégories et leurs URLs depuis la page des catégories.
    """
    url = f"{base_url}/categories"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Erreur lors de l'accès à la page des catégories : {url}")
        return []
    
    soup = BeautifulSoup(response.content, "html.parser")
    categories = []

    # Récupérer toutes les catégories
    for category in soup.select("div.card-header.mb-2.p-2.side-category-bar"):
        try:
            category_id = category.get("onclick").split("'")[1].split("/")[-1]  # ID de la catégorie
            category_url = f"{base_url}/products?id={category_id}&data_from=category"  # URL de la catégorie
            category_name = category.get_text(strip=True)  # Nom de la catégorie
            categories.append({"Nom": category_name, "URL": category_url})
        except (AttributeError, IndexError) as e:
            print(f"Erreur lors de l'extraction d'une catégorie : {e}")
            continue

    return categories


def scrape_product_details(product_url, category_name, base_url):
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
        title = soup.select_one("div.details span").get_text(strip=True)

        # Prix normal et prix barré
        price_normal_el = soup.select_one("div.details span.h3.font-weight-normal.text-accent")
        price_normal = price_normal_el.get_text(strip=True) if price_normal_el else "Non disponible"

        price_discounted_el = soup.select_one("div.details strike")
        price_discounted = price_discounted_el.get_text(strip=True) if price_discounted_el else None

        # État du bien
        condition_el = soup.select_one("span.gtm_ads_content_quality")
        condition = condition_el.get_text(strip=True) if condition_el else "Non spécifié"

        # Nombre d'étoiles
        star_el = soup.select_one("span.d-inline-block.align-middle.mt-1.mr-md-2.mr-sm-0.pr-2")
        star_rating = star_el.get_text(strip=True) if star_el else "Non disponible"

        # Nombre d'avis
        reviews_el = soup.select_one("span.font-for-tab.d-inline-block")
        reviews = reviews_el.get_text(strip=True).replace("Avis", "").strip() if reviews_el else "Non disponible"

        # Fournisseur
        vendor_el = soup.select_one("div.ml-3 > span[style*='font-weight: 700']")
        vendor = vendor_el.get_text(strip=True) if vendor_el else "Non disponible"

        # Lien vers l'image
        image_el = soup.select_one("div.details img")
        image_url = image_el["src"] if image_el else "Non disponible"

        return {
            "Titre": title,
            "Prix_normal": price_normal,
            "Lien_produit": product_url,
            "Prix_barré": price_discounted,
            "État": condition,
            "Évaluation (étoiles)": star_rating,
            "Nombre_avis": reviews,
            "Liens_images": image_url,
            "Catégorie": category_name,
            "Fournisseur_profil": vendor
        }
    except AttributeError as e:
        print(f"Erreur lors de l'extraction des détails du produit {product_url} : {e}")
        return None


def scrape_products_from_category(category, base_url):
    """
    Récupère les détails de tous les produits d'une catégorie donnée en visitant leur page respective,
    en parallélisant le scraping des détails produits.
    """
    category_name = category["Nom"]
    category_url = category["URL"]
    all_products = []

    # S'assurer que le fichier urls_file.txt existe (pour éviter les erreurs si on l'utilise)
    for page in range(1, 300):  # Ajustez la limite si nécessaire
        url = f"{category_url}&page={page}"
        print(f"Scraping page : {url}")
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Erreur lors de l'accès à la page {page} de la catégorie '{category_name}' : {url}")
            break

        soup = BeautifulSoup(response.content, "html.parser")

        # Vérifier si la page est vide
        product_links = soup.select("div.single-product-details div.text-left a")
        if not product_links:
            print(f"Aucun produit trouvé sur la page {page}. Fin du scraping pour cette catégorie.")
            break
        
        # Filtrer les liens déjà scrappés
        with open("./urls_file.txt", "r", encoding="utf-8") as urls_file:
            previous_links = set(line.strip() for line in urls_file if "iliko" in line)

        filtered_links = []
        for link in product_links:
            product_url = link.get("href", "")
            # Vérifier si déjà dans previous_links
            if product_url not in previous_links:
                filtered_links.append(link)

        # Si aucun nouveau lien n'est trouvé sur cette page, on peut sortir
        if not filtered_links:
            print(f"Aucun nouveau produit sur la page {page}. Fin du scraping pour cette catégorie.")
            break

        # Parallélisation du scraping des détails produits
        new_products = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(
                    scrape_product_details,
                    link["href"], 
                    category_name, 
                    base_url
                ): link["href"] for link in filtered_links
            }

            for future in as_completed(future_to_url):
                product_details = future.result()
                if product_details:
                    new_products.append(product_details)

        # Mise à jour du fichier urls_file.txt pour les nouveaux liens scrappés
        with open("./urls_file.txt", "a", encoding="utf-8") as uf:
            for link in filtered_links:
                uf.write(link["href"] + "\n")

        all_products.extend(new_products)

    return all_products


def main_iliko(base_url):
    """
    Scrape tous les produits de toutes les catégories et les associe aux catégories,
    puis retourne un DataFrame final.
    """
    categories = get_categories(base_url)
    if not categories:
        print("Aucune catégorie trouvée.")
        return pd.DataFrame()  # Renvoie un DataFrame vide si aucune catégorie

    all_products = []

    # Parcourir chaque catégorie
    for category in categories:
        print(f"Scraping produits de la catégorie : {category['Nom']}")
        products = scrape_products_from_category(category, base_url)
        all_products.extend(products)

    # Sauvegarder/convertir les données dans un DataFrame final
    df = pd.DataFrame(all_products)
    return df