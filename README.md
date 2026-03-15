Comquest Scraper Demo 
- a lightweight proof of concept scraper that scarpes pages and structures discussions commnets on the page from different news aggregate platforms
- this demo demonstrate ways discussion data can be collected then organized and analyzed
Overview
- user-generated content like comments are valuable for different downstream applications. Access is not widely had, and there are different limiations to the data that may skew information. Thus a system like Comquest was born, leveraging web APIs to collect comments from a large number of system.
Execution
- I created a variation of comquest that would be a kind of demo of what it might be used for in the real-world. While its is not as efficient or strong, I believe it executes enough to show why comquest would be valuable.

To Run
-   python3 -m pip install -r requirements.txt
-   python3 app.p and open http://127.0.0.1:5000, input the index page of
-   https://news.ycombinator.com/ and choose which articles to scrape 
