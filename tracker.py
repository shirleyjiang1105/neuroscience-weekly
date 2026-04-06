import feedparser
import datetime
from datetime import timedelta
import os
import requests
import json
import re

# ===================== 核心配置（3个核心关键词）=====================
# 25本神经科学Q1顶刊（RSS全覆盖）
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

# 精简为3个核心关键词（可按需修改）
KEYWORDS = [
    "Alzheimer",  # 阿尔茨海默病
    "fMRI",       # 功能磁共振
    "PET"     # 突触
]

DAYS = 7
# =====================================================

# 初始化变量
today = datetime.datetime.now()
cutoff = today - timedelta(days=DAYS)
week_tag = today.strftime("%Y-W%W")
filepath = f"weekly/weekly-{week_tag}.md"
total_papers = 0
output = {}

# 工具函数
def is_recent(parsed_time):
    try:
        pub_dt = datetime.datetime(*parsed_time[:6])
        return pub_dt >= cutoff
    except Exception as e:
        print(f"时间解析错误: {e}")
        return False

def clean_summary(summary):
    if not summary:
        return "无摘要"
    summary = re.sub(r"<[^>]+>", "", summary)
    summary = re.sub(r"\s+", " ", summary).strip()
    return summary[:200] + "..." if len(summary) > 200 else summary

def match_keyword(title, summary):
    text = (title + " " + summary).lower()
    matched = [kw for kw in KEYWORDS if kw.lower() in text]
    return ", ".join(matched) if matched else None

# 抓取期刊数据
print("开始抓取期刊数据...")
for journal_name, rss_url in JOURNALS.items():
    try:
        feed = feedparser.parse(rss_url)
        if feed.bozo != 0:
            print(f"{journal_name} RSS解析警告: {feed.bozo_exception}")
            continue
        
        matches = []
        for entry in feed.entries[:30]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            published = entry.get("published_parsed")
            summary = clean_summary(entry.get("summary", entry.get("description", "")))
            
            if not published or not is_recent(published):
                continue
            
            matched_kws = match_keyword(title, summary)
            if matched_kws:
                matches.append({
                    "keywords": matched_kws,
                    "title": title,
                    "link": link,
                    "summary": summary
                })
        
        if matches:
            output[journal_name] = matches
            total_papers += len(matches)
            print(f"✅ {journal_name}: 找到{len(matches)}篇匹配论文")
    except Exception as e:
        print(f"❌ {journal_name} 抓取失败: {str(e)}")

# 生成Markdown周报
os.makedirs("weekly", exist_ok=True)
md_content = f"# 神经科学顶刊周报 {week_tag}\n\n"
md_content += f"📅 更新时间：{today.strftime('%Y-%m-%d')}\n"
md_content += f"📊 本周匹配论文总数：{total_papers}篇\n\n"

for journal, papers in output.items():
    md_content += f"## 📖 {journal}\n\n"
    for idx, p in enumerate(papers, 1):
        md_content += f"### {idx}. **[{p['keywords']}]** {p['title']}\n"
        md_content += f"🔗 论文链接：{p['link']}\n"
        md_content += f"📝 摘要预览：{p['summary']}\n\n"

with open(filepath, "w", encoding="utf-8") as f:
    f.write(md_content)
print(f"✅ 周报已生成：{filepath}")

# 飞书推送
FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")

def send_feishu_notification():
    if not FEISHU_WEBHOOK:
        print("❌ 未配置飞书Webhook，跳过推送")
        return
    if total_papers == 0:
        print("ℹ️ 无匹配论文，跳过推送")
        return
    if not GITHUB_REPO:
        print("❌ 无法获取仓库地址，跳过推送")
        return
    
    report_link = f"https://github.com/{GITHUB_REPO}/blob/main/{filepath}"
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"content": "🧠 神经科学顶刊周报更新", "tag": "plain_text"},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "content": f"📅 更新时间：{today.strftime('%Y-%m-%d')}\n📊 本周共找到 **{total_papers}** 篇相关论文\n🔍 核心主题：{', '.join(KEYWORDS)}",
                    "tag": "lark_md"
                }
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"content": "📄 查看完整周报", "tag": "plain_text"},
                        "url": report_link,
                        "type": "primary"
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(
            FEISHU_WEBHOOK,
            json={"msg_type": "interactive", "card": card},
            timeout=10
        )
        if response.status_code == 200:
            print("✅ 飞书推送成功")
        else:
            print(f"❌ 飞书推送失败：{response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 飞书推送异常：{str(e)}")

send_feishu_notification()

# 更新README
readme_content = "# 🧠 神经科学顶刊每周自动追踪\n\n"
readme_content += "✅ 25本神经科学Q1顶刊 | 🕒 每周一自动更新 | 🔍 3个核心关键词过滤 | 📱 飞书实时推送\n\n"
readme_content += "## 🔧 核心配置\n"
readme_content += "### 跟踪期刊\n"
for j in JOURNALS.keys():
    readme_content += f"- {j}\n"
readme_content += "\n### 核心关键词\n"
for kw in KEYWORDS:
    readme_content += f"- {kw}\n"

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme_content)

print("\n🎉 任务执行完成！")
