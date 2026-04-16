# 2.1.0版本

> tldr：引入RAG，修改相应的内容层管线结构；

### 1、对比实验

enable_tmp_rag=True / False，对比生成的script质量：

- 开启RAG：由于有《西方哲学史讲演录》的原文作为参考，生成的内容中含有对复杂逻辑的精准阐述。质量高。

- 不开启RAG：生成的内容多生活化的通俗比喻，流于浅表。质量低。

### 2、2.1.0版本内容生成管线流程图

已加入log文件夹下（如果下面图片显示不出来的话）

<img src="C:\Code\sophia\hello_agent\sophia-app\log\v2.1设计&开发日志&文档\2.1.0版本内容生成管线流程图.jpg" alt="2.1.0版本内容生成管线流程图" style="zoom: 33%;" />

## bug to fix

- [ ] feat:chunk切分过于粗糙，年份被切断；同一语义的片段被切碎，同一语义块内内切碎的小块被按相关度排序而不是原序，喂给大模型之后大模型可能会很混乱（chunk_size过小）
  - [ ] 考虑markitdown之后按语义切分，再把chunksize调大一点，检索的top_k调小一点（或者不调小，但在写作llm前引入一个挑资料llm，因为调小了HyDE真的会遮蔽MQE和原始query的查询结果）
  - [ ] chunk_size过小+暴力切割 的一个例子：<img src="C:\Users\zanyan\AppData\Roaming\Typora\typora-user-images\image-20260411160117857.png" alt="image-20260411160117857" style="zoom:50%;" />

- [ ] feat: add_rag没有去重，这样重复加一本书会导致知识库污染，查询结果都是同一个chunk的重复

- [ ] fix: langraph checkpoint 保存报错，rag_componet里的复杂对象没法被保存到checkpoint中
  - [ ] 把rag_component从状态中拿出来，作为一个独立的服务启动
  - [ ] refactor: 顺便把go-api.bat也作为独立服务启动，防止忘记开