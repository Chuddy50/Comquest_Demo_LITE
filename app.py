from flask import Flask, request, render_template, redirect, url_for
from bs4 import BeautifulSoup
import requests
import subprocess
import json
import os

app = Flask(__name__)

# Home page: choose site (currently only Hacker News)
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/articles")
def articles():
    index_url = request.args.get("index_url")
    if not index_url:
        return "No index URL provided.", 400

    try:
        page = requests.get(index_url)
        soup = BeautifulSoup(page.text, "html.parser")
        links = soup.find_all("a", href=True)
        story_ids = []

        for a in links:
            href = a["href"]
            if href.startswith("item?id="):
                story_id = href.split("id=")[1]
                if story_id not in story_ids:
                    story_ids.append(story_id)
        story_ids = story_ids[:10]  # top 10
    except Exception as e:
        return f"Failed to parse index page: {e}", 500

    # Now fetch story metadata from HN API
    stories = []
    for sid in story_ids:
        data = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json").json()
        if data and "title" in data:
            stories.append({
                "id": data["id"],
                "title": data["title"],
                "by": data.get("by", "unknown"),
                "descendants": data.get("descendants", 0)
            })

    return render_template("articles.html", stories=stories)# Step 3: Scrape the article by ID

@app.route("/scrape")
def scrape():
    story_id = request.args.get("id")
    if not story_id:
        return "No story ID provided.", 400

    subprocess.run(["python3", "hn_scraper.py", story_id])
    with open("last_story_id.txt", "w") as f:
        f.write(story_id)
    return redirect(url_for("results"))

# Step 4: Show results from scrape
@app.route("/results")
def results():
    try:
        with open("output.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return "No results available. Please scrape an article first."

    blocks = data.get("blocks", [])
    sentiments = [b["avg_sentiment"] for b in blocks]

    if not sentiments:
        sentiment_summary = "No comment blocks found."
    else:
        avg = sum(sentiments) / len(sentiments)
        if avg > 0.05:
            sentiment_summary = "Overall sentiment: Positive 😊"
        elif avg < -0.05:
            sentiment_summary = "Overall sentiment: Negative 😠"
        else:
            sentiment_summary = "Overall sentiment: Neutral 😐"

    top_block = max(blocks, key=lambda b: b["avg_sentiment"], default=None)
    bottom_block = min(blocks, key=lambda b: b["avg_sentiment"], default=None)

    return render_template(
        "results.html",
        story=data,
        sentiment_summary=sentiment_summary,
        filter=request.args.get("filter"),
        top_block=top_block,
        bottom_block=bottom_block
    )

@app.route("/export")
def export_csv():
    try:
        with open("output.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return "No output to export."

    output = []
    for block in data["blocks"]:
        for comment in block["block"]:
            output.append({
                "author": comment["author"],
                "text": comment["text"].replace(",", " ").replace("\n", " "),
                "depth": comment["depth"],
                "sentiment": comment["sentiment"]
            })

    def generate():
        yield "author,text,depth,sentiment\n"
        for row in output:
            yield f"{row['author']},{row['text']},{row['depth']},{row['sentiment']}\n"

    from flask import Response
    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment; filename=comments.csv"})


if __name__ == "__main__":
    app.run(debug=True)
