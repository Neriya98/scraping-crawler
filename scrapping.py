# Import the packages
import os
import time
import pandas as pd
import datetime as dt
from scrapping_scripts.scrapping_script_mtn import main_mtn
from scrapping_scripts.scrapping_script_iliko import main_iliko
from scrapping_scripts.scrapping_script_carisowo import main_carisowo
from scrapping_scripts.scrapping_script_tout_vendu import main_tout_vendu
from scrapping_scripts.scrapping_script_coin_afrique import main_coin_afrique
from scrapping_scripts.scrapping_script_bazar_afrique import main_bazar_afrique

SITES_LIST = ["http://carisowo.com", "https://shop.mtn.bj", "https://www.toutvendu.bj",\
              "https://www.iliko.bj", "https://bj.coinafrique.com", "https://bj.bazarafrique.com"]

# Definition of the crawler
class Crawler:
    """
    A web crawler that scrapes websites for data and logs its operations. 
    It maintains:
      - a log file recording important events and actions,
      - a file for storing all URLs encountered or processed,
      - and a CSV file containing consolidated scraped data.
    """
    
    # function to initialize the crawler
    def __init__(self):
        """
        Initialize the crawler by creating (or overwriting) the necessary log and URL files.
        This method also writes the crawler creation timestamp to the log file.
        """
        # Define the date at which the crawler is initialized
        built_date = str(dt.datetime.today())[:-7]
        # Create the log file to store information about the operation executed
        with open("./files/log_file.txt", "w", encoding="utf-8") as log_file:
            log_file.write(f"Crawler created at {built_date}\n\n")
        # The file to store the urls we'll scrap
        with open ("./files/urls_file.txt", "w", encoding="utf-8") as url_file:
            url_file.write(f"Urls file created at {built_date}\n\n")

    # function to reset the state of the crawler
    def reset(self) -> None:
        """
        Resets the crawler's state, allowing it to perform fresh scrapes.
        
        This method:
          - Removes existing log, scraped data, and URL files if they exist.
          - Creates a new log file indicating the reset time.
        Returns:
            None
        """
        # Log the reset event
        reset_date = str(dt.datetime.today())[:-7]
        
        for path in ["./files/log_file.txt", "./files/scraped_data.csv", "./files/urls_file.txt"]:
            if os.path.exists(path):
                os.remove(path)
        
        # Indicate that the file has been reset
        with open("./files/log_file.txt", "w", encoding="utf-8") as file:
            file.write(f"The crawler has been reset and created on {reset_date}\n")
        
        with open("./files/urls_file.txt", "w", encoding="utf-8") as uf:
            uf.write(f"The url file has been reset and created on {reset_date}\n")
        
        # Return the reset crawler instance
        print("Crawler has been reset. Reinitializing the crawler...")
        return None #Crawler()  # Reinstantiate the object
    
    # function to save the data
    def save_data(self, new_scraped:pd.DataFrame, existing_data = pd.DataFrame({})) -> None:
        """
        Saves newly scraped data to a CSV file and updates relevant logs and URL files.
        
        This method:
          - Concatenates new scraped data (`new_scraped`) with existing data (`existing_data`) if provided.
          - Saves the combined dataset to 'scraped_data.csv'.
          - Appends newly scraped URLs to 'urls_file.txt'.
          - Logs the number of new links scraped and the date/time of the scrape.
        
        Args:
            new_scraped (pd.DataFrame): A DataFrame containing newly scraped data.
            existing_data (pd.DataFrame, optional): A DataFrame with existing data to combine. 
                                                   Defaults to an empty DataFrame.
        
        Returns:
            None
        """
        
        # Add the new scraped data to the old scraped data
        if len(existing_data) == 0:
            df = new_scraped
        else:
            df = pd.concat([existing_data, new_scraped])
        
        # Save the new data base
        df.to_csv("./files/scraped_data.csv")
        # Modify the urls file to add the new urls scraped
        with open ("./files/urls_file.txt", "a", encoding="utf-8") as url_file:
            url_file.writelines(new_scraped["Lien_produit"].astype(str) + "\n")
        # Modify the log_file to add the historic of actions
        with open("./files/log_file.txt", "a") as log_file:
            log_file.write(f"{new_scraped['Lien_produit'].count()} new links scraped\n")
        
        return None
    
    # Function to scrap the data
    def scrap(self, site_urls = SITES_LIST) -> None:
        """
        Scrapes data from a list of website URLs.
        
        This method:
          - Logs the start time of the scraping process.
          - Iterates through each URL in the `site_urls` list and calls the 
            appropriate site-specific scraping function.
          - Collects and concatenates all the scraped data into a single DataFrame.
          - Appends a "Scrap date" column to the final DataFrame.
          - Calls `save_data` to save the combined DataFrame.
          - Logs the outcome of the scraping process, including any errors or empty results.
        
        Args:
            site_urls (list): A list of website URLs to be scraped.
        
        Returns:
            None
        """
        day_date = dt.datetime.today()
        with open("./files/log_file.txt", "a") as log_file:
            log_file.write(f"[Scrap] {day_date.strftime("%Y-%m-%d")} Doing scrapping for {site_urls}\n")
            log_file.write(f"Scrapping lunched at {day_date.strftime("%H:%M")}\n")

        data_collected = []  # Will store individual DataFrames from each site
        # The time the scraping started
        start = time.time()
        for url in site_urls:
            if "carisowo" in url:
                df = main_carisowo(url)
            elif "mtn" in url:
                df = main_mtn(url)
            elif "toutvendu" in url:
                df = main_tout_vendu(url)
            elif "iliko" in url:
                df = main_iliko(url)
            elif "coinafrique" in url:
                df = main_coin_afrique(url)
            elif "bazarafrique" in url:
                df = main_bazar_afrique(url)
            else:
                # If none of the conditions match, skip
                print(f"Skipping unknown site: {url}")
                continue
            
            # It's possible that your scraping function returns None or an empty DataFrame;
            # if you want to skip those, you can do:
            if df is not None and not df.empty:
                data_collected.append(df)
        # Write in the log file when the scrapping is finished
        with open("./files/log_file.txt", "a", encoding='utf-8') as lf:
            lf.write(f"[Scrap] Scrapping finished in {(time.time() - start)/3600:.4f} hours\n")
        # If no data was collected at all, we can handle that case
        if not data_collected:
            print("No data was collected from the provided URLs.")
            with open("./files/log_file.txt", "a") as log_file:
                log_file.write(f"No data was collected from the provided URLs.\n")
            return

        # Concatenate all DataFrames in data_collected
        final_data = pd.concat(data_collected, ignore_index=True)
        
        # Add a "Scrap date" column
        final_data["Scrap date"] = dt.date.today().strftime("%Y-%m-%d")

        # Conclude the scraping by saving the data
        self.save_data(final_data)

# Run the scraper 
crawler = Crawler()
crawler.scrap(["https://shop.mtn.bj"])  # Run the scraper
