import json
import os

def json_to_md(json_path, md_dir):
    with open(json_path, "r", encoding="utf-8") as f:
        posts = json.load(f)
    os.makedirs(md_dir, exist_ok=True)
    for post in posts:
        md_content = f"# {post['topic_title']}\n\n"
        md_content += f"**Author:** {post['author']}  \n"
        md_content += f"**Date:** {post['created_at']}  \n"
        md_content += f"**URL:** {post['url']}  \n\n"
        md_content += post['content']
        md_file = os.path.join(md_dir, f"{post['topic_id']}_{post['post_id']}.md")
        with open(md_file, "w", encoding="utf-8") as f_md:
            f_md.write(md_content)

if __name__ == "__main__":
    json_to_md("data/fetched_discourse/fetched_discourse.json", "data/fetched_discourse/")
