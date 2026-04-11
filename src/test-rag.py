import os

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_community.vectorstores import Chroma

from config import llm, RESOURCES_DIR

mini_sophia_doc_path = str(RESOURCES_DIR / "documents" / "mini_sophia.txt")
with open(mini_sophia_doc_path, "w", encoding="utf-8") as f:
    f.write("笛卡尔是法国哲学家，提出了'我思故我在'的命题。他认为普遍怀疑是一切知识的起点，只有那个正在怀疑的'我'是不可怀疑的。\n")
    f.write("康德是德国哲学家，他的三大批判奠定了古典哲学的基石。他提出了'人为自然立法'，认为我们的理性为经验世界提供规律。\n")
    f.write("苏怜烟是明末扬州的著名女子。\n")

print("正在加载文档...")
loader = TextLoader(mini_sophia_doc_path, encoding="utf-8")
docs = loader.load()

print("正在切割文本...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=50,
    chunk_overlap=10
)
chunks = text_splitter.split_documents(docs)

print("正在将文本向量化并存入 ChromaDB (初次运行需下载模型，可能较慢)...")
embeddings = HuggingFaceEmbeddings(
    model_name="moka-ai/m3e-base"
)

print("将数据存入当前目录下的 ./chroma_db 文件夹...")
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

print("下面开始检索...")
question = "苏怜烟是谁？"
print(f"\n用户提问：{question}")

retriever = vectorstore.as_retriever(search_kwargs={"k": 1})
retriever_doccs = retriever.invoke(question)

rag_context = retriever_doccs[0].page_content
print(f"\n检索到的相关内容：{rag_context}\n")

prompt = f"""
你是一个西方哲学播客的主讲人。请根据以下参考资料，用通俗易懂的话回答用户的问题。
严禁瞎编，如果参考资料里没提，你就说不知道。

【参考资料】：
{rag_context}

【用户问题】：
{question}
"""

response = llm.invoke(prompt)
print("============ DeepSeek 输出 ============")
print(f"{response.content}\n")
print("=======================================")