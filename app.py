from flask import Flask, request, render_template, redirect, url_for
import requests
import subprocess
import json
import os

app = Flask(__name__)

# Home page: choose site (currently only Hacker News)
@app.route("/")
def index():
    return render_template("index.html")

# Step 2: Show Hacker News articles
@app.route("/articles")
def articles():
    top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    story_ids = requests.get(top_stories_url).json()[:10]  # top 10
    stories = []
    for story_id in story_ids:
        data = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
        if data and data.get("type") == "story" and "title" in data:
            stories.append({
                "id": data["id"],
                "title": data["title"],
                "by": data.get("by", "unknown"),
                "descendants": data.get("descendants", 0)
            })
    return render_template("articles.html", stories=stories)

# Step 3: Scrape the article by ID
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
