import os
import json
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

def parse_single_product(product):
    """
    Extrait les informations d'un produit à partir de l'objet 'product' (balise HTML).
    """
    try:
        # URL du produit
        product_url = product.select_one("a.product-card.shawdow-card.h-100")["href"]
        # Titre du produit
        title = product.select_one("div.product-card-details h3").get_text(strip=True)
        # Disponibilité du produit
        availability = product.select_one("div.alert.alert-danger.text-center.font-14.out-of-stock")
        availability_text = availability.get_text(strip=True) if availability else "NA"
        # Prix normal
        price_normal = product.select_one("div.product-card-pricing span.woocommerce-Price-amount").get_text(strip=True)
        # Prix réduit
        price_discounted = product.select_one("div.product-promo-price span.woocommerce-Price-amount")
        price_discounted = price_discounted.get_text(strip=True) if price_discounted else price_normal
        # Taux de réduction
        discount = product.select_one("div.product-promotion-percentage")
        discount = discount.get_text(strip=True) if discount else "0%"
        # Catégorie
        category = product.select_one("div.product-card-header-cat span").get_text(strip=True)
        # Fournisseur
        vendor = product.select_one("div.product-card-footer span:nth-of-type(2)").get_text(strip=True)
        # URL image
        image_url = product.select_one("div.product-card-header-image img")["src"]

        # Construire le dictionnaire des détails du produit
        product_details = {
            "Titre": title,
            "Prix_normal": price_normal,
            "Prix_barré": price_discounted,
            "Réduction_proposée": discount,
            "Lien_produit": product_url,
            "Liens_images": image_url,
            "Catégorie": category,
            "Disponibilité": availability_text,
            "Fournisseur_profil": vendor,
        }
        return product_details

    except AttributeError as e:
        # En cas de champ manquant ou autre erreur de parsing
        product_title = product.select_one("div.product-card-details h3")
        product_title = product_title.get_text(strip=True) if product_title else "Inconnu"
        print(f"Erreur lors de l'extraction des détails du produit '{product_title}' : {e}")
        return None


def scrape_product_details(base_url):
    """
    Récupère les détails des produits listés sur la page de base (base_url).
    Parallélise le parsing des produits individuels.
    """
    response = requests.get(base_url)
    if response.status_code != 200:
        print(f"Erreur lors de l'accès à la page : {base_url}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")

    # Récupérer tous les produits
    products = soup.select("div.product-card-container.product-item-card.col-lg-3.col-6:not(.highlighted-products)")

    if not products:
        print("Aucun produit trouvé sur cette page.")
        return []

    # Lire les anciens liens du fichier urls_file.txt
    with open("./files/urls_file.txt", "r", encoding="utf-8") as urls_file:
        previous_links = set(line.strip() for line in urls_file if "mtn" in line)

    # Filtrer les produits dont le lien a déjà été scrappé
    filtered_products = []
    for product in products:
        product_tag = product.select_one("a.product-card.shawdow-card.h-100")
        if product_tag:
            product_url = product_tag.get("href")
            if product_url not in previous_links:
                filtered_products.append(product)

    if not filtered_products:
        print("Aucun nouveau produit à scraper sur cette page.")
        return []

    all_products = []

    # Paralléliser le parsing de chaque produit
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(parse_single_product, prod) for prod in filtered_products]
        for future in as_completed(futures):
            product_data = future.result()
            if product_data:
                all_products.append(product_data)

    # Mettre à jour urls_file.txt pour ne pas re-scraper les mêmes produits
    with open("./files/urls_file.txt", "a", encoding="utf-8") as uf:
        for product in filtered_products:
            url_ = product.select_one("a.product-card.shawdow-card.h-100")["href"]
            uf.write(url_ + "\n")

    return all_products


def main_mtn(base_url):
    """
    Scrape tous les produits listés sur la page et renvoie un DataFrame.
    """
    all_products = scrape_product_details(base_url)
    if not all_products:
        print("Aucun produit n'a été trouvé ou tous sont déjà scrappés.")
        return pd.DataFrame()

    df = pd.DataFrame(all_products)
    return df
