import feedparser
import datetime
from datetime import timedelta
import os
import requests
import json
import re

# 25本神经科学顶刊
JOURNALS = {
    "Nature Reviews Neuroscience": "https://www.nature.com/nrn/rss/current.xml",
    "Nature Neuroscience": "https://www.nature.com/nn/rss/current.xml",
    "Neuron": "https://www.cell.com/neuron/rss",
    "Brain": "https://academic.oup.com/brain/rss.xml",
    "Molecular Psychiatry": "https://www.nature.com/mp/rss/current.xml",
    "Acta Neuropathologica": "https://link.springer.com/search.rss?f-journal=Acta+Neuropathologica",
    "Acta Neuropathologica Communications": "https://actaneurocomms.biomedcentral.com/articles/rss",
    "Alzheimer's & Dementia": "https://alz-journal.org/rss/published.xml",
    "NeuroImage": "https://www.sciencedirect.com/feeds?jid=10538119",
    "Cerebral Cortex": "https://academic.oup.com/cercor/rss.xml",
    "Acta Physiologica": "https://onlinelibrary.wiley.com/feed/14698994/latest",
    "Journal of Neuroinflammation": "https://jneuroinflammation.biomedcentral.com/articles/rss",
    "Neurobiology of Aging": "https://www.sciencedirect.com/feeds?jid=01974580",
    "Human Brain Mapping": "https://onlinelibrary.wiley.com/feed/10970193/latest",
    "Neurobiology of Disease": "https://www.sciencedirect.com/feeds?jid=09699961",
    "Glia": "https://onlinelibrary.wiley.com/feed/08941491/latest",
    "Pain": "https://www.sciencedirect.com/feeds?jid=03043959",
    "Cortex": "https://www.sciencedirect.com/feeds?jid=00109452",
    "Neuropsychopharmacology": "https://www.nature.com/npp/rss/current.xml",
    "Journal of Neuroscience": "https://www.jneurosci.org/rss/current.xml",
    "eNeuro": "https://www.eneuro.org/rss/current.xml",
    "NeuroMolecular Medicine": "https://link.springer.com/search.rss?f-journal=12017",
    "Frontiers in Neuroscience": "https://www.frontiersin.org/rss/neuroscience.xml",
    "Neurology": "https://n.neurology.org/rss/current.xml",
    "Brain Stimulation": "https://www.sciencedirect.com/feeds?jid=1935861X"
}

# 10个核心关键词
KEYWORDS = [
    "Alzheimer", "neurodegeneration", "neuroinflammation",
    "fMRI", "synapse", "plasticity", "microglia",
    "memory", "cognition", "depression"
]

DAYS = 7
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")

today = datetime.datetime.now()
cutoff = today - timedelta(days=DAYS)
week_tag = today.strftime("%Y-W%W")

def is_recent(parsed):
    try:
        return datetime.datetime(*parsed[:6]) >= cutoff
    except:
        return False

def clean_summary(s):
    s = re.sub(r"<[^>]+>", "", s)
    return s[:200] + "..." if len(s) > 200 else s

def has_keyword(t, s):
    txt = (t + s).lower()
    match = [k for k in KEYWORDS if k.lower() in txt]
    return ", ".join(match) if match else None

output = {}
total = 0

for jn, url in JOURNALS.items():
    try:
        fd = feedparser.parse(url)
        res = []
        for e in fd.entries[:30]:
            t = e.get("title", "")
            lk = e.get("link", "")
            ps = e.get("published_parsed")
            sm = clean_summary(e.get("summary", e.get("description", "")))
            if not ps or not is_recent(ps):
                continue
            kw = has_keyword(t, sm)
            if kw:
                res.append({
                    "kw": kw, "t": t, "lk": lk, "sm": sm
                })
        if res:
            output[jn] = res
            total += len(res)
    except:
        pass

os.makedirs("weekly", exist_ok=True)
path = f"weekly/weekly-{week_tag}.md"

md = f"# 神经科学顶刊周报 {week_tag}\n更新：{today.strftime('%Y-%m-%d')}\n总数：{total}\n\n"
for jn, papers in output.items():
    md += f"## {jn}\n"
    for i, p in enumerate(papers, 1):
        md += f"{i}. **[{p['kw']}]** {p['t']}\n"
        md += f"🔗 {p['lk']}\n"
        md += f"📝 {p['sm']}\n\n"

with open(path, "w", encoding="utf-8") as f:
    f.write(md)

# 飞书推送
if FEISHU_WEBHOOK and total > 0:
    repo = os.getenv("GITHUB_REPOSITORY")
    link = f"https://github.com/{repo}/blob/main/{path}"
    msg = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"content": "🧠 神经科学周报已更新", "tag": "plain_text"}},
            "elements": [
                {"tag": "div", "text": {"content": f"本周找到 **{total}** 篇相关论文", "tag": "lark_md"}},
                {"tag": "div", "text": {"content": f"[📄 查看完整周报]({link})", "tag": "lark_md"}}
            ]
        }
    }
    requests.post(FEISHU_WEBHOOK, json=msg)

with open("README.md", "w", encoding="utf-8") as f:
    f.write("# 神经科学顶刊周报\n自动跟踪25本顶刊，每周一飞书推送\n")
