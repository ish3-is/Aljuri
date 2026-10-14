"""Test ranged (byte-range) parquet reads over HTTPS against a huge remote shard.

We must not download 4 GB/shard x 186 shards. pyarrow over an fsspec HTTP file
issues range requests, so we can read only the footer + specific row groups.
"""
import time

import fsspec
import pyarrow.parquet as pq

URL = "https://huggingface.co/datasets/OwensLab/CommunityForensics-Small/resolve/main/data/HFCF_small_0.parquet"

t0 = time.time()
fs = fsspec.filesystem("http", client_kwargs={"trust_env": True})
f = fs.open(URL, "rb", block_size=1 << 20)
pf = pq.ParquetFile(f)
print("opened in %.1fs" % (time.time() - t0))
print("num_rows:", pf.metadata.num_rows)
print("num_row_groups:", pf.metadata.num_row_groups)
print("schema:", pf.schema_arrow.names)

t0 = time.time()
tbl = pf.read_row_groups([0], columns=["image_name", "format", "resolution",
                                       "model_name", "label", "architecture",
                                       "real_source", "subset", "split"])
print("read metadata-only rowgroup 0 in %.1fs -> %d rows" % (time.time() - t0, tbl.num_rows))
print(tbl.slice(0, 5).to_pydict())