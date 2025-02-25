import os
import math
import time
import pandas as pd
import datetime as dt
from scrapping import Crawler
from flask_apscheduler import APScheduler
from flask import Flask, render_template, request, redirect, url_for

# Mapping site names to their URLs
SITES_DICT = {
    "Carisowo": "http://carisowo.com",
    "MTN": "https://shop.mtn.bj",
    "Toutvendu": "https://www.toutvendu.bj",
    "Iliko": "https://www.iliko.bj",
    "Coinafrique": "https://bj.coinafrique.com",
    "Bazarafrique": "https://bj.bazarafrique.com"
}

# APScheduler configuration
class Config:
    SCHEDULER_API_ENABLED = True

app = Flask(__name__)
app.config.from_object(Config())

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Create a global crawler instance
crawler = Crawler()

# We'll store the user-chosen sites for scheduled scraping in this global list
scheduled_sites = []

def scheduled_scrape_job():
    """
    Called automatically by APScheduler at the specified daily time,
    scraping the sites in 'scheduled_sites'.
    """
    if not scheduled_sites:
        print("[Scheduler] No sites selected for automated scraping.")
        return
    site_urls = [SITES_DICT[s] for s in scheduled_sites if s in SITES_DICT]
    if site_urls:
        print(f"[Scheduler] Automatically scraping: {site_urls}")
        crawler.scrap(site_urls)

@app.route('/')
def home():
    """
    Renders a single-page dashboard (index.html).
    """
    return render_template('index.html', sites=SITES_DICT.keys())

@app.route('/reset', methods=['POST'])
def reset_crawler():
    """
    Resets the crawler's data/logs.
    """
    crawler.reset()
    return redirect(url_for('home'))

@app.route('/scrap', methods=['POST'])
def scrap():
    """
    Handles the user's form submission:
      - If user picks "Yes" and provides a time -> schedule daily scraping + optional immediate scrape.
      - If user picks "No" -> do an immediate, one-time scrape.
    """
    global scheduled_sites

    # Collect selected sites
    selected_sites = request.form.getlist('sites')  # e.g. ["MTN", "Carisowo"]
    site_urls = [SITES_DICT[s] for s in selected_sites if s in SITES_DICT]

    # Radio: "automate" can be "yes" or "no"
    automate_choice = request.form.get('automate_radio')  # "yes" or "no"
    schedule_time_str = request.form.get('schedule_time', '')  # e.g. "14:30"

    print("=== DEBUG: scrap route ===")
    print("Selected sites:", selected_sites)
    print("Automate choice:", automate_choice)
    print("Schedule time:", schedule_time_str)

    if automate_choice == "yes" and schedule_time_str:
        # User wants daily scheduled scraping at the provided time
        scheduled_sites = selected_sites

        # Remove any old job to avoid duplicates
        try:
            scheduler.remove_job('scheduled_scrape')
        except:
            pass

        # Parse HH:MM
        hour_str, minute_str = schedule_time_str.split(':')
        hour = int(hour_str)
        minute = int(minute_str)

        # Schedule a daily cron job
        scheduler.add_job(
            id='scheduled_scrape',
            func=scheduled_scrape_job,
            trigger='cron',
            hour=hour,
            minute=minute
        )
        print(f"[Scheduler] Daily job scheduled at {hour:02}:{minute:02} for {selected_sites}")
        # Write the action into the log file
        with open("log_file.txt", "a", encoding="utf-8") as lf:
            lf.write(f"[Scheduler] Daily job scheduled at {hour:02}:{minute:02} for {selected_sites}\n")
        # Optional: also do an immediate scrape once
        if site_urls:
            print("[Scheduler] Doing an immediate scrape too.")
            start = time.time()
            crawler.scrap(site_urls)
            with open("log_file.txt", "a", encoding="utf-8") as lf:
                lf.write(f"[Scrap] Operation finished in {(time.time() - start)/3600:.4f} hours\n")

    else:
        # automate_choice is "no" or no time provided => one-time scrape
        day_date = dt.datetime.today()
        if site_urls:
            print("[Scrap] Doing a one-time scrape for:", site_urls)
            # Write the starting of the operation
            with open("log_file.txt", "a", encoding="utf-8") as lf:
                lf.write(f"[Scrap] {day_date.strftime("%Y-%m-%d")} Doing a one-time scrape for: {site_urls}\n")
            start = time.time()
            crawler.scrap(site_urls)
            # Write the runtime of the operation
            with open("log_file.txt", "a", encoding="utf-8") as lf:
                lf.write(f"[Scrap] Operation finished in {(time.time() - start)/3600:.4f} hours\n")
    return redirect(url_for('home'))

@app.route('/view-data')
def view_data():
    """
    Shows paginated data from 'scraped_data.csv', if present.
    """
    file_path = "./scraped_data.csv"
    if not os.path.exists(file_path):
        return "<h1>No data found</h1><br><a href='/'>Back to Home</a>"

    df = pd.read_csv(file_path, index_col=0)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    total_rows = len(df)
    total_pages = math.ceil(total_rows / per_page)

    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    page_data = df.iloc[start_index:end_index]
    table_html = page_data.to_html(classes="table table-striped", index=False)

    return render_template(
        'view_data.html',
        table_html=table_html,
        current_page=page,
        total_pages=total_pages,
        per_page=per_page,
        total_rows=total_rows
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
