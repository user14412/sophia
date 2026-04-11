
import json
from rich import print as rprint

if __name__ == "__main__":
    rag_query_results = [
        "笛卡尔是法国哲学家，提出了'我思故我在'的命题。他认为普遍怀疑是一切知识的起点，只有那个正在怀疑的'我'是不可怀疑的。",
        "康德是德国哲学家，他的三大批判奠定了古典哲学的基石。他提出了'人为自然立法'，认为我们的理性为经验世界提供规律。",
        "苏怜烟是明末扬州的著名女子。"
    ]
    a = json.dumps(rag_query_results, ensure_ascii=False, indent=2)
    rprint(a)