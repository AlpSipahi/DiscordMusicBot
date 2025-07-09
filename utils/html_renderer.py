import os
from datetime import datetime
import html
import re


async def generate_html_transcript(
    channel,
    limit=100,
    output_dir="transcripts",
    on_progress=None,
    pre_fetched_messages=None
):
    """
    Generates a Discord-style HTML transcript of messages in the given channel.

    :param channel: discord.TextChannel
    :param limit: number of messages to fetch (0 for all)
    :param output_dir: directory to save transcript file
    :param on_progress: optional callback(current_index, total)
    :param pre_fetched_messages: optional list of preloaded messages to use
    :return: full file path to the saved HTML transcript
    """

    messages = pre_fetched_messages or [msg async for msg in channel.history(limit=limit if limit != 0 else None)]
    messages.sort(key=lambda m: m.created_at)
    total = len(messages)

    css = """
    * { box-sizing: border-box; }
    html, body {
        max-width: 100vw;
        overflow-x: hidden;
    }
    body {
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        background: #36393F;
        color: #DCDDDE;
        margin: 0;
        padding: 20px;
    }
    h2 {
        color: #FFFFFF;
    }
    .message {
        display: flex;
        align-items: flex-start;
        padding: 8px 0;
        border-bottom: 1px solid #2F3136;
        overflow-x: hidden;
    }
    .avatar {
        width: 40px;
        height: 40px;
        object-fit: cover;
        border-radius: 50%;
        margin-right: 12px;
        flex-shrink: 0;
    }
    .content {
        flex-grow: 1;
        min-width: 0;
    }
    .username {
        font-weight: 600;
        color: #00AFF4;
        margin-right: 8px;
    }
    .timestamp {
        color: #72767D;
        font-size: 0.85em;
    }
    .text {
        margin-top: 4px;
        white-space: pre-wrap;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }
    a {
        color: #00AFF4;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    img {
        max-width: 100%;
        height: auto;
        border-radius: 6px;
        margin-top: 6px;
    }
    """

    html_content = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<title>Transcript - #{html.escape(channel.name)}</title>
<style>{css}</style>
</head>
<body>
<h2>Transcript for #{html.escape(channel.name)} ({html.escape(channel.guild.name)})</h2>
<hr />
"""

    for i, msg in enumerate(messages, start=1):
        timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = html.escape(msg.author.display_name)
        content = html.escape(msg.clean_content).replace("\n", "<br>") or "(no text)"

        avatar_url = getattr(msg.author, "display_avatar", None)
        avatar_url = avatar_url.url if avatar_url else ""

        html_content += f"""
<div class=\"message\">
  <img class=\"avatar\" src=\"{html.escape(avatar_url)}\" alt=\"avatar\" />
  <div class=\"content\">
    <span class=\"username\">{author}</span>
    <span class=\"timestamp\">{timestamp}</span>
    <div class=\"text\">{content}</div>
"""

        for embed in msg.embeds:
            title = html.escape(embed.title) if embed.title else ""
            description = html.escape(embed.description) if embed.description else ""
            url = html.escape(embed.url) if embed.url else ""
            html_content += f"<div class='text'><strong>{title}</strong><br>{description}<br><a href='{url}'>{url}</a></div>"

        for attachment in msg.attachments:
            url = html.escape(attachment.url)
            if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                html_content += f"<div class='text'><a href='{url}' target='_blank'><img src='{url}' alt='attachment'></a></div>"
            else:
                html_content += f"<div class='text'>📎 <a href='{url}' target='_blank'>{attachment.filename}</a></div>"

        html_content += "</div></div>"

        if on_progress:
            on_progress(i, total)

    html_content += """
</body>
</html>
"""

    os.makedirs(output_dir, exist_ok=True)

    def sanitize(text):
        return re.sub(r'[^a-zA-Z0-9_-]', '_', text)

    filename = f"transcript_{sanitize(channel.guild.name)}_{sanitize(channel.name)}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filepath
