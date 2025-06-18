import json
import os

def json_to_md(json_path, md_dir):
    if not os.path.exists(json_path):
        print(f"JSON file not found: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            posts = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

    if not posts or not isinstance(posts, list):
        print("No valid posts found in JSON.")
        return
    
    os.makedirs(md_dir, exist_ok=True)
    for post in posts:
        topic_title = post.get("topic_title", "Untitled Topic")
        author = post.get("author", "Unknown")
        created_at = post.get("created_at", "Unknown Date")
        url = post.get("url", "No URL Provided")
        content = post.get("content", "")

        if not content.strip():
            print(f"Skipping post with no content: {post.get('post_id')}")
            continue

        md_content = f"# {topic_title}\n\n"
        md_content += f"**Author:** {author}  \n"
        md_content += f"**Date:** {created_at}  \n"
        md_content += f"**URL:** {url}  \n\n"
        md_content += content
        
        topic_id = post.get("topic_id", "unknown")
        post_id = post.get("post_id", "unknown")
        md_file = os.path.join(md_dir, f"{topic_id}_{post_id}.md")

        try:
            with open(md_file, "w", encoding="utf-8") as f_md:
                f_md.write(md_content)
        except Exception as e:
            print(f"Failed to write markdown file for post {post_id}: {e}")