from flask import Flask, request, render_template, redirect, url_for
from bs4 import BeautifulSoup
import requests
import subprocess
import json
import os

app = Flask(__name__)
current_task_source = None  # To track the most recently used index page

# Home page: choose site (currently only Hacker News)
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/articles")
def articles():
    global current_task_source
    index_url = request.args.get("index_url")
    if not index_url:
        return "No index URL provided.", 400

    current_task_source = index_url  # save for later reuse

    # scrape article IDs
    page = requests.get(index_url)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(page.text, "html.parser")
    links = soup.find_all("a", href=True)
    story_ids = []

    for a in links:
        href = a["href"]
        if href.startswith("item?id="):
            story_id = href.split("id=")[1]
            if story_id not in story_ids:
                story_ids.append(story_id)
    story_ids = story_ids[:20]

    # get article metadata
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

    # extract domain for task display
    from urllib.parse import urlparse
    parsed_url = urlparse(index_url)
    source_name = parsed_url.netloc or index_url

    return render_template("articles.html", stories=stories, source_name=source_name)


@app.route("/scrape", methods=["POST"])
def scrape():
    story_id = request.form.get("story_id")
    if not story_id:
        return "No story ID provided.", 400
    subprocess.run(["python3", "hn_scraper.py", story_id])
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

    # ✅ Get the source name for the task header bar
    from urllib.parse import urlparse
    source_name = urlparse(current_task_source).netloc if current_task_source else "Hacker News"

    return render_template(
        "results.html",
        story=data,
        sentiment_summary=sentiment_summary,
        filter=request.args.get("filter"),
        top_block=top_block,
        bottom_block=bottom_block,
        source_name=source_name  # ✅ pass this to the template
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

@app.route("/delete_block", methods=["POST"])
def delete_block():
    block_index = int(request.form.get("block_index"))
    with open("output.json", "r") as f:
        data = json.load(f)

    if 0 <= block_index < len(data["blocks"]):
        del data["blocks"][block_index]

    with open("output.json", "w") as f:
        json.dump(data, f, indent=2)

    return redirect(url_for("results"))

@app.route("/override_block", methods=["POST"])
def override_block():
    block_index = int(request.form.get("block_index"))
    new_sentiment = request.form.get("new_sentiment")

    with open("output.json", "r") as f:
        data = json.load(f)

    if 0 <= block_index < len(data["blocks"]) and new_sentiment:
        # Map labels to values
        if new_sentiment == "positive":
            value = 0.8
        elif new_sentiment == "negative":
            value = -0.8
        else:
            value = 0.0
        data["blocks"][block_index]["avg_sentiment"] = value

    with open("output.json", "w") as f:
        json.dump(data, f, indent=2)

    return redirect(url_for("results"))


if __name__ == "__main__":
    app.run(debug=True)
