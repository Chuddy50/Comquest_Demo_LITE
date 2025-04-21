import requests
from textblob import TextBlob

BASE_URL = "https://hacker-news.firebaseio.com/v0"

def get_item(item_id):
    url = f"{BASE_URL}/item/{item_id}.json"
    response = requests.get(url)
    return response.json()

def analyze_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity
