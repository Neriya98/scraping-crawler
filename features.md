* reset the crawler:
    1. delete the scraped document
    2. delete the log info

* update:
    1. take the database and then update it with the new informations
    2. 

* scrap:
    1. take a website url
    2. find a sub url
    3. load the log info
    4. check if the url is already scraped (the suburl is in the log info)
    5. if yes, skip else scrap it
    6. add the new suburl scraped into the log file
