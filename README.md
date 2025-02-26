# **Automated Web Scraper – Private Repository**

## **📌 Project Overview**

This project is a custom web scraper designed to extract product data from multiple e-commerce websites. The scraper runs automatically every 72 hours using GitHub Actions, and saves the extracted data into the repository.  

## **⚙️ How it works**

### **1️⃣ Automated Execution via GitHub Actions**
The scraping script is scheduled to run **every 3 days at midnight UTC** using the following schedule:

- **Cron schedule:** `0 0 */3 * *` (every 72 hours)
- **Manual Execution:** Can be triggered from the GitHub Actions tab.

### **2️⃣ Data Storage in the Repository**
After each execution, the scraper updates the following files:

- `files/scraped_data.csv` → Extracted product data.
- `files/log_file.txt` → Logs the scraping process.
- `files/urls_file.txt` → URLs processed.

These files are **committed and pushed to the repository automatically**.

---

## **🛠️ Setup Instructions**

### **1️⃣ Clone the Repository**
```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

### **2️⃣ Install Dependencies**
Ensure Python 3.12 is installed. Then, install the required libraries. If using github, it will be done directly within the yml file:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### **3️⃣ Configure GitHub Actions**
To enable automatic execution, set up a **GitHub Personal Access Token (PAT)**:

1. **Go to:** GitHub → Settings → Developer Settings → Personal Access Tokens.
2. **Generate a new token (classic)** with:
   - **repo** (Full control of private repositories)
   - **workflow** (Trigger GitHub Actions workflows)
3. **Copy the token** and go to the repository:
   - Settings → Secrets and variables → Actions → **New repository secret**.
   - Name it **GH_PAT** and paste the token.

### **4️⃣ Run the Scraper Manually**
To trigger the scraper manually:
- Go to **GitHub Repository → Actions → Run Scraper → Run Workflow**.
- Or, run:
```bash
gh workflow run run_scraper.yml
```

---

## **🚀 Automation Workflow (GitHub Actions)**

The scraper runs automatically through **GitHub Actions** using this workflow:

```yaml
name: Run Scraper

on:
  schedule:
    - cron: "0 0 */3 * *"  # Runs every 3 days (72 hours)
  workflow_dispatch:  # Allows manual trigger

jobs:
  run_scraper:
    runs-on: ubuntu-latest

    steps:
      - name: Check out repository
        uses: actions/checkout@v3
        with:
          persist-credentials: false  # Prevents default GitHub token usage

      - name: Set up Python
        uses: actions/setup-python@v3
        with:
          python-version: 3.12  

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt  

      - name: Run Scraper
        run: python3 scrapping.py

      - name: Commit and Push Changes
        run: |
          git config --global user.email "github-actions@github.com"
          git config --global user.name "GitHub Actions"
          git add files/scraped_data.csv files/log_file.txt files/urls_file.txt
          git commit -m "Update scraped data [$(date)]" || echo "No changes to commit"
          git push https://x-access-token:${{ secrets.GH_PAT }}@github.com/YOUR-USERNAME/YOUR-REPOSITORY.git main
        env:
          GH_PAT: ${{ secrets.GH_PAT }}
```

---

## **📂 Project Structure**

| File/Directory         | Description |
|------------------------|-------------|
| `scrapping.py`        | Main script that scrapes product data. |
| `requirements.txt`    | List of dependencies. |
| `files/scraped_data.csv` | Stores extracted product information. |
| `files/log_file.txt`  | Logs the scraping process. |
| `files/urls_file.txt` | Stores the URLs processed. |
| `.github/workflows/run_scraper.yml` | GitHub Actions workflow for automation. |
| `scrapping_scripts`| Folder that contains the scripts needed to scrap each site|
---

## **⚠️ Troubleshooting**

### **1️⃣ GitHub Actions Fails Due to Authentication**
- Ensure the **GH_PAT** secret is correctly set in GitHub.
- Check that the PAT has the **repo** and **workflow** permissions.
- If authentication still fails, try re-generating the PAT.

### **2️⃣ Scraper Doesn't Push Updates**
- Ensure the script modifies the tracked files (`files/scraped_data.csv`).
- Confirm that `git commit -m` logs **changes** before pushing.


