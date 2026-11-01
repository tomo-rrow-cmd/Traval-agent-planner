# RAG 系统

## 1. 架构

```text
用户查询 "北京历史人文景点适合亲子"
    │
    ▼
EmbeddingService (ModelScope 下载/缓存 BAAI/bge-m3, 缺失时伪 embedding 降级)
    │
    ▼
Chroma VectorStore
    │
    ├── attractions  collection
    ├── restaurants  collection
    └── hotels       collection
    │
    ▼
Top-K 候选 (默认 RAG_TOP_K=40)
    │
    ▼
RerankerService (BAAI/bge-reranker-base, 默认取 RAG_FINAL_K=25)
    │
    ▼
PostgreSQL 补充坐标 (模糊匹配)
    │
    ▼
DeepSeek LLM → 排序/筛选/写推荐理由 → 最终结果
```

默认离线测试不依赖 BGE 模型缓存、ModelScope 网络或真实 Chroma 数据；需要真实向量检索数据的用例必须标记 `integration`。

## 2. VectorStore API

实现位置：`app/services/vector/vector_store.py`

```python
# 搜索
vector_store.search(collection_name, query_embedding, n_results=20, where={"city": "北京"})
# -> {"ids": [[...]], "metadatas": [[...]], "documents": [[...]], "distances": [[...]]}

# 写入
vector_store.upsert(collection_name, ids, embeddings, documents, metadatas)

# 统计
vector_store.count(collection_name)  # -> int
```

## 3. Embedding API

实现位置：`app/services/vector/embedding.py`

```python
# 文本转向量
vec = await embedding_service.embed_query("北京历史人文景点")
# -> list[float]  (1024维, normalized)

# 批量
vecs = await embedding_service.embed(["文本1", "文本2"])
# -> list[list[float]]
```

切换到 `BAAI/bge-m3` 后，已有 `chroma_data/` 中由旧 512 维模型写入的 collection 需要重建。可通过重新运行 `scripts/seed_poi.py --city 城市名` 删除并写入对应城市 collection。
