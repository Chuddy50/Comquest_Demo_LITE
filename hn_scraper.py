from utils import get_item, analyze_sentiment
import json
import sys

def flatten_block(comment_id, depth=0, max_depth=3):
    comment = get_item(comment_id)
    if comment is None or comment.get('deleted') or comment.get('dead'):
        return [], 0, 0

    text = comment.get('text', '').replace('<p>', ' ')
    sentiment = analyze_sentiment(text)
    flat = [{
        "id": comment_id,
        "author": comment.get('by', '[deleted]'),
        "text": text,
        "depth": depth,
        "sentiment": sentiment
    }]
    total_sentiment = sentiment
    count = 1

    for kid in comment.get('kids', []):
        children, child_sent, child_count = flatten_block(kid, depth + 1, max_depth)
        flat.extend(children)
        total_sentiment += child_sent
        count += child_count

    return flat, total_sentiment, count

def scrape_story(story_id):
    story = get_item(story_id)
    comment_blocks = []

    for kid in story.get('kids', []):
        comments, total_sentiment, count = flatten_block(kid)
        avg_sent = total_sentiment / count if count else 0
        comment_blocks.append({
            "block": comments,
            "avg_sentiment": avg_sent
        })

    output = {
        "title": story['title'],
        "by": story['by'],
        "url": story.get('url'),
        "blocks": comment_blocks
    }

    with open("output.json", "w") as f:
        json.dump(output, f, indent=2)

    print("Saved to output.json")

if __name__ == "__main__":
    story_id = sys.argv[1] if len(sys.argv) > 1 else "37570037"
    scrape_story(int(story_id))
