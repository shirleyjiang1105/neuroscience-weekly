import feedparser
import datetime
from datetime import timedelta
import os
import requests
import re

# ==============================================
# 【你提供的 25 本神经科学顶刊 + 官方 RSS 链接】
# ==============================================
JOURNALS = {
    "Nature Reviews Neuroscience": "http://feeds.nature.com/nrn/rss/current",
    "Nature Human Behaviour": "http://feeds.nature.com/nathumbehav/rss/current",
    "Nature Neuroscience": "http://feeds.nature.com/neuro/rss/current",
    "Nature Aging": "http://feeds.nature.com/nataging/rss/current",
    "Trends in Cognitive Sciences": "https://www.cell.com/trends/cognitive-sciences/rss",
    "Behavioral and Brain Sciences": "https://www.cambridge.org/core/journals/behavioral-and-brain-sciences/rss",
    "Molecular Neurodegeneration": "http://www.molecularneurodegeneration.com/rss/",
    "Neuron": "https://www.cell.com/neuron/current.rss",
    "Trends in Neurosciences": "https://www.cell.com/trends/neurosciences/rss",
    "Annual Review of Neuroscience": "https://www.annualreviews.org/rss/neuro",
    "Sleep Medicine Reviews": "https://www.sciencedirect.com/journal/sleep-medicine-reviews/rss",
    "Translational Neurodegeneration": "http://www.translationalneurodegeneration.com/latest/rss",
    "Brain": "https://academic.oup.com/brain/rss",
    "Molecular Psychiatry": "http://feeds.nature.com/mp/rss/current",
    "Biological Psychiatry": "https://www.biologicalpsychiatryjournal.com/rss",
    "Acta Neuropathologica": "https://link.springer.com/search.rss?facet-content-type=Article&facet-journal-title=Acta+Neuropathologica",
    "Journal of Neuroinflammation": "https://jneuroinflammation.biomedcentral.com/rss",
    "Brain Behavior and Immunity": "https://www.sciencedirect.com/journal/brain-behavior-and-immunity/rss",
    "Journal of Pineal Research": "https://onlinelibrary.wiley.com/rss/journal/1600079x",
    "Annals of Neurology": "https://onlinelibrary.wiley.com/rss/journal/15318249",
    "Alzheimer's Research & Therapy": "https://alzres.biomedcentral.com/rss",
    "Neurology: Neuroimmunology & Neuroinflammation": "https://nn.neurology.org/rss",
    "Brain Stimulation": "https://www.brainstimulationjournal.com/rss",
    "Neuroscience and Biobehavioral Reviews": "https://www.sciencedirect.com/journal/neuroscience-and-biobehavioral-reviews/rss",
    "Journal of Headache and Pain": "https://thejournalofheadacheandpain.biomedcentral.com/rss"
}

# ===================== 3 个核心关键词 =====================
KEYWORDS = [
    "Alzheimer",
    "fMRI",
    "brain"
]

DAYS = 28  # 扩大到14天，保证抓到论文
# ==========================================================

today = datetime.datetime.now()
cutoff = today - timedelta(days=DAYS)
week_tag = today.strftime("%Y-W%W")
filepath = f"weekly/weekly-{week_tag}.md"
total_papers = 0
output = {}

# 工具函数
def is_recent(published_parsed):
    try:
        pub_time = datetime.datetime(*published_parsed[:6])
        return pub_time >= cutoff
    except:
        return False

def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200] + "..." if len(text) > 200 else text

def match_keywords(title, summary):
    combined = (title + " " + summary).lower()
    matched = [kw for kw in KEYWORDS if kw.lower() in combined]
    return ", ".join(matched) if matched else None

# 开始抓取
for journal_name, rss_url in JOURNALS.items():
    try:
        feed = feedparser.parse(rss_url)
        matches = []
        for entry in feed.entries[:30]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published_parsed")
            summary = clean_text(entry.get("summary", entry.get("description", "")))

            if published and is_recent(published):
                kw_match = match_keywords(title, summary)
                if kw_match:
                    matches.append({
                        "kw": kw_match,
                        "title": title,
                        "link": link,
                        "summary": summary
                    })
        if matches:
            output[journal_name] = matches
            total_papers += len(matches)
    except Exception:
        continue

# 生成周报
os.makedirs("weekly", exist_ok=True)
md_content = f"# 神经科学顶刊周报 {week_tag}\n"
md_content += f"📅 更新时间：{today.strftime('%Y-%m-%d')}\n"
md_content += f"🔍 匹配论文总数：{total_papers} 篇\n\n"

for jn, papers in output.items():
    md_content += f"## {jn}\n"
    for idx, p in enumerate(papers, 1):
        md_content += f"{idx}. **[{p['kw']}]** {p['title']}\n"
        md_content += f"🔗 {p['link']}\n"
        md_content += f"📝 {p['summary']}\n\n"

with open(filepath, "w", encoding="utf-8") as f:
    f.write(md_content)

# ===================== 飞书推送 =====================
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")

if FEISHU_WEBHOOK and REPO_NAME:
    report_url = f"https://github.com/{REPO_NAME}/blob/main/{filepath}"
    
    if total_papers > 0:
        title = "🧠 神经科学周报更新成功"
        content = f"本周共找到 **{total_papers} 篇** 匹配论文\n关键词：Alzheimer、fMRI、synapse"
    else:
        title = "🧠 周报运行成功"
        content = "✅ 系统正常\n本周无匹配论文，下周继续～"

    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "content": title,
                    "tag": "plain_text"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "content": content,
                        "tag": "lark_md"
                    }
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "content": "查看完整周报",
                                "tag": "plain_text"
                            },
                            "url": report_url,
                            "type": "primary"
                        }
                    ]
                }
            ]
        }
    }

    try:
        requests.post(FEISHU_WEBHOOK, json=message, timeout=10)
    except:
        pass

# 更新 README
with open("README.md", "w", encoding="utf-8") as f:
    f.write(f"# 🧠 神经科学顶刊自动周报\n\n跟踪25本顶刊 | 每周更新 | 关键词：Alzheimer、fMRI、synapse\n")
